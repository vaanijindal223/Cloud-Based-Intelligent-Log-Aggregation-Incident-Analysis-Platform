import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    # Entering as a context manager keeps one persistent event loop/portal alive
    # for the whole module, instead of a fresh one per request - required for a
    # background asyncio.create_task (the simulation runner) to keep progressing
    # between requests rather than being torn down with a per-request loop.
    with TestClient(app) as c:
        yield c


def _stop_if_running(client):
    client.post("/api/simulation/stop")


def test_list_workflows(client):
    response = client.get("/api/simulation/workflows")
    assert response.status_code == 200
    names = {w["name"] for w in response.json()}
    assert "ecommerce" in names


def test_list_failures(client):
    response = client.get("/api/simulation/failures")
    assert response.status_code == 200
    names = {f["name"] for f in response.json()}
    assert {"none", "database_timeout", "redis_failure", "payment_api_timeout",
            "auth_failure", "cpu_spike", "disk_full"} <= names


def test_start_instant_completes_and_writes_log(client):
    _stop_if_running(client)
    response = client.post(
        "/api/simulation/start",
        json={"workflow": "ecommerce", "failure": "database_timeout", "speed": "instant"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["incident_id"] is not None
    trace_id = body["trace_id"]

    status = {}
    for _ in range(20):
        status = client.get("/api/simulation/status").json()
        if status["status"] == "completed":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("simulation did not complete in time")

    assert status["emitted_count"] == status["total_steps"]

    log_lines = Path(settings.log_file_path).read_text(encoding="utf-8").splitlines()
    matching = [json.loads(line) for line in log_lines if trace_id in line]
    assert len(matching) == status["total_steps"]
    assert all(entry["trace_id"] == trace_id for entry in matching)
    assert all(entry["incident_id"] == body["incident_id"] for entry in matching)


def test_cannot_start_while_running_then_stop(client):
    _stop_if_running(client)
    start = client.post(
        "/api/simulation/start",
        json={"workflow": "ecommerce", "failure": "cpu_spike", "speed": "normal"},
    )
    assert start.status_code == 200

    conflict = client.post(
        "/api/simulation/start",
        json={"workflow": "ecommerce", "failure": "none", "speed": "instant"},
    )
    assert conflict.status_code == 409

    stop = client.post("/api/simulation/stop")
    assert stop.status_code == 200

    status = {}
    for _ in range(20):
        status = client.get("/api/simulation/status").json()
        if status["status"] == "stopped":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("simulation did not stop in time")
