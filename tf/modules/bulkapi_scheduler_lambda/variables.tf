variable "environment" {
  type        = string
  description = "The environment being deployed to"
}

variable "image_uri" {
  type        = string
  description = "Lambda container image URI including tag"
}

variable "scheduler_role_arn" {
  type        = string
  description = "ARN of the IAM role used by the bulk API scheduler lambda"
}

variable "auth_secret_name" {
  type        = string
  description = "Secrets Manager secret name containing CallMiner BulkAPI client credentials"
}

variable "bulk_job_name" {
  type        = string
  description = "Primary CallMiner Bulk API export job name to reconcile"
}

variable "bulk_job_previous_name" {
  type        = string
  description = "Optional previous job name used for rename migration fallback"
  default     = ""
}

variable "bulk_job_template_json" {
  type        = string
  description = "Baseline export job payload JSON used for sync/rerun operations"
}

variable "schedule_expression" {
  type        = string
  description = "EventBridge schedule expression for scheduler sync mode"
  default     = "rate(1 day)"
}
