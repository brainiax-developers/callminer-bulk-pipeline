module "ecr" {
  source      = "git@git.tech.theverygroup.com:data/pipelines/modules/terraform/ecr.git?ref=v1.1.1"
  environment = var.environment
  project     = var.project
  category    = "callminer-bulk-pipeline"
  component   = "lambda"
  tags        = module.label.tags
}

module "ssm_param_ecr_repo_url" {
  source                = "git@git.tech.theverygroup.com:data/platform/modules/terraform/parameter-store.git//modules/ssm_parameter_put?ref=v1.2"
  environment           = var.environment
  project               = var.project
  parameter_name        = "callminer_bulk_pipeline_ecr_repo_url"
  parameter_value       = module.ecr.ecr_repository_url
  parameter_description = "The ECR repository URL for callminer-bulk-pipeline in the ${var.environment} environment."
}
