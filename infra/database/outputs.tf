output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "rds_port" {
  value = aws_db_instance.main.port
}

output "rds_instance_id" {
  value = aws_db_instance.main.id
}

output "redis_endpoint" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "redis_cluster_id" {
  value = aws_elasticache_replication_group.main.id
}

output "db_password_secret_arn" {
  value = aws_secretsmanager_secret.db_password.arn
}

output "db_password" {
  value     = random_password.db_password.result
  sensitive = true
}
