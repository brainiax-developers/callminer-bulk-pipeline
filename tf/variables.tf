variable environment {
  type        = string
  description = "The current working environment"
}

variable project {
  type        = string
  description = "The project the work belongs to"
  default     = "basetier"
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

variable subscription_role_arn {
  type        = string
  description = "The ARN of an IAM role that grants CW logs permissions to deliver log events to the destination"
}

variable firehose_destination_arn {
  type        = string
  description = "The ARN of the destination to deliver matching log events to."
}

variable project_version {
  type        = string
  description = "The current version of the project "
}

variable bulkapi_storage_target_name {
  type        = string
  description = "CallMiner Bulk API storage target name that maps to the holding zone export destination"
}

variable bulkapi_holding_bucket_name {
  type        = string
  description = "S3 bucket used as CallMiner Bulk API export destination"
}

variable bulkapi_holding_prefix {
  type        = string
  description = "S3 prefix used as CallMiner Bulk API export destination"
}
