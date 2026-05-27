provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "jobedin-v3"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
