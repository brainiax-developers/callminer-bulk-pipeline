
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

module "cloudwatch_bulkapi_scheduler" {
  source = "./modules/cloudwatch"
  tags   = module.label.tags

  lambda_function_name      = module.bulkapi_scheduler_lambda.bulkapi_scheduler_function_name
  subscription_role_arn     = var.subscription_role_arn
  firehose_destination_arn  = var.firehose_destination_arn
  lambda_destination_arn    = module.opsgenie_lambda.opsgenie_function_arn
  cwlog_lambda_permission   = [module.opsgenie_lambda.cwlog_lambda_permission]
  cwrerun_lambda_permission = [module.rerun_lambda.cwrerun_lambda_permission]
}

module "iam" {
  source            = "./modules/iam"
  environment       = var.environment
  aws_account_id    = local.aws_account_id
  tags              = module.label.tags
  name              = module.label.name
  alert_sns_arn     = module.opsgenie_lambda.alert_sns_arn

  assumedrole_policy                = "./templates/assumedrole_policy.json"
  iam_rerun_lambda_policy           = "./templates/rerun_lambda_policy.json"
  iam_bulkapi_scheduler_policy      = "./templates/bulkapi_scheduler_policy.json"
  bulkapi_auth_secret_name          = local.bulkapi_auth_secret_name

  # kms_keys = [
  #   module.kms.sas_s3_key_arn,
  #   module.kms.landing_zone_key_arn
  # ]

  rerun_lambda_arn             = module.rerun_lambda.rerun_function_arn
}

module "rerun_lambda" {
  source      = "./modules/rerun_lambda"
  environment = var.environment
  filename    = local.payload_filename
  aws_account_id  = local.aws_account_id

  event_rule_arn  = module.step_functions.event_rule_arn
  rerun_role_arn = module.iam.iam_rerun_role_arn
  file_loc          = local.python_file_loc
  zipped_file_loc   = local.zipped_file_loc
  alert_sns_arn     = module.opsgenie_lambda.alert_sns_arn
}

module "bulkapi_scheduler_lambda" {
  source                  = "./modules/bulkapi_scheduler_lambda"
  environment             = var.environment
  file_loc                = local.python_file_loc
  zipped_file_loc         = local.zipped_file_loc
  scheduler_role_arn      = module.iam.iam_bulkapi_scheduler_role_arn
  auth_secret_name        = local.bulkapi_auth_secret_name
  bulk_job_name           = "${var.environment}-callminer-bulkapi-export-job"
  bulk_job_previous_name  = ""
  bulk_job_template_json  = local.bulkapi_job_template_json
  holding_bucket_name     = local.bulkapi_holding_bucket_name
  holding_prefix          = local.bulkapi_holding_prefix
}

module "kms" {
  source      = "./modules/kms"
  environment = var.environment
}
