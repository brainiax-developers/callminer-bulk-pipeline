output iam_bulkapi_scheduler_role_arn {
 value = aws_iam_role.callminer_bulkapi_scheduler_role.arn
}

output tmpf_kms_keys {
  value = local.tmpf_kms_keys
}
