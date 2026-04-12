data "aws_caller_identity" "current" {}

data "aws_secretsmanager_secret" "callminer_bulkapi_credentials" {
  name = local.bulkapi_auth_secret_name
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "callminer_bulkapi_scheduler_role" {
  name               = local.scheduler_role_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.tags
}

resource "aws_iam_policy" "bulkapi_scheduler_policy" {
  name = "${var.environment}-bulkapi-scheduler-lambda-policy"
  policy = templatefile("${path.module}/bulkapi_scheduler_policy.json", {
    environment        = var.environment
    account_id         = data.aws_caller_identity.current.account_id
    bulkapi_secret_arn = data.aws_secretsmanager_secret.callminer_bulkapi_credentials.arn
  })
}

resource "aws_iam_role_policy_attachment" "callminer_bulkapi_scheduler_role_policy" {
  role       = aws_iam_role.callminer_bulkapi_scheduler_role.name
  policy_arn = aws_iam_policy.bulkapi_scheduler_policy.arn
}

module "bulkapi_scheduler_lambda" {
  source          = "./bulkapi_scheduler_lambda"
  environment     = var.environment
  file_loc        = local.python_file_loc
  zipped_file_loc = local.zipped_file_loc

  scheduler_role_arn = aws_iam_role.callminer_bulkapi_scheduler_role.arn
  auth_secret_name   = local.bulkapi_auth_secret_name

  bulk_job_name          = local.bulkapi_job_name
  bulk_job_previous_name = var.bulk_job_previous_name
  bulk_job_template_json = local.bulkapi_job_template_json

  bulk_api_base_url   = var.callminer_bulk_api_base_url
  idp_base_url        = var.callminer_idp_base_url
  bulk_scope          = var.callminer_bulk_scope
  schedule_expression = var.schedule_expression
  log_level           = var.log_level
}
