data "archive_file" "callminer_bulkapi_scheduler" {
  type        = "zip"
  source_dir  = "${var.file_loc}/"
  output_path = "${var.zipped_file_loc}/callminer_bulkapi_scheduler.zip"
}
