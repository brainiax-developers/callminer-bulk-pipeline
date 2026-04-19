# callminer-bulk-pipeline

CallMiner BulkAPI scheduler for `PPLNS-7739`.

## Runtime Model

- AWS Lambda is deployed as a **container image** (`package_type = "Image"`).
- Image is built from the root [`Dockerfile`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/Dockerfile).
- Build-account and environment-account ECR copy flow is handled by:
  - [`buildspec-push.yaml`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/buildspec-push.yaml)
  - [`buildspec-pull.yaml`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/buildspec-pull.yaml)
  - [`Jenkinsfile`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/Jenkinsfile)

## Python Layout

Source is under one package root:

- [`src/callminer_bulk_pipeline/handlers/bulkapi_scheduler.py`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/src/callminer_bulk_pipeline/handlers/bulkapi_scheduler.py)

Test imports target the package path directly:

- [`tests/test_callminer_bulkapi_scheduler.py`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/tests/test_callminer_bulkapi_scheduler.py)

## Scheduler Behavior

- Reconciliation Lambda cadence: **daily** (`rate(1 day)` by default).
- CallMiner export job cadence: **hourly** (`0 0 * ? * *` in job template).
- Sync mode: finds configured job by name and creates/updates it.
- Rerun mode: creates one-off job by **omitting** the `Schedule` field and only allows `Duration` overrides plus naming/idempotency controls.

## Operational Defaults

Defaults are centralized in Terraform locals and can be overridden via variables.

- Duration defaults:
  - `SearchMode = "NewAndUpdated"`
  - `LastNHours = 1`
  - `LastNDays = null`
  - `TimeFrame = null`
  - `StartDate = null`
  - `EndDate = null`
- Storage target name: `${environment}-callminer-bulkapi-holding-target`
- Expected holding bucket: `${environment}-lakehouse-holding-zone`
- Expected holding prefix: `callminer/export/`
- Notification config is explicit:
  - `bulkapi_notification_method = "Email"` requires non-empty `bulkapi_notification_email_recipients`
  - `bulkapi_notification_method = "Webhook"` requires `bulkapi_notification_webhook_id`
  - Terraform and runtime validation enforce that exactly one notification path is configured.

Environment overrides live in:

- [`tf/config/dev/vars.tfvars`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/tf/config/dev/vars.tfvars)
- [`tf/config/test/vars.tfvars`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/tf/config/test/vars.tfvars)
- [`tf/config/prod/vars.tfvars`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/tf/config/prod/vars.tfvars)

## Terraform Structure

- Runtime stack: `tf/`
  - IAM role/policy for scheduler
  - Lambda (image-based)
  - EventBridge daily trigger
- Build/deploy ECR stack: `tf/deploy-build/`
  - ECR repo + SSM parameter for repo URL

## Local Validation

Run scheduler unit tests from repo root:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -q
```
