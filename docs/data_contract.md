# Data Contract

## Source modes

The stored record contract is source-independent. Local development uses
`application.log -> local collector -> PostgreSQL`; cloud deployment uses `Application ->
CloudWatch Agent -> CloudWatch Logs -> collector -> PostgreSQL`. The local adapter assigns a
stable hash-based `source_event_id`; the CloudWatch adapter preserves CloudWatch's `eventId`.
In both cases downstream correlation and timeline code only sees the Stored Log Record.

The canonical shape of a log event as it moves through the pipeline:

```
Demo App (simulation) → application.log → CloudWatch Agent → CloudWatch Logs
    → Collector (normalize + dedup) → PostgreSQL (logs table)
    → Correlation Engine → Incident Timeline → Knowledge Base → LLM → Dashboard
```

Every module from the collector onward — correlation engine, timeline generator, knowledge
base, LLM engine, dashboard — reads logs **only** in the "Stored Log Record" shape defined
below. None of them should special-case CloudWatch's envelope or the simulator's output
directly; that translation happens exactly once, in the collector.

## 1. Emitted log event (`application.log`, one JSON object per line)

Written by the demo app (`backend/app/simulation/`), and by any real service instrumented
the same way. This is also the exact byte content of the `message` field once CloudWatch
Agent ships the line.

| Field | Type | Nullable | Set by |
|---|---|---|---|
| `timestamp` | ISO-8601 string, UTC | no | emitter, at write time |
| `service` | string | no | emitter |
| `severity` | `INFO` \| `WARNING` \| `ERROR` | no | emitter |
| `message` | string | no | emitter |
| `host` | string | no | emitter |
| `trace_id` | string | no | emitter, one per simulation/request run |
| `incident_id` | string | **yes** | emitter, only set when a failure is injected |
| `workflow` | string | no | emitter, e.g. `ecommerce` |
| `failure_type` | string | **yes** | emitter, e.g. `database_timeout`; null for a healthy run |

```json
{
  "timestamp": "2026-08-06T17:16:35.568703+00:00",
  "service": "order-service",
  "severity": "ERROR",
  "message": "Database retry failed after 3 attempts",
  "host": "DESKTOP-J5E4M82",
  "trace_id": "1424c64fd0324e7584db42324ce147dc",
  "incident_id": "INC-36929A89",
  "workflow": "ecommerce",
  "failure_type": "database_timeout"
}
```

## 2. CloudWatch Log Event (Phase 3A)

CloudWatch wraps the line above; it does not know about our fields. `message` is the
emitted JSON **as a string**, unparsed:

```json
{
  "eventId": "37472847292...",
  "timestamp": 1786032995568,
  "message": "{\"timestamp\": \"2026-08-06T17:16:35.568703+00:00\", \"service\": \"order-service\", ...}",
  "logStreamName": "..."
}
```

The collector is the only module allowed to see this shape. `eventId` becomes
`source_event_id` below.

## 3. Stored Log Record (`logs` table, Phase 3B onward — the actual contract)

The collector parses `message`, validates it against section 1, and adds three
collector-owned bookkeeping fields before writing to Postgres:

| Field | Type | Nullable | Set by |
|---|---|---|---|
| `id` | integer, PK | no | Postgres |
| `timestamp` | timestamptz | no | from emitted event |
| `service` | string | no | from emitted event |
| `severity` | string | no | from emitted event |
| `message` | text | no | from emitted event |
| `host` | string | no | from emitted event |
| `trace_id` | string | no | from emitted event |
| `incident_id` | string | yes | from emitted event |
| `workflow` | string | yes | from emitted event |
| `failure_type` | string | yes | from emitted event |
| `source` | string | no | **collector**, e.g. `"cloudwatch"` |
| `source_event_id` | string, unique | yes | **collector**, CloudWatch's `eventId` — dedup key |
| `processed` | boolean, default `false` | no | **collector** sets `false` on insert; correlation engine flips to `true` after consuming |

This is the row shape every downstream module (correlation engine, timeline generator,
knowledge base, LLM engine, dashboard API) reads and must keep reading. If a field needs
to change, change it here first, then propagate — don't let an individual module invent
its own variant of a log record.

## Rules

1. `trace_id` is always present; `incident_id` and `failure_type` are only present when the
   event is part of an injected incident (a healthy run has both `null`).
2. The collector is the single place CloudWatch's envelope is unwrapped. Nothing past the
   collector imports `boto3` or knows CloudWatch exists.
3. Dedup is by `source_event_id`, not by content — CloudWatch can redeliver the same event
   on a retried `FilterLogEvents` page.
4. `processed = false` on insert; the correlation engine is the only writer that sets it
   `true`, and only after it has folded the row into an incident.
