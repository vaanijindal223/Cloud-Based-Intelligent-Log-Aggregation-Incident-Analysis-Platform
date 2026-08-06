import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.config import settings
from app.database.session import Base, engine
from app.models import Feedback, Incident, IncidentTimeline, KnowledgeBase, Log  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        logger.warning("Database unavailable at startup; tables were not created.", exc_info=True)
    yield


app = FastAPI(title="Cloud-Based Log Aggregation & Alerting System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])


@app.get("/")
def root():
    return {"message": "Log Aggregation & Alerting System API is running"}
