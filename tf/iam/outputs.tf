output aws_iam_policy_secrets_manager_arn {
  value = aws_iam_policy.secrets_manager_policy.arn
}

output aws_aws_iam_policy_s3_kms_arn {
  value = aws_iam_policy.s3_kms_policy.arn
}

output aws_aws_iam_role_step_function_arn {
 value = aws_iam_role.step_functions_role.arn
}

output iam_landing_role_arn {
 value = aws_iam_role.callminer_landing_role.arn
}

output iam_events_role_arn {
  value = aws_iam_role.callminer_events_role.arn
}

output iam_transfer_role_arn {
 value = aws_iam_role.callminer_transfer_role.arn
}

output iam_opsgenie_role_arn {
 value = aws_iam_role.callminer_opsgenie_role.arn
}

output iam_rerun_role_arn {
 value = aws_iam_role.callminer_rerun_role.arn
}

output iam_bulkapi_scheduler_role_arn {
 value = aws_iam_role.callminer_bulkapi_scheduler_role.arn
}

output tmpf_kms_keys {
  value = local.tmpf_kms_keys
}
