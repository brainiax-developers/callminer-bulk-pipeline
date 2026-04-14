data aws_secretsmanager_secret_version callminer_bulkapi_credentials {
  secret_id = var.bulkapi_auth_secret_name
}

# resource aws_iam_policy secrets_manager_policy {
#   name   = "${var.environment}-ds-ingestion-callminer-secrets-manager-policy"
#   policy = templatefile("${var.iam_secret_manager_policy}",
#     {
#       environment            = var.environment,
#       account_id             = var.aws_account_id,
#       tmp_kms_keys           = local.tmpf_kms_keys,
#       secret_mgr_credentials = data.aws_secretsmanager_secret_version.callminer_credentials.arn,
#       tmp_alert_sns_arn      = var.alert_sns_arn
#     }
#   )
# }

# resource aws_iam_policy s3_kms_secret_manager_policy {
#   name   = "${var.environment}-ds-ingestion-callminer-s3-kms-secret-manager-policy"
#   policy = templatefile("${var.iam_s3_kms_secret_manager_policy}",
#     {
#       environment               = var.environment,
#       account_id                = var.aws_account_id,
#       tmp_kms_keys              = local.tmpf_kms_keys,
#       secretsmgr_secret_version = data.aws_secretsmanager_secret_version.callminer_credentials.arn
#     }
#   )
# }


# resource aws_iam_policy s3_kms_policy {
#   name   = "${var.environment}-ds-ingestion-callminer-s3-kms-policy"
#   policy = templatefile("${var.iam_s3_kms_policy}",
#     {
#       environment  = var.environment,
#       account_id   = var.aws_account_id,
#       tmp_kms_keys = local.tmpf_kms_keys
#     }
#   )
# }


resource aws_iam_role callminer_bulkapi_scheduler_role {
  name = "${var.environment}-hubs-data-bulkapi-scheduler-iamrole-callminer"
  assume_role_policy = templatefile("${var.assumedrole_policy}",
    {
      service_role = "lambda.amazonaws.com"
    }
  )
  tags = var.tags
}

resource aws_iam_role_policy_attachment callminer_bulkapi_scheduler_role_policy {
  role       = aws_iam_role.callminer_bulkapi_scheduler_role.name
  policy_arn = aws_iam_policy.bulkapi_scheduler_policy.arn
}

resource aws_iam_policy bulkapi_scheduler_policy {
  name   = "${var.environment}-bulkapi-scheduler-lambda-policy"
  policy = templatefile("${var.iam_bulkapi_scheduler_policy}",
    {
      environment        = var.environment,
      account_id         = var.aws_account_id,
      bulkapi_secret_arn = data.aws_secretsmanager_secret_version.callminer_bulkapi_credentials.arn
    }
  )
}
