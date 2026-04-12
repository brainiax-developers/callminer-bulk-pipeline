
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

module "cloudwatch_landing" {
  source = "./modules/cloudwatch"
  tags   = module.label.tags

  lambda_function_name     = module.landing_lambda.landing_function_name
  subscription_role_arn    = var.subscription_role_arn
  firehose_destination_arn = var.firehose_destination_arn
  lambda_destination_arn   = module.opsgenie_lambda.opsgenie_function_arn
  cwlog_lambda_permission  = [module.opsgenie_lambda.cwlog_lambda_permission]
  cwrerun_lambda_permission = [module.rerun_lambda.cwrerun_lambda_permission]
}

module "cloudwatch_transfer" {
  source = "./modules/cloudwatch"
  tags   = module.label.tags

  lambda_function_name     = module.transfer_lambda.transfer_function_name
  subscription_role_arn    = var.subscription_role_arn
  firehose_destination_arn = var.firehose_destination_arn
  lambda_destination_arn   = module.opsgenie_lambda.opsgenie_function_arn
  cwlog_lambda_permission  = [module.opsgenie_lambda.cwlog_lambda_permission]
  cwrerun_lambda_permission = [module.rerun_lambda.cwrerun_lambda_permission]
}

module "cloudwatch_events" {
  source = "./modules/cloudwatch"
  tags   = module.label.tags

  lambda_function_name     = module.events_lambda.events_function_name
  subscription_role_arn    = var.subscription_role_arn
  firehose_destination_arn = var.firehose_destination_arn
  lambda_destination_arn   = module.opsgenie_lambda.opsgenie_function_arn
  cwlog_lambda_permission  = [module.opsgenie_lambda.cwlog_lambda_permission]
  cwrerun_lambda_permission = [module.rerun_lambda.cwrerun_lambda_permission]
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

  iam_opsgenie_policy               = "./templates/callminer_opsgenie_policy.json"
  iam_step_functions_policy         = "./templates/step_functions_policy.json"
  iam_secret_manager_policy         = "./templates/secret_manager_policy.json"
  iam_s3_kms_secret_manager_policy  = "./templates/s3_kms_secret_manager_policy.json"
  iam_s3_kms_policy                 = "./templates/s3_kms_policy.json"
  assumedrole_policy                = "./templates/assumedrole_policy.json"
  iam_rerun_lambda_policy           = "./templates/rerun_lambda_policy.json"
  iam_bulkapi_scheduler_policy      = "./templates/bulkapi_scheduler_policy.json"
  bulkapi_auth_secret_name          = local.bulkapi_auth_secret_name


  # Kms for Decrypting and Encrypting
  kms_keys = [
    module.kms.sas_s3_key_arn,
    module.kms.landing_zone_key_arn
  ]

  landing_lambda_arn           = module.landing_lambda.landing_function_arn
  events_lambda_arn            = module.events_lambda.events_function_arn
  transfer_lambda_arn          = module.transfer_lambda.transfer_function_arn
  opsgenie_lambda_arn          = module.opsgenie_lambda.opsgenie_function_arn
  state_machine_arn            = module.step_functions.state_machine_arn
  step_function_event_rule_arn = module.step_functions.event_rule_arn
  rerun_lambda_arn             = module.rerun_lambda.rerun_function_arn
}

module "landing_lambda" {
  source           = "./modules/landing_lambda"
  environment      = var.environment
  filename         = local.payload_filename
  aws_account_id   = local.aws_account_id

  event_rule_arn   = module.step_functions.event_rule_arn
  landing_role_arn = module.iam.iam_landing_role_arn
}

module "events_lambda" {
  source      = "./modules/events_lambda"
  environment = var.environment
  filename    = local.payload_filename

  event_rule_arn  = module.step_functions.event_rule_arn
  events_role_arn = module.iam.iam_events_role_arn
}

module "opsgenie_lambda" {
  source      = "./modules/opsgenie_lambda"
  environment = var.environment

  opsgenie_role_arn = module.iam.iam_opsgenie_role_arn
  file_loc          = local.python_file_loc
  zipped_file_loc   = local.zipped_file_loc
  account_id        = local.aws_account_id
  log_group_arn = [
    module.cloudwatch_landing.log_group_arn,
    module.cloudwatch_events.log_group_arn,
    module.cloudwatch_transfer.log_group_arn,
    module.cloudwatch_bulkapi_scheduler.log_group_arn
  ]
}

module "transfer_lambda" {
  source      = "./modules/transfer_lambda"
  environment = var.environment
  filename    = local.payload_filename

  event_rule_arn    = module.step_functions.event_rule_arn
  transfer_role_arn = module.iam.iam_transfer_role_arn
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

module "step_functions" {
  source      = "./modules/step_functions"
  environment = var.environment
  tags        = module.label.tags

  aws_account_id      = local.aws_account_id
  step_functions_role = module.iam.aws_aws_iam_role_step_function_arn
  landing_lambda_arn  = module.landing_lambda.landing_function_arn
  events_lambda_arn   = module.events_lambda.events_function_arn
  transfer_lambda_arn = module.transfer_lambda.transfer_function_arn
}

module "kms" {
  source      = "./modules/kms"
  environment = var.environment
}
