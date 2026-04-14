data aws_kms_key landing_kms_key {
  key_id = "alias/${var.environment}-hubs-data-landing-zone-enckey"
}

resource aws_lambda_function rerun_lambda {
  function_name                 = "${var.environment}-ingestion-callminer-rerun-lambda"
  role                          = var.rerun_role_arn
  filename                      = data.archive_file.callminer_rerun.output_path
  handler                       = "CallMinerLandingRerunLambda.lambda_handler"
  source_code_hash              = data.archive_file.callminer_rerun.output_base64sha256
  memory_size                   = "3008"
  runtime                       = "python3.12"
  timeout                       = "900"
  publish                       = true
  environment {
    variables = {
      step_function_arn = "arn:aws:states:eu-west-1:${var.aws_account_id}:stateMachine:${var.environment}_callminer"
      alarm_name = "${var.environment}-anomaly-detection-callminer-landing"
      MISSING_THRESHOLD_SNS_ARN = var.alert_sns_arn
    }
  }
}

resource aws_lambda_permission allow_execution_from_event_rule {
  statement_id                  = "AllowExecutionFromCloudWatch"
  action                        = "lambda:InvokeFunction"
  function_name                 = aws_lambda_function.rerun_lambda.function_name
  principal                     = "events.amazonaws.com"
  source_arn                    = var.event_rule_arn
}

resource "aws_lambda_permission" "allow_execution_from_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatchRerun"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rerun_lambda.function_name
  principal     = "lambda.alarms.cloudwatch.amazonaws.com"   # CloudWatch Alarms principal
}