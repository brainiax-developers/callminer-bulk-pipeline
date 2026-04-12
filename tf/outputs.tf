output "bulkapi_scheduler_lambda_name" {
  description = "Scheduler Lambda function name"
  value       = module.bulkapi_scheduler_lambda.bulkapi_scheduler_function_name
}

output "bulkapi_scheduler_lambda_arn" {
  description = "Scheduler Lambda function ARN"
  value       = module.bulkapi_scheduler_lambda.bulkapi_scheduler_function_arn
}

output "bulkapi_scheduler_event_rule_arn" {
  description = "EventBridge rule ARN for scheduler reconciliation"
  value       = module.bulkapi_scheduler_lambda.event_rule_arn
}

output "bulkapi_scheduler_role_arn" {
  description = "IAM role ARN used by the scheduler Lambda"
  value       = aws_iam_role.callminer_bulkapi_scheduler_role.arn
}
