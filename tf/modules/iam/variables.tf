variable environment {
  type        = string
  description = "The environment being deployed to"
}

variable tags {
  type        = map(string)
  description = "The associated tags"
}

variable name {
  type        = string
  description = "Name generated from label module"
}

variable rerun_lambda_arn {
  type        = string
  description = "ARN of the callminer rerun lambda function"
}

variable aws_account_id {
  type        = string
  description = "The AWS ACCOUNT ID being deployed to"
}

variable kms_keys {
  type       = list(string)
  description = "A list of kms keys to give permissions to"
}

variable iam_secret_manager_policy {
  type        = string
  description = "The IAM policy template for the secret manager  "
}

variable iam_s3_kms_secret_manager_policy {
  type        = string
  description = "The IAM policy template for the s3_kms secret manager "
}

variable iam_s3_kms_policy {
  type        = string
  description = "The IAM policy template for the s3_kms "
}

variable assumedrole_policy {
  type        = string
  description = "The assumed role policy template for lambda and state machine"
}

variable iam_rerun_lambda_policy {
  type        = string
  description = "The IAM policy template for the rerun_lambda"
}

variable iam_bulkapi_scheduler_policy {
  type        = string
  description = "The IAM policy template for the bulk API scheduler lambda"
}

variable bulkapi_auth_secret_name {
  type        = string
  description = "Secrets Manager secret name for CallMiner Bulk API OAuth credentials"
}
