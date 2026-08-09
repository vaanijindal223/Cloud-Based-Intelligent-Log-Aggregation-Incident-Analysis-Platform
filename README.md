# Cloud-Based Log Aggregation & Alerting System

An intelligent monitoring platform that sits on top of cloud log aggregation and turns thousands of raw logs into a handful of meaningful, explained incidents — instead of another CloudWatch/ELK/Splunk clone.

```
Logs → Aggregation → Incident Correlation → Incident Timeline →
Historical Retrieval → Explainable AI → Smart Alerts → Engineer Feedback → Knowledge Base
```

Built incrementally, one module/phase at a time. See progress below.

## Tech stack
- **Frontend:** React, Tailwind CSS, Axios, Recharts
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL
- **Processing:** deterministic in-process correlation (no queue required)
- **Cloud:** AWS EC2, CloudWatch Logs, SNS, IAM, S3 (optional)
- **AI:** optional OpenAI-ready provider configuration; deterministic fallback remains available
- **Containers:** Docker, Docker Compose

## Project structure
```
backend/                FastAPI app (API, models, services, database)
  app/simulation/          Scenario-based demo log generator     (Phase 2)
frontend/                React + Vite + Tailwind dashboard
collector/                CloudWatch → PostgreSQL normalizer   (Phase 3B)
correlation_engine/       Groups logs into incidents           (Phase 4)
incident_builder/          Persists incidents                    (Phase 4)
timeline_engine/           Builds incident timelines              (Phase 5)
knowledge_base/            Historical incident storage/retrieval  (Phase 7)
llm_engine/                 Explainable AI (LangChain)              (Phase 8)
alert_service/               Smart SNS alerting                       (Phase 9)
docker/                       Shared infra config
docs/                          Design/reference docs
  data_contract.md              Canonical log shape across every module
  aws/                            Phase 3A CloudWatch Agent config, IAM policy, runbook
scripts/                        Helper/automation scripts
tests/                            Test suites
docker-compose.yml
```

## Phase progress
- [x] **Phase 1 — Project Setup**: FastAPI backend, React frontend, PostgreSQL, Docker Compose, all wired together
- [x] **Phase 2 — Log Generation**: scenario-based simulation engine (ecommerce workflow + 6 injectable failures), real-time paced background execution, REST control API
- [x] **Phase 3A — Cloud Log Collection**: CloudWatch Agent config/IAM policy/runbook prepared (`docs/aws/`) — apply on your own AWS account, not run from this repo's dev environment
- [x] **Phase 3B — CloudWatch Log Collector**: polls CloudWatch Logs, normalizes into the [data contract](docs/data_contract.md), dedups via `source_event_id`, writes to PostgreSQL with `processed = false`
- [ ] Phase 4 — Incident Correlation Engine
- [ ] Phase 5 — Incident Timeline
- [ ] Phase 6 — Dashboard
- [ ] Phase 7 — Historical Knowledge Base
- [ ] Phase 8 — Explainable AI
- [ ] Phase 9 — Smart Alerts
- [ ] Phase 10 — Engineer Feedback

## Phase 1 — Setup & Run

### What's included
- FastAPI backend (`backend/`) with `GET /` and `GET /api/health`, SQLAlchemy models for all 5 tables (`logs`, `incidents`, `incident_timeline`, `knowledge_base`, `feedback`, auto-created on startup), CORS enabled for the frontend.
- React + Vite + Tailwind frontend (`frontend/`) with a page that calls `/api/health` and shows a live backend/DB connection indicator.
- `docker-compose.yml` wiring `postgres` → `backend` → `frontend`, with a Postgres healthcheck gating backend startup.
- Pytest smoke tests (`tests/backend/test_health.py`).

### Option A — Docker (recommended)
```bash
cp .env.example .env
docker compose up --build
```
- Frontend: http://localhost:5173
- Backend + Swagger docs: http://localhost:8000/docs
- Postgres: localhost:5432

### Option B — Run locally without Docker

**Backend**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```
Without a running Postgres, `/api/health` reports `"database": "disconnected"` — the API still starts, since the DB connection is only checked, not required at boot.

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

### Testing
```bash
cd backend
pip install -r requirements.txt
pytest ../tests/backend -v
```

### Common errors
| Symptom | Cause | Fix |
|---|---|---|
| `port is already allocated` | Something else is using 5432/8000/5173 | Stop the conflicting process, or remap the host port in `docker-compose.yml` |
| Backend crashes immediately in Docker | Postgres not ready yet | Already handled via `depends_on: condition: service_healthy`; if it persists, check `docker compose logs postgres` |
| Frontend shows "Backend Unreachable" | Backend not running, or CORS origin mismatch | Confirm backend is up at `:8000`; check `cors_origins` in `backend/app/config.py` |
| `ModuleNotFoundError` running pytest | Wrong working directory / venv not activated | Run from `backend/` with the venv activated |

### Future improvements
Alembic migrations (replacing `create_all()`), multi-stage production Docker builds, reverse proxy/HTTPS termination.

## Phase 2 — Log Generation

A demo log generator simulates realistic incidents instead of random noise, so the (future)
correlation engine has logically-connected events to group. It writes newline-delimited JSON
to `logs/application.log` — the exact file a CloudWatch Agent will tail unchanged in Phase 3.
Nothing in this phase talks to AWS.

### Concepts
- **Workflow** (`backend/app/simulation/workflows/`): a baseline business flow. Currently just
  `ecommerce` (login → browse → cart → checkout).
- **Failure** (`backend/app/simulation/failures/`): an injectable tail appended after the
  workflow completes — `database_timeout`, `redis_failure`, `payment_api_timeout`,
  `auth_failure`, `cpu_spike`, `disk_full`, or `none` for a healthy run.
- Every run shares one `trace_id` across all its logs; runs with a failure also get an
  `incident_id`, so Phase 4's correlation engine can group by either.
- Simulations run as a background asyncio task and write one log line at a time, paced in
  real time (`speed: instant | fast | normal`), so `/api/simulation/status` and
  `/api/simulation/stop` reflect an actually-running simulation instead of a completed no-op.

### API
| Method | Path | Description |
|---|---|---|
| GET | `/api/simulation/workflows` | List available workflows |
| GET | `/api/simulation/failures` | List available failures (incl. `none`) |
| POST | `/api/simulation/start` | Body: `{"workflow": "ecommerce", "failure": "database_timeout", "speed": "fast"}` |
| POST | `/api/simulation/stop` | Cancel the running simulation |
| GET | `/api/simulation/status` | Current simulation state, trace/incident id, last log emitted |

```bash
curl -X POST http://localhost:8000/api/simulation/start \
  -H "Content-Type: application/json" \
  -d '{"workflow": "ecommerce", "failure": "database_timeout", "speed": "fast"}'

curl http://localhost:8000/api/simulation/status
```

## Phase 3 — Cloud Log Collection

Split into two independent pieces so a broken CloudWatch integration can never take down
log ingestion into PostgreSQL, and vice versa. Read [`docs/data_contract.md`](docs/data_contract.md)
first — it's the schema every module below and every future phase (correlation, timeline,
knowledge base, LLM) reads and writes.

**Phase 3A — CloudWatch Agent** (`docs/aws/`): ship `logs/application.log` into CloudWatch
Logs. No collector, no database writes — just confirm structured logs are visibly landing in
CloudWatch. Requires an AWS account; follow `docs/aws/cloudwatch_agent_setup.md`.

**Phase 3B — Collector** (`collector/`): an independent process that polls CloudWatch Logs,
normalizes each event into the Stored Log Record shape, deduplicates by CloudWatch's
`eventId`, and writes to the `logs` table with `processed = false`. See `collector/README.md`.

> **Note:** the `logs` table gained new columns (`incident_id`, `workflow`, `failure_type`,
> `source`, `source_event_id`, `processed`) in this phase. There's no Alembic yet
> (tables are created via `create_all()`, which won't alter an existing table) — if you
> already have a local Postgres volume from Phase 1/2, reset it: `docker compose down -v`
> then `docker compose up --build`.
