resource "aws_lambda_function" "bulkapi_scheduler_lambda" {
  function_name    = "${var.environment}-ingestion-callminer-bulkapi-scheduler"
  description      = "Lambda function for reconciling CallMiner BulkAPI export jobs and triggering reruns."
  role             = var.scheduler_role_arn
  filename         = data.archive_file.callminer_bulkapi_scheduler.output_path
  source_code_hash = data.archive_file.callminer_bulkapi_scheduler.output_base64sha256
  handler          = "CallMinerBulkApiSchedulerLambda.lambda_handler"
  runtime          = "python3.12"
  memory_size      = 512
  timeout          = 900
  publish          = true

  environment {
    variables = {
      CALLMINER_BULK_API_BASE_URL = "https://apiuk.callminer.net/bulkexport"
      CALLMINER_IDP_BASE_URL      = "https://idpuk.callminer.net"
      CALLMINER_BULK_SCOPE        = "https://callminer.net/auth/platform-bulkexport"
      CALLMINER_AUTH_SECRET_NAME  = var.auth_secret_name
      BULK_JOB_NAME               = var.bulk_job_name
      BULK_JOB_PREVIOUS_NAME      = var.bulk_job_previous_name
      LOG_LEVEL                   = "INFO"
      BULK_JOB_TEMPLATE_JSON      = var.bulk_job_template_json
      EXPECTED_HOLDING_BUCKET     = var.holding_bucket_name
      EXPECTED_HOLDING_PREFIX     = var.holding_prefix
    }
  }
}

resource "aws_cloudwatch_event_rule" "bulkapi_scheduler_event_rule" {
  name                = "${var.environment}_callminer_bulkapi_scheduler_event_rule"
  description         = "How often the CallMiner BulkAPI scheduler should reconcile jobs"
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "bulkapi_scheduler_event_target" {
  target_id = "${var.environment}_callminer_bulkapi_scheduler"
  rule      = aws_cloudwatch_event_rule.bulkapi_scheduler_event_rule.name
  arn       = aws_lambda_function.bulkapi_scheduler_lambda.arn
}

resource "aws_lambda_permission" "allow_execution_from_event_rule" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bulkapi_scheduler_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.bulkapi_scheduler_event_rule.arn
}
