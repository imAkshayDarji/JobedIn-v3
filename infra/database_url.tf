# Computed DATABASE_URL secret (built from RDS outputs)
resource "aws_secretsmanager_secret" "database_url" {
  name                    = "${var.project_name}/database/url"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql+asyncpg://${var.db_username}:${urlencode(module.database.db_password)}@${module.database.rds_endpoint}:5432/${var.db_name}"
}
