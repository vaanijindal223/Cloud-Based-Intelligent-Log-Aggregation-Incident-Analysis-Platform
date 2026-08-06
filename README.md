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
- **Queue:** Apache Kafka (Docker)
- **Cloud:** AWS EC2, CloudWatch Logs, SNS, IAM, S3 (optional)
- **AI:** LangChain + OpenAI/Gemini API
- **Containers:** Docker, Docker Compose

## Project structure
```
backend/                FastAPI app (API, models, services, database)
frontend/                React + Vite + Tailwind dashboard
collector/                CloudWatch log collector            (Phase 3)
correlation_engine/       Groups logs into incidents           (Phase 4)
incident_builder/          Persists incidents                    (Phase 4)
timeline_engine/           Builds incident timelines              (Phase 5)
knowledge_base/            Historical incident storage/retrieval  (Phase 7)
llm_engine/                 Explainable AI (LangChain)              (Phase 8)
alert_service/               Smart SNS alerting                       (Phase 9)
docker/                       Shared infra config
docs/                          Design/reference docs
scripts/                        Helper/automation scripts
tests/                            Test suites
docker-compose.yml
```

## Phase progress
- [x] **Phase 1 — Project Setup**: FastAPI backend, React frontend, PostgreSQL, Docker Compose, all wired together
- [ ] Phase 2 — Log Generation
- [ ] Phase 3 — Cloud Log Collection
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
