output "bulkapi_scheduler_function_name" {
  value = aws_lambda_function.bulkapi_scheduler_lambda.function_name
}

output "bulkapi_scheduler_function_arn" {
  value = aws_lambda_function.bulkapi_scheduler_lambda.arn
}

output "event_rule_arn" {
  value = aws_cloudwatch_event_rule.bulkapi_scheduler_event_rule.arn
}
