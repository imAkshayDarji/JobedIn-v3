variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Environment name (production, staging)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "jobedin-v3"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "jobedin"
}

variable "db_name" {
  description = "RDS database name"
  type        = string
  default     = "jobedin"
}

variable "alert_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
}
