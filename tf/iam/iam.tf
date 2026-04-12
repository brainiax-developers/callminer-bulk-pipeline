data aws_secretsmanager_secret_version callminer_credentials {
  secret_id = var.environment != "prod" ? "${var.environment}-hubs-basetier-land-ds-ingestion-callminer-landing-creds-nonprod-only" : "${var.environment}-hubs-basetier-land-ds-ingestion-callminer-landing-creds"
}

data aws_secretsmanager_secret_version callminer_bulkapi_credentials {
  secret_id = var.bulkapi_auth_secret_name
}

resource aws_iam_role callminer_landing_role {
  name = "${var.environment}-hubs-data-landing-iamrole-callminer"
  assume_role_policy = templatefile("${var.assumedrole_policy}",
    {
      service_role = "lambda.amazonaws.com"
    }
  )
  tags = var.tags
}

resource aws_iam_policy secrets_manager_policy {
  name   = "${var.environment}-ds-ingestion-callminer-secrets-manager-policy"
  policy = templatefile("${var.iam_secret_manager_policy}",
    {
      environment            = var.environment,
      account_id             = var.aws_account_id,
      tmp_kms_keys           = local.tmpf_kms_keys,
      secret_mgr_credentials = data.aws_secretsmanager_secret_version.callminer_credentials.arn,
      tmp_alert_sns_arn      = var.alert_sns_arn
    }
  )
}

resource aws_iam_role callminer_events_role {
  name = "${var.environment}-hubs-data-events-iamrole-callminer"
  assume_role_policy = templatefile("${var.assumedrole_policy}",
    {
      service_role = "lambda.amazonaws.com"
    }
  )
  tags = var.tags
}

resource aws_iam_policy s3_kms_secret_manager_policy {
  name   = "${var.environment}-ds-ingestion-callminer-s3-kms-secret-manager-policy"
  policy = templatefile("${var.iam_s3_kms_secret_manager_policy}",
    {
      environment               = var.environment,
      account_id                = var.aws_account_id,
      tmp_kms_keys              = local.tmpf_kms_keys,
      secretsmgr_secret_version = data.aws_secretsmanager_secret_version.callminer_credentials.arn
    }
  )
}

resource aws_iam_role callminer_transfer_role {
  name = "${var.environment}-hubs-data-transfer-iamrole-callminer"
  assume_role_policy = templatefile("${var.assumedrole_policy}",
    {
      service_role = "lambda.amazonaws.com"
    }
  )
  tags = var.tags
}

resource aws_iam_policy s3_kms_policy {
  name   = "${var.environment}-ds-ingestion-callminer-s3-kms-policy"
  policy = templatefile("${var.iam_s3_kms_policy}",
    {
      environment  = var.environment,
      account_id   = var.aws_account_id,
      tmp_kms_keys = local.tmpf_kms_keys
    }
  )
}

resource aws_iam_role callminer_rerun_role {
  name = "${var.environment}-hubs-data-rerun-iamrole-callminer"
  assume_role_policy = templatefile("${var.assumedrole_policy}",
    {
      service_role = "lambda.amazonaws.com"
    }
  )
  tags = var.tags
}

resource aws_iam_role callminer_bulkapi_scheduler_role {
  name = "${var.environment}-hubs-data-bulkapi-scheduler-iamrole-callminer"
  assume_role_policy = templatefile("${var.assumedrole_policy}",
    {
      service_role = "lambda.amazonaws.com"
    }
  )
  tags = var.tags
}

resource aws_iam_role_policy_attachment callminer_landing_role_policy {
  role       = aws_iam_role.callminer_landing_role.name
  policy_arn = aws_iam_policy.secrets_manager_policy.arn
}

resource aws_iam_role_policy_attachment callminer_events_role_policy {
  role       = aws_iam_role.callminer_events_role.name
  policy_arn = aws_iam_policy.s3_kms_secret_manager_policy.arn
}

resource aws_iam_role_policy_attachment callminer_transfer_role_policy {
  role       = aws_iam_role.callminer_transfer_role.name
  policy_arn = aws_iam_policy.s3_kms_policy.arn
}

resource aws_iam_role_policy_attachment callminer_rerun_role_policy {
  role       = aws_iam_role.callminer_rerun_role.name
  policy_arn = aws_iam_policy.rerun_lambda_policy.arn
}

resource aws_iam_role_policy_attachment callminer_bulkapi_scheduler_role_policy {
  role       = aws_iam_role.callminer_bulkapi_scheduler_role.name
  policy_arn = aws_iam_policy.bulkapi_scheduler_policy.arn
}

resource aws_iam_role step_functions_role {
  name = "${var.name}_callminer_step_functions_role"
  assume_role_policy = templatefile("${var.assumedrole_policy}",
    {
      service_role = "states.amazonaws.com"
    }
  )
  tags = var.tags
}

resource aws_iam_role_policy_attachment step_functions_role_policy {
  role       = aws_iam_role.step_functions_role.name
  policy_arn = aws_iam_policy.step_functions_policy.arn
}

resource aws_iam_policy step_functions_policy {
  name   = "${var.environment}-ds-ingestion-callminer-step-functions-policy"
  policy = templatefile("${var.iam_step_functions_policy}",
    {
      environment                      = var.environment,
      tmp_step_function_event_rule_arn = var.step_function_event_rule_arn,
      tmp_state_machine_arn            = var.state_machine_arn,
      tmp_landing_lambda_arn           = var.landing_lambda_arn,
      tmp_events_lambda_arn            = var.events_lambda_arn,
      tmp_transfer_lambda_arn          = var.transfer_lambda_arn,
      tmp_landing_role_arn             = aws_iam_role.callminer_landing_role.arn,
      tmp_alert_sns_arn                = var.alert_sns_arn
    }
  )
}

resource aws_iam_role callminer_opsgenie_role {
  name = "${var.environment}-callminer-opsgenie-role"
  assume_role_policy = templatefile("${var.assumedrole_policy}",
    {
      service_role = "lambda.amazonaws.com"
    }
  )
  tags = var.tags
}

resource aws_iam_policy callminer_opsgenie_policy {
  name   = "${var.environment}-callminer-opsgenie-policy"
  policy = templatefile("${var.iam_opsgenie_policy}",
    {
      environment               = var.environment,
      account_id                = var.aws_account_id,
      tmp_kms_keys              = local.tmpf_kms_keys,
      secretsmgr_secret_version = data.aws_secretsmanager_secret_version.callminer_credentials.arn,
      tmp_alert_sns_arn         = var.alert_sns_arn
    }
  )
}

resource aws_iam_policy rerun_lambda_policy {
  name   = "${var.environment}-rerun-lambda-policy"
  policy = templatefile("${var.iam_rerun_lambda_policy}",
    {
      environment               = var.environment,
      account_id                = var.aws_account_id,
      tmp_kms_keys              = local.tmpf_kms_keys,
      tmp_alert_sns_arn         = var.alert_sns_arn,
      secretsmgr_secret_version = data.aws_secretsmanager_secret_version.callminer_credentials.arn
    }
  )
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

resource aws_iam_role_policy_attachment callminer_opsgenie {
  policy_arn = aws_iam_policy.callminer_opsgenie_policy.arn
  role       = aws_iam_role.callminer_opsgenie_role.name
}
