# Terraform Notes (`tf/`)

This directory is the runtime stack for the CallMiner BulkAPI scheduler Lambda.

## What It Deploys

- IAM role + policy for scheduler Lambda access to Secrets Manager + CloudWatch logs
- Lambda function deployed from a **container image**
- EventBridge rule/target to run the scheduler daily

## Container Image Wiring

- Lambda uses `package_type = "Image"` in [`modules/bulkapi_scheduler_lambda/lambda.tf`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/tf/modules/bulkapi_scheduler_lambda/lambda.tf).
- Image URI is resolved from SSM parameter:
  - `/terraform/${environment}/lakehouse/callminer_bulk_pipeline_ecr_repo_url`
  - final URI: `<repo_url>:<image_version>`

## PPLNS-7739 Defaults

Set in [`local.tf`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/tf/local.tf):

- Scheduler reconcile cadence (Lambda/EventBridge): `rate(1 day)`
- Export job schedule (CallMiner cron): `0 0/20 * ? * *`
- Storage target name default: `${environment}-callminer-bulkapi-holding-target`
- Expected holding destination default:
  - bucket: `${environment}-lakehouse-holding-zone`
  - prefix: `callminer/export/`

Environment-specific overrides:

- [`config/dev/vars.tfvars`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/tf/config/dev/vars.tfvars)
- [`config/test/vars.tfvars`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/tf/config/test/vars.tfvars)
- [`config/prod/vars.tfvars`](/C:/Users/abhis/OneDrive/Desktop/MY%20FILES/Github/callminer-bulk-pipeline/tf/config/prod/vars.tfvars)

## Variables You Must Provide

- `environment`
- `image_version`

`image_version` is the ECR image tag for the scheduler container to deploy.

## Build/ECR Stack

ECR repo + repo URL SSM parameter are managed in `tf/deploy-build/`.
