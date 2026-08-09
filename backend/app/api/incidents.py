from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Feedback, Incident, IncidentLog, IncidentTimeline, KnowledgeBase, Log
from app.services.incidents import build_timeline, correlate, resolve, serialize, similar

router=APIRouter(prefix="/incidents")

class ResolveRequest(BaseModel):
    resolution: str = Field(min_length=2)
    root_cause: str | None = None
    notes: str | None = None
class FeedbackRequest(BaseModel):
    ai_correct: bool | None = None
    actual_root_cause: str | None = None
    actual_resolution: str | None = None
    engineer_comments: str | None = None

def get_incident(db, iid):
    obj=db.get(Incident, iid)
    if not obj: raise HTTPException(404, "Incident not found")
    return obj

@router.post("/correlate")
def run_correlation(db: Session=Depends(get_db)):
    return {"created": [serialize(x) for x in correlate(db)]}

@router.get("")
def list_incidents(status: str|None=None, severity: str|None=None, search: str|None=None, db: Session=Depends(get_db)):
    q=db.query(Incident)
    if status: q=q.filter(Incident.status==status.upper())
    if severity: q=q.filter(Incident.severity==severity.upper())
    if search: q=q.filter(Incident.summary.ilike(f"%{search}%"))
    return [serialize(x) for x in q.order_by(Incident.created_at.desc()).all()]

@router.get("/{incident_id}")
def detail(incident_id:int, db:Session=Depends(get_db)): return serialize(get_incident(db,incident_id))
@router.get("/{incident_id}/timeline")
def timeline(incident_id:int, db:Session=Depends(get_db)):
    get_incident(db,incident_id); return [{c.name:getattr(x,c.name) for c in x.__table__.columns} for x in db.query(IncidentTimeline).filter_by(incident_id=incident_id).order_by(IncidentTimeline.timestamp).all()]
@router.get("/{incident_id}/logs")
def logs(incident_id:int, db:Session=Depends(get_db)):
    get_incident(db,incident_id); return [{c.name:getattr(x,c.name) for c in x.__table__.columns} for x in db.query(Log).join(IncidentLog,IncidentLog.log_id==Log.id).filter(IncidentLog.incident_id==incident_id).order_by(Log.timestamp).all()]
@router.post("/{incident_id}/acknowledge")
def acknowledge(incident_id:int, db:Session=Depends(get_db)):
    x=get_incident(db,incident_id); x.status="ACKNOWLEDGED"; db.commit(); return serialize(x)
@router.post("/{incident_id}/resolve")
def resolve_incident(incident_id:int, body:ResolveRequest, db:Session=Depends(get_db)):
    return serialize(resolve(db,get_incident(db,incident_id),body.resolution,body.root_cause,body.notes))
@router.post("/{incident_id}/feedback")
def feedback(incident_id:int, body:FeedbackRequest, db:Session=Depends(get_db)):
    get_incident(db,incident_id); x=db.get(Feedback,incident_id) or Feedback(incident_id=incident_id); x.ai_correct=body.ai_correct; x.actual_root_cause=body.actual_root_cause; x.actual_resolution=body.actual_resolution; x.engineer_comments=body.engineer_comments; db.add(x); db.commit(); return {"ok":True}
@router.get("/{incident_id}/similar")
def get_similar(incident_id:int, db:Session=Depends(get_db)): return similar(db,get_incident(db,incident_id))
@router.get("/{incident_id}/analysis")
def analysis(incident_id:int, db:Session=Depends(get_db)):
    x=get_incident(db,incident_id); return {"status":"deterministic", "summary":x.summary, "probable_root_cause":x.root_cause or "Insufficient verified evidence", "evidence":["Observed timeline events"], "confidence":x.confidence or 0.35, "affected_services":serialize(x)["affected_services"], "suggested_resolution":"Acknowledge, inspect the timeline, then record the verified resolution.", "alternative_causes":[], "historical_matches":similar(db,x)}
