import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.models import IncidentLog, IncidentTimeline, Log  # noqa: E402
from app.services.incidents import correlate  # noqa: E402


def test_correlation_creates_incident_links_and_timeline():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    timestamp = datetime.now(timezone.utc)
    session.add_all([
        Log(timestamp=timestamp, service="order-service", severity="ERROR", message="Database timeout",
            host="host", trace_id="trace-1", incident_id="INC-source", workflow="ecommerce",
            failure_type="database_timeout", source="local", source_event_id="local:1", processed=False),
        Log(timestamp=timestamp + timedelta(seconds=1), service="api-gateway", severity="ERROR", message="503",
            host="host", trace_id="trace-1", incident_id="INC-source", workflow="ecommerce",
            failure_type="database_timeout", source="local", source_event_id="local:2", processed=False),
    ])
    session.commit()

    created = correlate(session)

    assert len(created) == 1
    assert created[0].severity == "HIGH"
    assert session.query(IncidentLog).filter_by(incident_id=created[0].incident_id).count() == 2
    assert session.query(IncidentTimeline).filter_by(incident_id=created[0].incident_id).count() == 2
    assert session.query(Log).filter_by(processed=False).count() == 0
