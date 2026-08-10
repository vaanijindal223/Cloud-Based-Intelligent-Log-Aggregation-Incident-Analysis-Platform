import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.database.migrations import upgrade_database
from app.database.session import Base
from app.models import Incident


def test_legacy_incidents_table_is_upgraded_without_losing_rows():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        # Representative old schema: it predates every newer Incident field.
        connection.execute(text("""
            CREATE TABLE incidents (
                incident_id INTEGER PRIMARY KEY,
                severity VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL
            )
        """))
        connection.execute(text("""
            INSERT INTO incidents (incident_id, severity, status)
            VALUES (42, 'HIGH', 'ACTIVE')
        """))

    Base.metadata.create_all(engine)
    added = upgrade_database(engine)

    expected = {column.name for column in Incident.__table__.columns}
    assert expected <= {column["name"] for column in inspect(engine).get_columns("incidents")}
    assert {"summary", "affected_services", "created_at", "updated_at"} <= set(added)

    db = sessionmaker(bind=engine)()
    incident = db.get(Incident, 42)
    assert incident is not None
    assert incident.summary == "Incident awaiting correlation"
    assert incident.affected_services == "[]"
    assert incident.severity == "HIGH"
    assert incident.status == "ACTIVE"

    # A restart is safe and does not alter the preserved row.
    assert upgrade_database(engine) == []
    assert db.get(Incident, 42).incident_id == 42
