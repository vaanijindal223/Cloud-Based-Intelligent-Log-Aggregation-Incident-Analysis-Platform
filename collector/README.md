# Collector — Phase 3B

Polls AWS CloudWatch Logs, normalizes each event into the [Stored Log Record](../docs/data_contract.md)
shape, and writes it to the `logs` table in PostgreSQL. Independent of the backend process —
if CloudWatch or the collector breaks, the FastAPI app and simulation module keep working;
only new log ingestion pauses.

Depends on Phase 3A having a log group actually receiving events
(`docs/aws/cloudwatch_agent_setup.md`). Doesn't touch AWS IAM/agent setup itself.

## How it works

- `cloudwatch_client.py` — calls `FilterLogEvents` against `log_group_name`, paginating via `nextToken`.
- `normalizer.py` — parses each event's `message` (our JSON line) into a Stored Log Record row;
  drops anything that fails to parse or is missing a required field, rather than failing the batch.
- `db.py` — a standalone `logs` table definition mirroring `backend/app/models/log.py` (the
  collector doesn't import the backend package or create/migrate tables — the backend owns
  the schema). Inserts use `INSERT ... ON CONFLICT (source_event_id) DO NOTHING` for dedup.
- `collector.py` — the poll loop. Each cycle: read the checkpoint (`MAX(timestamp)` of
  already-stored CloudWatch rows, minus a small overlap window), fetch events since then,
  normalize, insert.

No separate checkpoint table — the checkpoint is derived from what's already in `logs`, so a
collector restart can't drift from what's actually been persisted. The overlap window plus
`source_event_id` dedup means re-fetching the same event twice is harmless.

## Local development

Compose starts this service with `LOG_SOURCE=local` and mounts the same `./logs` directory as
the backend. The development flow is:

```
Simulation -> logs/application.log -> local collector -> PostgreSQL -> correlation -> incident/timeline
```

The collector polls every two seconds. It safely rescans the file after a restart because the
unique `source_event_id` constraint prevents previously inserted lines from being duplicated.

## CloudWatch mode

CloudWatch remains the production/demo cloud architecture. Set `LOG_SOURCE=cloudwatch` and
configure the standard boto3 credentials, region, and log group:

```
Application -> CloudWatch Agent -> CloudWatch Logs -> CloudWatch collector -> PostgreSQL
```

## Running it

```bash
python -m venv collector\.venv
collector\.venv\Scripts\activate        # Windows
pip install -r collector\requirements.txt
# Set DATABASE_URL and LOG_SOURCE in .env (use localhost as the host DB address).
python -m collector.collector --once     # one poll cycle, for testing
python -m collector.collector            # continuous polling loop
```

AWS credentials come from boto3's default chain (env vars, `~/.aws/credentials`, or an EC2
instance role) — nothing is hardcoded. The collector only needs read access to the log group;
don't reuse the CloudWatch Agent's write-only policy. Minimal read policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["logs:FilterLogEvents", "logs:DescribeLogStreams"],
      "Resource": "arn:aws:logs:*:*:log-group:/log-aggregator/*:*"
    }
  ]
}
```

## Testing

```bash
cd collector
pytest tests/ -v
```

Tests mock both `boto3` and the database — no AWS credentials or live Postgres required to
run them.
