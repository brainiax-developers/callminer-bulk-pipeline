data "aws_caller_identity" "here" {}

module "label" {
  source                 = "git@git.tech.theverygroup.com:pe/public/tf-modules/pe-tf-module-tag.git?ref=v1.6.0"
  environment            = var.environment
  project                = var.project
  category               = var.category
  service_owner          = var.service_owner
  service                = var.service
  business_capability_l0 = var.business_capability_l0
  business_capability_l1 = var.business_capability_l1
  service_tier           = var.service_tier
  data_classification    = var.data_classification
  # name_separator = "-"
  created_by = var.created_by
}


module "iam" {
  source         = "./modules/iam"
  environment    = var.environment
  region         = var.region
  aws_account_id = local.aws_account_id
  tags           = module.label.tags

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
