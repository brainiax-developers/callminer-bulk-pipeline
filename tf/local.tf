locals {
  python_file_loc = "${path.root}/../src"
  zipped_file_loc = path.root

  bulkapi_auth_secret_name = var.environment != "prod" ? "${var.environment}-hubs-basetier-land-ds-ingestion-callminer-bulkapi-creds-nonprod-only" : "${var.environment}-hubs-basetier-land-ds-ingestion-callminer-bulkapi-creds"
  bulkapi_job_name         = trimspace(var.bulk_job_name) != "" ? var.bulk_job_name : "${var.environment}-callminer-bulkapi-export-job"

  scheduler_role_name = "${var.environment}-hubs-data-bulkapi-scheduler-iamrole-callminer"

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

  tags = merge(
    {
      created_by  = var.created_by
      service     = "callminer-bulkapi-scheduler"
      environment = var.environment
    },
    var.extra_tags
  )
}
