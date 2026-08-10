import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, simulation, incidents, dashboard, knowledge_base
from app.config import settings
from app.database.migrations import upgrade_database
from app.database.session import Base, engine
from app.models import Feedback, Incident, IncidentTimeline, KnowledgeBase, Log, IncidentAnalysis, IncidentAlert  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        upgrade_database(engine)
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
app.include_router(simulation.router, prefix="/api", tags=["simulation"])
app.include_router(incidents.router, prefix="/api", tags=["incidents"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(knowledge_base.router, prefix="/api", tags=["knowledge base"])


@app.get("/")
def root():
    return {"message": "Log Aggregation & Alerting System API is running"}
