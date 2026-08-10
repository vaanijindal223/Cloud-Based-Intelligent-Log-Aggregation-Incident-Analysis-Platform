import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.database.migrations import upgrade_database
from app.database.session import Base
from app.models import Incident, IncidentTimeline, Log
from app.services.incidents import process_pending_incidents


def test_existing_timeline_schema_gets_log_id_before_processing():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE incidents (
                incident_id INTEGER PRIMARY KEY,
                severity VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL
            )
        """))
        # Phase-1 timeline shape: service, severity, and log_id were added later.
        # The missing log_id reproduces the EC2 INSERT failure.
        connection.execute(text("""
            CREATE TABLE incident_timeline (
                id INTEGER PRIMARY KEY,
                incident_id INTEGER NOT NULL,
                timestamp DATETIME NOT NULL,
                event TEXT NOT NULL,
                evidence TEXT
            )
        """))
        connection.execute(text("""
            INSERT INTO incident_timeline
                (id, incident_id, timestamp, event, evidence)
            VALUES (1, 99, '2026-08-10 00:00:00', 'legacy event', 'observed log')
        """))

    # create_all cannot alter either existing table; the repository migration
    # must do that before correlation attempts its timeline INSERT.
    Base.metadata.create_all(engine)
    upgrade_database(engine)
    assert "log_id" in {
        column["name"] for column in inspect(engine).get_columns("incident_timeline")
    }
    assert sessionmaker(bind=engine)().query(IncidentTimeline).count() == 1

    db = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)
    db.add_all([
        Log(id=i, timestamp=now, service=f"service-{i}", severity="ERROR", message=f"event-{i}",
            host="host", trace_id="trace-18", incident_id="INC-18", workflow="checkout",
            failure_type="database_timeout", source="local", source_event_id=f"timeline:{i}", processed=False)
        for i in range(5, 11)
    ])
    db.commit()

    created = process_pending_incidents(db)

    assert len(created) == 1
    incident = db.query(Incident).one()
    timeline = db.query(IncidentTimeline).filter_by(incident_id=incident.incident_id).all()
    assert len(timeline) == 6
    assert {row.log_id for row in timeline} == set(range(5, 11))
