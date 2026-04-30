
locals {
  aws_account_id           = data.aws_caller_identity.here.account_id
  bulkapi_auth_secret_name = "${var.environment}/callminer/api-credentials"
  bulkapi_job_name         = "${var.environment}-callminer-bulkapi-export-job"


  bulkapi_storage_target_name = "${var.environment}CallminerHoldingZone"
  bulkapi_holding_bucket_name = "${var.environment}-lakehouse-holding-zone"
  bulkapi_holding_prefix = "callminer/export/"

  bulkapi_export_job_schedule = "0 0 * ? * *"
  scheduler_reconcile_schedule = "rate(1 day)"

  bulkapi_notification_method = var.bulkapi_notification_method
  bulkapi_notification_email_recipients = [
    for recipient in var.bulkapi_notification_email_recipients : trimspace(recipient)
    if trimspace(recipient) != ""
  ]
  bulkapi_notification_webhook_id = trimspace(var.bulkapi_notification_webhook_id) != "" ? trimspace(
    var.bulkapi_notification_webhook_id
  ) : null

  bulkapi_job_template_json = jsonencode({
    Duration = {
      SearchMode = "NewAndUpdated"    #Allowed options: [ClientCaptureDate, CreateDate, Updated, NewAndUpdated]
      LastNDays  = null               #Set number of days worth of data from Callminer job start time
      LastNHours = 1                  #Set number of hours worth of data from Callminer job start time
      TimeFrame  = null               #Allowed options: [Yesterday, LastWeek, ThisMonth, LastMonth, Custom]
      StartDate  = null
      EndDate    = null
    }
    DataTypes          = ["Contacts", "Categories", "Category_Components", "Scores", "Score_Indicators"]
    NotificationMethod = local.bulkapi_notification_method
    EmailRecipients    = local.bulkapi_notification_method == "Email" ? local.bulkapi_notification_email_recipients : null
    WebhookId          = local.bulkapi_notification_method == "Webhook" ? local.bulkapi_notification_webhook_id : null
    StorageTargetName  = local.bulkapi_storage_target_name
    Schedule           = local.bulkapi_export_job_schedule
  })
}

check "bulkapi_notification_configuration" {
  assert {
    condition = (
      local.bulkapi_notification_method == "Email" ? (
        length(local.bulkapi_notification_email_recipients) > 0 &&
        local.bulkapi_notification_webhook_id == null &&
        alltrue([
          for recipient in local.bulkapi_notification_email_recipients :
          can(regex("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$", recipient))
        ])
      ) : local.bulkapi_notification_method == "Webhook" ? (
        local.bulkapi_notification_webhook_id != null &&
        length(local.bulkapi_notification_email_recipients) == 0
      ) : false
    )
    error_message = "Invalid notification configuration: use exactly one path - Email with at least one valid recipient and no webhook id, or Webhook with webhook id and no email recipients."
  }
}
