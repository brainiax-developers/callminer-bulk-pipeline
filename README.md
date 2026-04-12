# CallMiner Bulk API Scheduler (PPLNS-7739)

Standalone repository for the CallMiner Bulk API scheduler Lambda.

The scheduler reconciles a configured CallMiner export job and supports controlled reruns for specific time periods.

## Scope

This repository intentionally contains only the PPLNS-7739 scheduler service.

Included:
- Create/update reconciliation for a scheduled CallMiner export job.
- Rerun job creation with strict duration-only overrides.
- Terraform for scheduler Lambda, IAM, and EventBridge schedule.
- Unit tests for scheduler logic.

Excluded:
- Legacy landing/transfer/events/rerun Lambdas.
- Legacy Step Functions orchestration.
- Container-image build/deploy flow.

## Repository Layout

- `src/CallMinerBulkApiSchedulerLambda.py` - Scheduler Lambda handler and CallMiner API client logic.
- `tests/test_callminer_bulkapi_scheduler.py` - Unit tests.
- `tf/` - Standalone Terraform for scheduler deployment.
- `.docs/callminer/` - Background Jira/context documents.

## Scheduler Behavior

### Sync mode (`mode=sync`, default)

1. Fetch OAuth token from CallMiner IDP (`/connect/token`).
2. List existing export jobs (`GET /api/export/job`).
3. Match by `BULK_JOB_NAME` and optional `BULK_JOB_PREVIOUS_NAME`.
4. If found, update job (`PUT /api/export/job/{id}`) using configured template.
5. If not found, create job (`POST /api/export/job`).

Optional `dry_run=true` returns intended action without mutating CallMiner.

### Rerun mode (`mode=rerun`)

Creates a one-off rerun job by cloning the configured template and forcing:
- `Schedule = null`
- `Duration` overridden by allowed time-period fields only.

Allowed rerun duration keys:
- `LastNDays`
- `LastNHours`
- `TimeFrame`
- `StartDate`
- `EndDate`

Protected fields (for example `StorageTargetName`, `DataTypes`, `SearchMode`) cannot be overridden via rerun input.

## Lambda Configuration (Environment Variables)

Required:
- `CALLMINER_AUTH_SECRET_NAME`
- `BULK_JOB_NAME`
- `BULK_JOB_TEMPLATE_JSON`

Optional:
- `BULK_JOB_PREVIOUS_NAME`
- `CALLMINER_BULK_API_BASE_URL` (default: `https://apiuk.callminer.net/bulkexport`)
- `CALLMINER_IDP_BASE_URL` (default: `https://idpuk.callminer.net`)
- `CALLMINER_BULK_SCOPE` (default: `https://callminer.net/auth/platform-bulkexport`)
- `LOG_LEVEL` (default: `INFO`)

Secret format for `CALLMINER_AUTH_SECRET_NAME`:

```json
{
  "client_id": "...",
  "client_secret": "..."
}
```

## Event Contract

### Sync (default)

```json
{}
```

```json
{
  "mode": "sync",
  "dry_run": true
}
```

### Rerun

```json
{
  "mode": "rerun",
  "request_id": "rerun-2026-03-01",
  "rerun": {
    "idempotency_key": "rerun-20260301",
    "duration": {
      "StartDate": "2026-03-01T00:00:00Z",
      "EndDate": "2026-03-01T23:59:59Z"
    }
  }
}
```

## Terraform

Terraform root: `tf/`

What it creates:
- Scheduler IAM role and policy.
- Scheduler Lambda function.
- EventBridge schedule and Lambda invoke permission.

Environment configs:
- `tf/config/dev/vars.tfvars`
- `tf/config/test/vars.tfvars`
- `tf/config/prod/vars.tfvars`

## CI/CD

`Jenkinsfile` runs:
1. Unit tests (`python -m unittest discover`).
2. `terraform init` (environment backend config).
3. `terraform validate`.
4. `terraform plan`.
5. Optional `terraform apply` or `terraform destroy` after manual approval.

## Local Testing

Run from repo root:

```bash
python -m unittest discover -s tests -p "test*.py" -v
```

## References

- `.docs/callminer/README.md`
- `.docs/callminer/PPLNS-7739.xml`
