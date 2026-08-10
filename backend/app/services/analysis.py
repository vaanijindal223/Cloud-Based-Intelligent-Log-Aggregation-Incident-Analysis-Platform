"""Optional Gemini-powered incident analysis. Failure never blocks incidents."""
import json
import logging
from datetime import date, datetime
from google import genai
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.config import settings
from app.models import IncidentAnalysis, IncidentTimeline
from app.services.incidents import serialize, similar

logger = logging.getLogger(__name__)

class GeminiAnalysisPayload(BaseModel):
    """The structured response contract requested from the Gemini SDK."""
    summary: str
    probable_root_cause: str
    evidence: list[str]
    confidence: float
    suggested_resolution: str
    alternative_causes: list[str]


def _json_default(value):
    """Convert database timestamps into unambiguous prompt-safe values."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _dump(row):
    data = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    for key in ("evidence", "alternative_causes", "historical_matches"):
        data[key] = json.loads(data[key] or "[]")
    data["affected_services"] = data.get("affected_services", [])
    return data


def get_analysis(db: Session, incident):
    row = db.get(IncidentAnalysis, incident.incident_id)
    return _dump(row) if row else None


def analyze(db: Session, incident):
    """Generate once and persist. Returns None when Gemini is not usable."""
    existing = db.get(IncidentAnalysis, incident.incident_id)
    if existing:
        return _dump(existing)
    if not settings.gemini_api_key:
        return None
    timeline = db.query(IncidentTimeline).filter_by(incident_id=incident.incident_id).order_by(IncidentTimeline.timestamp).limit(25).all()
    historical = similar(db, incident)
    prompt = {
        "current_incident": serialize(incident),
        "timeline_observed_facts": [{"service": x.service, "severity": x.severity, "event": x.event} for x in timeline],
        "historical_evidence": historical,
        "instructions": "Return JSON only: summary, probable_root_cause, evidence, confidence (0..1), suggested_resolution, alternative_causes. Clearly label inference as likely/unconfirmed; never present inferred cause as observed fact.",
    }
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        result = client.models.generate_content(
            model=settings.gemini_model,
            contents=json.dumps(prompt, default=_json_default),
            config={
                "system_instruction": "You are an incident analyst. Use only supplied evidence.",
                "response_mime_type": "application/json",
                "response_schema": GeminiAnalysisPayload,
                "http_options": {"timeout": settings.gemini_timeout_seconds * 1000},
            },
        )
        payload = json.loads(result.text or "{}")
        required = ("summary", "probable_root_cause", "evidence", "confidence", "suggested_resolution", "alternative_causes")
        if any(key not in payload for key in required):
            raise ValueError("model response omitted required analysis fields")
        row = IncidentAnalysis(incident_id=incident.incident_id, summary=str(payload["summary"]), probable_root_cause=str(payload["probable_root_cause"]), evidence=json.dumps(payload["evidence"]), confidence=max(0.0, min(1.0, float(payload["confidence"]))), suggested_resolution=str(payload["suggested_resolution"]), alternative_causes=json.dumps(payload["alternative_causes"]), historical_matches=json.dumps(historical), model=settings.gemini_model)
        db.add(row); incident.status = "AI_ANALYZED"; db.commit(); db.refresh(row)
        return _dump(row)
    except Exception:
        db.rollback(); logger.exception("AI analysis unavailable for incident %s", incident.incident_id)
        return None

