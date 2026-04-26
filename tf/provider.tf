provider "aws" {
  region = "eu-west-1"
}

terraform {
  backend "s3" {}
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.27.0"
    }
  }
  required_version = ">=1.3.7"
}
