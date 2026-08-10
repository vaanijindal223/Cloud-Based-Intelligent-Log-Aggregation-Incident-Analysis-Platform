"""One SNS notification per incident, using boto3's default credential chain."""
import logging
from datetime import datetime, timezone
import boto3
from sqlalchemy.orm import Session
from app.config import settings
from app.models import IncidentAlert
from app.services.incidents import serialize

logger = logging.getLogger(__name__)


def should_alert(incident):
    return (incident.severity == "CRITICAL" and settings.alert_critical) or (incident.severity == "HIGH" and settings.alert_high)


def send_initial_alert(db: Session, incident, analysis=None):
    if not should_alert(incident) or not settings.sns_topic_arn or db.get(IncidentAlert, incident.incident_id):
        return None
    data = serialize(incident)
    message = f"Incident INC-{incident.incident_id}\nSeverity: {incident.severity}\nSummary: {incident.summary}\nAffected services: {', '.join(data['affected_services'])}"
    if analysis:
        message += f"\nLikely root cause (AI inference): {analysis['probable_root_cause']}\nConfidence: {analysis['confidence']}\nSuggested resolution: {analysis['suggested_resolution']}"
    row = IncidentAlert(incident_id=incident.incident_id)
    db.add(row); db.flush()
    try:
        response = boto3.client("sns", region_name=settings.aws_region).publish(TopicArn=settings.sns_topic_arn, Subject=f"[{incident.severity}] Incident INC-{incident.incident_id}", Message=message)
        row.sent=True; row.message_id=response.get("MessageId"); row.sent_at=datetime.now(timezone.utc); db.commit()
    except Exception as exc:
        row.error=str(exc); db.commit(); logger.exception("SNS alert failed for incident %s", incident.incident_id)
    return row
