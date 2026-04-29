variable "environment" {
  type        = string
  description = "The environment being deployed to"
}

variable "tags" {
  type        = map(string)
  description = "The associated tags"
}

variable "aws_account_id" {
  type        = string
  description = "The AWS ACCOUNT ID being deployed to"
}

variable "region" {
  type        = string
  description = "AWS region used for constructing ARNs"
}

variable "assumedrole_policy" {
  type        = string
  description = "The assumed role policy template for lambda and state machine"
}

variable "iam_bulkapi_scheduler_policy" {
  type        = string
  description = "The IAM policy template for the bulk API scheduler lambda"
}

variable "bulkapi_auth_secret_name" {
  type        = string
  description = "Secrets Manager secret name for CallMiner Bulk API OAuth credentials"
}
