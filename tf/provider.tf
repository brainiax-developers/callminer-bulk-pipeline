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

data "aws_ssm_parameter" "external_id" {
  provider = aws.build
  name     = "/build/terraform/crossaccount/data/${var.environment}/externalid"
}

data "aws_ssm_parameter" "cross_account_role" {
  provider = aws.build
  name     = "/build/terraform/crossaccount/data/${var.environment}/rolearn"
}

provider "aws" {
  alias  = "build"
  region = var.region
}

provider "aws" {
  region = var.region
  assume_role {
    role_arn    = data.aws_ssm_parameter.cross_account_role.value
    external_id = data.aws_ssm_parameter.external_id.value
  }
  default_tags {
    tags = {
      "created-by" = var.created_by
    }
  }
}

