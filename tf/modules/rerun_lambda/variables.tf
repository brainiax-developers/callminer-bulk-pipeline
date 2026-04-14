variable environment {
  type        = string
  description = "The environment being deployed to"
}

variable filename {
  type        = string
  description = "Code source"
}

variable event_rule_arn {
  type        = string
  description = "ARN of the AWS State Machine Event Rule"
}

variable file_loc {
  type        = string
  description = "Source location of the python script"
}

variable zipped_file_loc {
  type        = string
  description = "Output location of the zipped python script"
}

variable rerun_role_arn {
  type        = string
  description = "ARN of the AWS IAM Role used by the rerun lambda"
}

variable aws_account_id {
  type        = string
  description = "The AWS account ID for the account being deployed to"
}

variable alert_sns_arn {
  type        = string
  description = "SNS Topic ARN to notify when rerun is skipped due to missing threshold"
}