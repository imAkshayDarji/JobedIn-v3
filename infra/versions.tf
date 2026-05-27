terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "jobedin-v3-terraform-state-357542025442"
    key            = "infra/terraform.tfstate"
    region         = "eu-west-2"
    use_lockfile = true
    encrypt      = true
  }
}
