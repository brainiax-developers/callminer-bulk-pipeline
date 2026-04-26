variable environment {
  type        = string
  description = "The current working environment"
}

variable project {
  type        = string
  description = "The project the work belongs to"
}

variable service_owner {
  type        = string
  description = "TVG mandatory tag value: service owner"
  default     = ""
}

variable service {
  type        = string
  description = "TVG mandatory tag value: service"
  default     = ""
}

variable business_capability_l0 {
  type        = string
  description = "TVG mandatory tag value: business capability level 0"
  default     = ""
}

variable business_capability_l1 {
  type        = string
  description = "TVG mandatory tag value: business capability level 1"
  default     = ""
}

variable service_tier {
  type        = string
  description = "TVG mandatory tag value: service tier"
  default     = ""
}

variable data_classification {
  type        = string
  description = "TVG mandatory tag value: data classification"
  default     = ""
}

variable usage {
  type        = string
  default     = ""
}

variable category {
  type        = string
  description = "The category of the project"
  default     = "ingestion"
}

variable component {
  type        = string
  description = "The component of the project"
  default     = "landing"
}

variable created_by {
  type        = string
  description = "The repo this work is contained in"
  default     = "data/pipelines/lakehouse/jobs/callminer"
}

variable image_version {
  type        = string
  description = "Container image tag used for the scheduler Lambda deployment."
}

variable bulk_job_previous_name {
  type        = string
  description = "Optional previous job name used as a migration fallback when reconciling."
  default     = ""
}

variable bulkapi_storage_target_name {
  type        = string
  description = "CallMiner Bulk API storage target name that maps to the holding zone export destination."
  default     = ""
}

variable bulkapi_holding_bucket_name {
  type        = string
  description = "Expected CallMiner holding destination bucket."
  default     = ""
}

variable bulkapi_holding_prefix {
  type        = string
  description = "Expected CallMiner holding destination prefix."
  default     = ""
}

variable bulkapi_export_job_schedule {
  type        = string
  description = "Quartz cron expression for CallMiner BulkAPI export schedule."
  default     = ""
}

variable scheduler_reconcile_schedule_expression {
  type        = string
  description = "EventBridge schedule expression for the daily scheduler reconciliation Lambda run."
  default     = ""
}

variable bulkapi_notification_method {
  type        = string
  description = "Notification method for CallMiner export jobs. Allowed values: Email or Webhook."

  validation {
    condition     = contains(["Email", "Webhook"], var.bulkapi_notification_method)
    error_message = "bulkapi_notification_method must be either 'Email' or 'Webhook'."
  }
}

variable bulkapi_notification_email_recipients {
  type        = list(string)
  description = "Notification email recipients when bulkapi_notification_method is Email."
  default     = []
}

variable bulkapi_notification_webhook_id {
  type        = string
  description = "Webhook id when bulkapi_notification_method is Webhook."
  default     = ""
}
