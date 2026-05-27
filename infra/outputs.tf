output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.compute.alb_dns_name
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.database.rds_endpoint
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.database.redis_endpoint
}

output "ecr_backend_repo_url" {
  description = "ECR repository URL for backend API"
  value       = module.compute.ecr_backend_repo_url
}

output "ecr_worker_repo_url" {
  description = "ECR repository URL for worker image"
  value       = module.compute.ecr_worker_repo_url
}

output "ecr_ai_worker_repo_url" {
  description = "ECR repository URL for AI worker image"
  value       = module.compute.ecr_ai_worker_repo_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.compute.ecs_cluster_name
}
