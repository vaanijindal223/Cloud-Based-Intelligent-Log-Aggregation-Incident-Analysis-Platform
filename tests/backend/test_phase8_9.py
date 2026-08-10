import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.session import Base
from app.models import Incident, IncidentAlert
from app.services.analysis import analyze
from app.services.alerts import send_initial_alert


def _session_and_incident():
    engine=create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine); db=sessionmaker(bind=engine)()
    incident=Incident(severity="CRITICAL", status="ACTIVE", summary="database timeout", affected_services='["order-service"]')
    db.add(incident); db.commit(); return db, incident


def test_analysis_is_unavailable_without_key():
    db, incident = _session_and_incident()
    with patch("app.services.analysis.settings.openai_api_key", None):
        assert analyze(db, incident) is None


def test_sns_is_one_alert_per_incident():
    db, incident = _session_and_incident()
    client=MagicMock(); client.publish.return_value={"MessageId":"msg-1"}
    with patch("app.services.alerts.settings.sns_topic_arn", "arn:aws:sns:ap-south-1:123:test"), \
         patch("app.services.alerts.settings.alert_critical", True), \
         patch("app.services.alerts.boto3.client", return_value=client):
        assert send_initial_alert(db, incident).sent is True
        assert send_initial_alert(db, incident) is None
    assert client.publish.call_count == 1
    assert db.query(IncidentAlert).count() == 1
