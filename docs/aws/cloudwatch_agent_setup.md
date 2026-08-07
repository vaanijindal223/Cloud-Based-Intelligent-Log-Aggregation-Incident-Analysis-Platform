# Phase 3A — CloudWatch Agent Setup

**Scope:** ship `logs/application.log` into CloudWatch Logs. Nothing else. No collector,
no PostgreSQL writes — that's Phase 3B, and it depends on nothing here beyond a log group
name and read-only IAM credentials.

**Deliverable:** trigger a simulation (`POST /api/simulation/start`), then watch the same
JSON lines appear in CloudWatch Logs → Log groups → `/log-aggregator/application`.

This can't be run from this sandbox (no AWS CLI or credentials here) — follow it on your
own AWS account. Two ways to run the agent; pick one:

- **EC2** — matches production, needed for your final demo.
- **Local machine** — the agent supports on-prem/local hosts too. No EC2 cost, faster
  iteration while building Phase 3B. Switch to EC2 only once 3B works end-to-end.

## 1. Create the log group

```bash
aws logs create-log-group --log-group-name /log-aggregator/application
aws logs put-retention-policy --log-group-name /log-aggregator/application --retention-in-days 14
```

## 2. IAM

Create a policy from `docs/aws/iam-policy-cloudwatch-agent.json` (scoped to just this log
group — not the broad AWS-managed `CloudWatchAgentServerPolicy`).

```bash
aws iam create-policy \
  --policy-name LogAggregatorCloudWatchAgentWrite \
  --policy-document file://docs/aws/iam-policy-cloudwatch-agent.json
```

**EC2:** attach it to an instance role (`AmazonEC2RoleforCloudWatchAgent`-style setup) and
associate that role's instance profile with the EC2 instance running the demo app.

**Local machine:** create an IAM user with this policy attached, generate an access key,
and run `aws configure` so the agent's default credential chain picks it up. Don't reuse
your personal/root credentials for this — a scoped user makes it obvious in CloudTrail
exactly what the agent can and can't touch.

## 3. Install the agent

**EC2 (Ubuntu):** the agent ships as a `.deb`, not a yum package:
```bash
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
```

**EC2 (Amazon Linux 2023):**
```bash
sudo yum install -y amazon-cloudwatch-agent
```

**Local (Windows, matches this repo's dev environment):** download and run the MSI from
the [CloudWatch Agent downloads page](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/download-cloudwatch-agent-commandline.html).

## 4. Configure it

Copy `docs/aws/cloudwatch-agent-config.json`, and edit `file_path` to match where
`application.log` actually lands:
- EC2 (Ubuntu, this project's deployment target): wherever the repo is cloned under the
  `ubuntu` user's home, e.g.
  `/home/ubuntu/Cloud-Based-Intelligent-Log-Aggregation-Incident-Analysis-Platform/logs/application.log`
- EC2 (Amazon Linux): e.g. `/home/ec2-user/log-aggregator/logs/application.log`
- Local Windows dev: the repo's `logs\application.log`, e.g.
  `D:\Cloud-Based-Intelligent-Log-Aggregation-Incident-Analysis-Platform\logs\application.log`

Then start the agent pointing at that config:

```bash
# EC2 / Linux
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -s -c file:docs/aws/cloudwatch-agent-config.json

# Local Windows (adjust install path)
& "C:\Program Files\Amazon\AmazonCloudWatchAgent\amazon-cloudwatch-agent-ctl.ps1" `
  -a fetch-config -m onPremise -s -c file:docs/aws/cloudwatch-agent-config.json
```

## 5. Verify

```bash
curl -X POST http://localhost:8000/api/simulation/start \
  -H "Content-Type: application/json" \
  -d '{"workflow": "ecommerce", "failure": "database_timeout", "speed": "fast"}'
```

Then in the AWS Console: CloudWatch → Log groups → `/log-aggregator/application` → the
newest log stream. You should see the same JSON lines that land in `logs/application.log`,
arriving within a few seconds (the agent's default flush interval).

**Don't trust `DescribeLogStreams`'s `lastIngestionTime` for real-time verification** — it's
known to lag well behind actual delivery (observed several minutes stale even after fresh
events landed). To confirm delivery immediately after a config change, either check the
stream contents directly in the Console/`GetLogEvents`, or temporarily set `"debug": true`
under `agent` in the config and re-fetch — the agent then logs a line like `[outputs.cloudwatchlogs]
Pusher published N log events to group: ... in 38ms` on every successful flush. Revert the
debug flag (re-fetch the plain config) once confirmed; it's noisy for normal operation.

**Stop here.** Don't write collector code yet — confirm live streaming works first, since
if this step is broken, Phase 3B has nothing to read.
