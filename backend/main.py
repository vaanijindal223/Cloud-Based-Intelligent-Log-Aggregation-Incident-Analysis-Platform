import logging
import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, simulation, incidents, dashboard, knowledge_base
from app.config import settings
from app.database.migrations import upgrade_database
from app.database.session import Base, SessionLocal, engine
from app.models import Feedback, Incident, IncidentTimeline, KnowledgeBase, Log, IncidentAnalysis, IncidentAlert  # noqa: F401
from app.services.incidents import process_pending_incidents

logger = logging.getLogger(__name__)


async def _process_pending_incidents() -> None:
    """Consume collector rows using the existing in-process Phase 4 services."""
    while True:
        db = SessionLocal()
        try:
            process_pending_incidents(db)
        except Exception:
            db.rollback()
            logger.exception("Automatic incident correlation failed")
        finally:
            db.close()
        await asyncio.sleep(settings.correlation_poll_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    processing_task = None
    try:
        Base.metadata.create_all(bind=engine)
        upgrade_database(engine)
        processing_task = asyncio.create_task(_process_pending_incidents())
    except Exception:
        logger.warning("Database unavailable at startup; tables were not created.", exc_info=True)
    try:
        yield
    finally:
        if processing_task is not None:
            processing_task.cancel()
            with suppress(asyncio.CancelledError):
                await processing_task


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
