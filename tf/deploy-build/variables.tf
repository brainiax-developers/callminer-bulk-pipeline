variable "environment" {
  type        = string
  description = "The environment being deployed to"
}

variable "project" {
  type        = string
  default     = "lakehouse"
  description = "The project the work belongs to"
}

variable "category" {
  type        = string
  default     = "event-bus-table-ddl-lambda"
  description = "The category of the work"
}

# tflint-ignore: terraform_unused_declarations
variable "image_version" {
  type        = string
  description = "The version number of the ECR image for the Lambda"
}

variable "component" {
  type        = string
  default     = "lambda"
  description = "The component of the work"
}

variable "created_by" {
  type        = string
  default     = "event-bus-table-ddl-lambda"
  description = "The project (repo) the work was created in"
}

variable "service_owner" {
  type        = string
  description = "The Service Owner"
}

variable "service" {
  type        = string
  description = "The Service Name"
}

variable "business_capability_l0" {
  type        = string
  description = "The Business Capability Level 0"
}

variable "business_capability_l1" {
  type        = string
  description = "The Business Capability Level 1"
}

variable "service_tier" {
  type        = string
  description = "The Service Tier"
}

variable "data_classification" {
  type        = string
  description = "The Data Classification"
}
