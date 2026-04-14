
locals {
  aws_account_id                   = data.aws_caller_identity.here.account_id
  bulkapi_auth_secret_name         = "${var.environment}-callminer-bulkapi-creds"
  bulkapi_job_name                 = "${var.environment}-callminer-bulkapi-export-job"
  bulkapi_storage_target_name      = trimspace(var.bulkapi_storage_target_name) != "" ? var.bulkapi_storage_target_name : "${var.environment}-callminer-bulkapi-holding-target"
  bulkapi_holding_bucket_name      = trimspace(var.bulkapi_holding_bucket_name) != "" ? var.bulkapi_holding_bucket_name : "${var.environment}-lakehouse-holding-zone"
  bulkapi_holding_prefix           = trimspace(var.bulkapi_holding_prefix) != "" ? var.bulkapi_holding_prefix : "callminer/export/"
  bulkapi_export_job_schedule      = trimspace(var.bulkapi_export_job_schedule) != "" ? var.bulkapi_export_job_schedule : "0 0/20 * ? * *"
  scheduler_reconcile_schedule     = trimspace(var.scheduler_reconcile_schedule_expression) != "" ? var.scheduler_reconcile_schedule_expression : "rate(1 day)"
  bulkapi_job_template_json = jsonencode({
    Duration = {
      SearchMode = "ClientCaptureDate"
      LastNDays  = 1
      LastNHours = null
      TimeFrame  = null
      StartDate  = null
      EndDate    = null
    }
    DataTypes          = ["Contacts", "Categories", "Category_Components", "Scores", "Score_Indicators"]
    NotificationMethod = "Email"
    EmailRecipients    = []
    WebhookId          = null
    StorageTargetName  = local.bulkapi_storage_target_name
    Schedule           = local.bulkapi_export_job_schedule
  })
}
