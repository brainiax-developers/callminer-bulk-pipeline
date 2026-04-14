terraform {
  backend "s3" {}
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">=5.22.0"
    }
  }
  required_version = ">=1.6.2"
}

provider "aws" {
  region = "eu-west-1"
  default_tags {
    tags = {
      "created-by" = var.created_by
    }
  }
}

module "ecr" {
  source      = "git@git.tech.theverygroup.com:data/pipelines/modules/terraform/ecr.git?ref=v1.1.1"
  environment = var.environment
  project     = var.project
  category    = var.category
  component   = var.component
  tags        = module.label.tags
}

module "ssm_param_ecr_repo_url" {
  source                = "git@git.tech.theverygroup.com:data/platform/modules/terraform/parameter-store.git//modules/ssm_parameter_put?ref=v1.2"
  environment           = var.environment
  project               = var.project
  parameter_name        = "callminer_bulk_pipeline_ecr_repo_url"
  parameter_value       = module.ecr.ecr_repository_url
  parameter_description = "The ECR repository URL for the callminer-bulk-pipeline in the ${var.environment} environment."
}

module "label" {
  source                 = "git@git.tech.theverygroup.com:pe/public/tf-modules/pe-tf-module-tag.git?ref=v1.6.0"
  environment            = var.environment
  project                = var.project
  category               = var.category
  service_owner          = var.service_owner
  service                = var.service
  business_capability_l0 = var.business_capability_l0
  business_capability_l1 = var.business_capability_l1
  service_tier           = var.service_tier
  data_classification    = var.data_classification
  created_by             = var.created_by
}
