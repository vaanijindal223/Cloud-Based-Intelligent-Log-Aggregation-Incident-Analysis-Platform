import json
from datetime import datetime, timezone

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Feedback, Incident, IncidentLog, IncidentTimeline, KnowledgeBase, Log

RANK = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "WARN": 2, "ERROR": 3, "CRITICAL": 4}


def severity(logs):
    maximum = max((RANK.get((x.severity or "INFO").upper(), 1) for x in logs), default=1)
    errors = sum(RANK.get((x.severity or "INFO").upper(), 1) >= 3 for x in logs)
    services = len({x.service for x in logs})
    if maximum == 4 or errors >= 5: return "CRITICAL"
    if maximum >= 3 and (errors >= 2 or services >= 2): return "HIGH"
    if maximum >= 3: return "MEDIUM"
    return "LOW"


def correlate(db: Session):
    """Correlate only unprocessed error/warning records; stable key prevents global time grouping."""
    logs = db.query(Log).filter(Log.processed.is_(False)).order_by(Log.timestamp).all()
    grouped = {}
    for log in logs:
        if RANK.get((log.severity or "INFO").upper(), 1) < 2:
            log.processed = True
            continue
        key = ("incident", log.incident_id) if log.incident_id else (("trace", log.trace_id) if log.trace_id else ("signal", log.service, log.workflow, log.failure_type))
        grouped.setdefault(key, []).append(log)
    made = []
    for key, group in grouped.items():
        # Prevent an unrelated, long-running signal from forming a single incident.
        chunks, current = [], []
        for log in group:
            if current and (log.timestamp - current[-1].timestamp).total_seconds() > settings.max_incident_gap_seconds:
                chunks.append(current); current = []
            current.append(log)
        if current: chunks.append(current)
        for chunk in chunks:
            first, last = chunk[0], chunk[-1]
            services = sorted({x.service for x in chunk})
            issue = next((x.failure_type for x in chunk if x.failure_type), None) or first.message
            incident = Incident(severity=severity(chunk), status="ACTIVE", summary=f"{issue} affecting {', '.join(services)}", start_time=first.timestamp, end_time=last.timestamp, affected_services=json.dumps(services))
            db.add(incident); db.flush()
            for log in chunk:
                db.add(IncidentLog(incident_id=incident.incident_id, log_id=log.id)); log.processed = True
            build_timeline(db, incident, chunk)
            made.append(incident)
    db.commit()
    return made


def build_timeline(db, incident, logs=None):
    logs = logs or db.query(Log).join(IncidentLog, IncidentLog.log_id == Log.id).filter(IncidentLog.incident_id == incident.incident_id).order_by(Log.timestamp).all()
    db.query(IncidentTimeline).filter_by(incident_id=incident.incident_id).delete()
    for log in logs:
        db.add(IncidentTimeline(incident_id=incident.incident_id, timestamp=log.timestamp, service=log.service, severity=log.severity, event=log.message, evidence="observed log", log_id=log.id))
    db.flush()


def serialize(incident):
    data = {c.name: getattr(incident, c.name) for c in incident.__table__.columns}
    data["affected_services"] = json.loads(data["affected_services"] or "[]")
    return data


def similar(db, incident, limit=None):
    terms = set((incident.summary or "").lower().split())
    candidates = db.query(KnowledgeBase).join(Incident).filter(Incident.incident_id != incident.incident_id).all()
    scored=[]
    for row in candidates:
        text=" ".join(filter(None, [row.summary, row.root_cause, row.resolution])).lower(); words=set(text.split())
        score=len(terms & words)/max(1, len(terms | words))
        if score: scored.append({"incident_id": row.incident_id, "root_cause": row.root_cause, "resolution": row.resolution, "similarity": round(score, 2)})
    return sorted(scored, key=lambda x:x["similarity"], reverse=True)[:limit or settings.rag_top_k]


def resolve(db, incident, resolution, root_cause=None, notes=None):
    incident.status="RESOLVED"; incident.resolved_at=datetime.now(timezone.utc)
    feedback=db.get(Feedback, incident.incident_id)
    # Verified engineer evidence is the canonical historical record when supplied.
    verified_root_cause=(feedback.actual_root_cause if feedback and feedback.actual_root_cause else root_cause)
    verified_resolution=(feedback.actual_resolution if feedback and feedback.actual_resolution else resolution)
    if verified_root_cause: incident.root_cause=verified_root_cause
    events=db.query(IncidentTimeline).filter_by(incident_id=incident.incident_id).order_by(IncidentTimeline.timestamp).all()
    timeline_summary=" | ".join(f"{event.service}: {event.event}" for event in events[:20])
    historical_summary=" ".join(filter(None, [incident.summary, f"failure_type: {next((x.failure_type for x in db.query(Log).join(IncidentLog, IncidentLog.log_id == Log.id).filter(IncidentLog.incident_id == incident.incident_id).all() if x.failure_type), '')}", f"affected_services: {incident.affected_services}", f"timeline: {timeline_summary}"]))
    kb=db.query(KnowledgeBase).filter_by(incident_id=incident.incident_id).first()
    engineer_notes="\n".join(filter(None, [notes, feedback.engineer_comments if feedback else None]))
    if not kb: kb=KnowledgeBase(incident_id=incident.incident_id, root_cause=incident.root_cause or "Not confirmed", resolution=verified_resolution, engineer_notes=engineer_notes or None, summary=historical_summary); db.add(kb)
    else: kb.root_cause=incident.root_cause or kb.root_cause; kb.resolution=verified_resolution; kb.engineer_notes=engineer_notes or kb.engineer_notes; kb.summary=historical_summary
    db.commit(); db.refresh(incident); return incident
