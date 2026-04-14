
locals {
  payload_filename      = "../build/distributions/callminer-bulk-pipeline-${var.project_version}.zip"
  aws_account_id        = data.aws_caller_identity.here.account_id
  python_file_loc       = "../src/python"
  zipped_file_loc       = "../src/output"
  bulkapi_auth_secret_name =  "${var.environment}-callminer-bulkapi-creds"
  bulkapi_holding_bucket_name = var.bulkapi_holding_bucket_name
  bulkapi_holding_prefix = var.bulkapi_holding_prefix
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
    StorageTargetName  = var.bulkapi_storage_target_name
    Schedule           = "0 30 8 ? * *"
  })
}
