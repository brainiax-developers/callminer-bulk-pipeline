output "bulkapi_scheduler_lambda_function_name" {
  description = "Deployed scheduler Lambda function name."
  value       = module.bulkapi_scheduler_lambda.bulkapi_scheduler_function_name
}

output "bulkapi_storage_target_name" {
  description = "CallMiner BulkAPI storage target name used in the export job payload."
  value       = local.bulkapi_storage_target_name
}

output "bulkapi_expected_holding_destination_bucket" {
  description = "Expected CallMiner holding bucket backing the storage target."
  value       = local.bulkapi_holding_bucket_name
}

output "bulkapi_expected_holding_destination_prefix" {
  description = "Expected CallMiner holding prefix backing the storage target."
  value       = local.bulkapi_holding_prefix
}

output "bulkapi_export_job_schedule" {
  description = "Quartz cron expression configured for the CallMiner export job."
  value       = local.bulkapi_export_job_schedule
}

output "bulkapi_scheduler_reconcile_schedule_expression" {
  description = "EventBridge expression for the scheduler Lambda reconciliation cadence."
  value       = local.scheduler_reconcile_schedule
}
