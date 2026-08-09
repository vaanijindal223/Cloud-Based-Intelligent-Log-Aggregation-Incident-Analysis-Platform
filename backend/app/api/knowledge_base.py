from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models import KnowledgeBase
router=APIRouter(prefix="/knowledge-base")
@router.get("")
def list_kb(search:str|None=None, db:Session=Depends(get_db)):
 q=db.query(KnowledgeBase)
 if search: q=q.filter(KnowledgeBase.summary.ilike(f"%{search}%"))
 return [{c.name:getattr(x,c.name) for c in x.__table__.columns} for x in q.order_by(KnowledgeBase.created_at.desc()).all()]
