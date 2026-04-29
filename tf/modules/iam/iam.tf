data "aws_partition" "current" {}

locals {
  bulkapi_secret_arn = "arn:${data.aws_partition.current.partition}:secretsmanager:${var.region}:${var.aws_account_id}:secret:${var.bulkapi_auth_secret_name}*"
}

resource "aws_iam_role" "callminer_bulkapi_scheduler_role" {
  name = "${var.environment}-hubs-data-bulkapi-scheduler-iamrole-callminer"
  assume_role_policy = templatefile("${var.assumedrole_policy}",
    {
      service_role = "lambda.amazonaws.com"
    }
  )
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "callminer_bulkapi_scheduler_role_policy" {
  role       = aws_iam_role.callminer_bulkapi_scheduler_role.name
  policy_arn = aws_iam_policy.bulkapi_scheduler_policy.arn
}

resource "aws_iam_policy" "bulkapi_scheduler_policy" {
  name = "${var.environment}-bulkapi-scheduler-lambda-policy"
  policy = templatefile("${var.iam_bulkapi_scheduler_policy}",
    {
      environment        = var.environment,
      account_id         = var.aws_account_id,
      bulkapi_secret_arn = local.bulkapi_secret_arn
    }
  )
}
