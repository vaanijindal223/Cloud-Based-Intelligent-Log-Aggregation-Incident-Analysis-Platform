import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.session import Base
from app.models import Incident, IncidentAlert
from app.services.analysis import _json_default, analyze
from app.services.alerts import send_initial_alert


def _session_and_incident():
    engine=create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine); db=sessionmaker(bind=engine)()
    incident=Incident(severity="CRITICAL", status="ACTIVE", summary="database timeout", affected_services='["order-service"]')
    db.add(incident); db.commit(); return db, incident


def test_analysis_is_unavailable_without_gemini_key():
    db, incident = _session_and_incident()
    with patch("app.services.analysis.settings.gemini_api_key", None):
        assert analyze(db, incident) is None


def test_analysis_prompt_timestamps_are_json_safe():
    assert _json_default(datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)) == "2026-08-10T12:00:00+00:00"


def test_gemini_analysis_is_persisted():
    db, incident = _session_and_incident()
    response = MagicMock()
    response.text = '{"summary":"Checkout failures","probable_root_cause":"Database timeout","evidence":["order-service timeout"],"confidence":0.91,"suggested_resolution":"Restore database connectivity","alternative_causes":["Network latency"]}'
    client = MagicMock()
    client.models.generate_content.return_value = response
    with patch("app.services.analysis.settings.gemini_api_key", "test-key"), \
         patch("app.services.analysis.genai.Client", return_value=client):
        result = analyze(db, incident)
    assert result["probable_root_cause"] == "Database timeout"
    assert result["model"] == "gemini-3.6-flash"
    client.models.generate_content.assert_called_once()


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
