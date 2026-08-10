import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database.session import Base
from app.models import Incident, IncidentLog, Log
from app.services.incidents import process_pending_incidents
from app.database.session import get_db
from main import app


def test_collected_logs_are_built_into_an_incident():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    timestamp = datetime.now(timezone.utc)
    db.add_all([
        Log(timestamp=timestamp, service="orders", severity="ERROR", message="DB timeout", host="h",
            trace_id="trace-flow", incident_id="INC-flow", workflow="checkout", failure_type="database_timeout",
            source="local", source_event_id="flow:1", processed=False),
        Log(timestamp=timestamp, service="gateway", severity="ERROR", message="503", host="h",
            trace_id="trace-flow", incident_id="INC-flow", workflow="checkout", failure_type="database_timeout",
            source="local", source_event_id="flow:2", processed=False),
    ])
    db.commit()

    created = process_pending_incidents(db)

    assert len(created) == 1
    incident = db.query(Incident).one()
    assert incident.severity == "HIGH"
    assert db.query(IncidentLog).filter_by(incident_id=incident.incident_id).count() == 2
    assert process_pending_incidents(db) == []

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/incidents")
        assert response.status_code == 200
        assert response.json()[0]["incident_id"] == incident.incident_id
    finally:
        app.dependency_overrides.clear()
