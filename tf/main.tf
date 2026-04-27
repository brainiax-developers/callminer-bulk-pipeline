
data "aws_caller_identity" "here" {}

module "label" {
  source         = "git@git.tech.theverygroup.com:data/platform/modules/terraform/label.git?ref=v1.0.0"
  environment    = var.environment
  project        = var.project
  usage          = var.usage
  category       = var.category
  component      = var.component
  name_separator = "-"

  extra_tags = {
    "created_by" = var.created_by
  }
}

module "iam" {
  source            = "./modules/iam"
  environment       = var.environment
  aws_account_id    = local.aws_account_id
  tags              = module.label.tags

  assumedrole_policy           = "./templates/assumedrole_policy.json"
  iam_bulkapi_scheduler_policy = "./templates/bulkapi_scheduler_policy.json"
  bulkapi_auth_secret_name     = local.bulkapi_auth_secret_name
}

module "bulkapi_scheduler_lambda" {
  source                 = "./modules/bulkapi_scheduler_lambda"
  environment            = var.environment
  image_uri              = "${module.ecr.ecr_repository_url}:${var.image_version}"
  scheduler_role_arn     = module.iam.iam_bulkapi_scheduler_role_arn
  auth_secret_name       = local.bulkapi_auth_secret_name
  bulk_job_name          = local.bulkapi_job_name
  bulk_job_previous_name = var.bulk_job_previous_name
  bulk_job_template_json = local.bulkapi_job_template_json
  schedule_expression    = local.scheduler_reconcile_schedule
}
