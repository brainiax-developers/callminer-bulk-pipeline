data archive_file callminer_rerun {
  type          = "zip"
  source_dir    = "${var.file_loc}/"
  output_path   = "${var.zipped_file_loc}/callminer_rerun.zip"
}