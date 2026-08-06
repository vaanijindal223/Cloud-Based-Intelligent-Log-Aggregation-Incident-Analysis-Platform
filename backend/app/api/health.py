from fastapi import APIRouter
from sqlalchemy import text

from app.database.session import engine

router = APIRouter()


@router.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {"status": "ok", "database": db_status}
