from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models import Incident, KnowledgeBase
from app.services.incidents import serialize
router=APIRouter(prefix="/dashboard")
@router.get("/summary")
def summary(db:Session=Depends(get_db)):
    all_=db.query(Incident).all(); counts={s:sum(x.severity==s for x in all_) for s in ["CRITICAL","HIGH","MEDIUM","LOW"]}
    return {"total_incidents":len(all_),"active_incidents":sum(x.status not in ("RESOLVED","CLOSED") for x in all_),"resolved_incidents":sum(x.status=="RESOLVED" for x in all_),"severity":counts,"recent_incidents":[serialize(x) for x in sorted(all_,key=lambda x:x.created_at,reverse=True)[:8]],"knowledge_base_count":db.query(KnowledgeBase).count()}
