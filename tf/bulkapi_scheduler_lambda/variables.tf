variable "environment" {
  type        = string
  description = "The environment being deployed to"
}

variable "file_loc" {
  type        = string
  description = "Source location of Python scheduler code"
}

variable "zipped_file_loc" {
  type        = string
  description = "Output location of zipped Python artifacts"
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

variable "bulk_api_base_url" {
  type        = string
  description = "Base URL for CallMiner Bulk Export API"
  default     = "https://apiuk.callminer.net/bulkexport"
}

variable "idp_base_url" {
  type        = string
  description = "Base URL for CallMiner IDP token endpoint"
  default     = "https://idpuk.callminer.net"
}

variable "bulk_scope" {
  type        = string
  description = "OAuth scope used for CallMiner Bulk Export access token"
  default     = "https://callminer.net/auth/platform-bulkexport"
}

variable "log_level" {
  type        = string
  description = "Lambda log level"
  default     = "INFO"
}

variable "schedule_expression" {
  type        = string
  description = "EventBridge schedule expression for scheduler sync mode"
  default     = "rate(1 day)"
}
