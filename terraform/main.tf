terraform {
  required_version = ">= 1.6"

  backend "s3" {
    bucket  = "nsw-property-terraform-state"
    key     = "terraform.tfstate"
    region  = "ap-southeast-2"
    encrypt = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = "ap-southeast-2"
}
