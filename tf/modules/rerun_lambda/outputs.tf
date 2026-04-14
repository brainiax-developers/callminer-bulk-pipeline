output rerun_function_name {
  value = aws_lambda_function.rerun_lambda.function_name
}

output rerun_function_arn {
  value = aws_lambda_function.rerun_lambda.arn
}

output zipped_file_loc {
  value = data.archive_file.callminer_rerun.output_path
}

output cwlog_lambda_permission {
  value = aws_lambda_permission.allow_execution_from_event_rule[*]
}

output cwrerun_lambda_permission {
  value = aws_lambda_permission.allow_execution_from_cloudwatch[*]
}

