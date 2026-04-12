variable "environment" {
  type        = string
  description = "Deployment environment"
}

variable "region" {
  type        = string
  description = "AWS region"
  default     = "eu-west-1"
}

variable "created_by" {
  type        = string
  description = "Repository identifier for tagging"
  default     = "data/pipelines/lakehouse/core/callminer-bulk-pipeline"
}

variable "extra_tags" {
  type        = map(string)
  description = "Additional resource tags"
  default     = {}
}

variable "bulkapi_storage_target_name" {
  type        = string
  description = "CallMiner storage target name used by the export job"
}

variable "bulk_job_name" {
  type        = string
  description = "Optional explicit scheduled job name"
  default     = ""
}

variable "bulk_job_previous_name" {
  type        = string
  description = "Optional previous scheduled job name for rename fallback"
  default     = ""
}

variable "schedule_expression" {
  type        = string
  description = "EventBridge schedule for sync reconciliation"
  default     = "rate(1 day)"
}

variable "callminer_bulk_api_base_url" {
  type        = string
  description = "CallMiner Bulk API base URL"
  default     = "https://apiuk.callminer.net/bulkexport"
}

variable "callminer_idp_base_url" {
  type        = string
  description = "CallMiner IDP base URL"
  default     = "https://idpuk.callminer.net"
}

variable "callminer_bulk_scope" {
  type        = string
  description = "CallMiner OAuth scope for bulk export"
  default     = "https://callminer.net/auth/platform-bulkexport"
}

variable "log_level" {
  type        = string
  description = "Scheduler Lambda log level"
  default     = "INFO"
}
