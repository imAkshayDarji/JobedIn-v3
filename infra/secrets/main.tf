# Application secrets — stored in AWS Secrets Manager
# These are created with placeholder values. You fill in the actual values after initial deploy.

resource "aws_secretsmanager_secret" "app_secret_key" {
  name                    = "${var.project_name}/app/secret-key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "app_secret_key" {
  secret_id     = aws_secretsmanager_secret.app_secret_key.id
  secret_string = "CHANGE-ME-GENERATE-A-SECURE-KEY"
}

resource "aws_secretsmanager_secret" "app_encryption_key" {
  name                    = "${var.project_name}/app/encryption-key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "app_encryption_key" {
  secret_id     = aws_secretsmanager_secret.app_encryption_key.id
  secret_string = "CHANGE-ME-GENERATE-A-SECURE-KEY"
}

# Clerk secrets
resource "aws_secretsmanager_secret" "clerk_jwks_url" {
  name                    = "${var.project_name}/clerk/jwks-url"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "clerk_jwks_url" {
  secret_id     = aws_secretsmanager_secret.clerk_jwks_url.id
  secret_string = "CHANGE-ME-YOUR-CLERK-JWKS-URL"
}

resource "aws_secretsmanager_secret" "clerk_secret_key" {
  name                    = "${var.project_name}/clerk/secret-key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "clerk_secret_key" {
  secret_id     = aws_secretsmanager_secret.clerk_secret_key.id
  secret_string = "CHANGE-ME-YOUR-CLERK-SECRET-KEY"
}

# Sentry
resource "aws_secretsmanager_secret" "sentry_dsn_backend" {
  name                    = "${var.project_name}/sentry/dsn-backend"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "sentry_dsn_backend" {
  secret_id     = aws_secretsmanager_secret.sentry_dsn_backend.id
  secret_string = "CHANGE-ME-YOUR-SENTRY-DSN"
}

# AI API Keys
resource "aws_secretsmanager_secret" "glm_api_key" {
  name                    = "${var.project_name}/ai/glm-api-key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "glm_api_key" {
  secret_id     = aws_secretsmanager_secret.glm_api_key.id
  secret_string = "CHANGE-ME-YOUR-GLM-API-KEY"
}

resource "aws_secretsmanager_secret" "openai_api_key" {
  name                    = "${var.project_name}/ai/openai-api-key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "openai_api_key" {
  secret_id     = aws_secretsmanager_secret.openai_api_key.id
  secret_string = "CHANGE-ME-YOUR-OPENAI-API-KEY"
}

# Job API Keys
resource "aws_secretsmanager_secret" "jsearch_api_key" {
  name                    = "${var.project_name}/jobs/jsearch-api-key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "jsearch_api_key" {
  secret_id     = aws_secretsmanager_secret.jsearch_api_key.id
  secret_string = "CHANGE-ME-YOUR-JSEARCH-API-KEY"
}

resource "aws_secretsmanager_secret" "rapidapi_key" {
  name                    = "${var.project_name}/jobs/rapidapi-key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "rapidapi_key" {
  secret_id     = aws_secretsmanager_secret.rapidapi_key.id
  secret_string = "CHANGE-ME-YOUR-RAPIDAPI-KEY"
}

resource "aws_secretsmanager_secret" "adzuna_app_id" {
  name                    = "${var.project_name}/jobs/adzuna-app-id"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "adzuna_app_id" {
  secret_id     = aws_secretsmanager_secret.adzuna_app_id.id
  secret_string = "CHANGE-ME-YOUR-ADZUNA-APP-ID"
}

resource "aws_secretsmanager_secret" "adzuna_app_key" {
  name                    = "${var.project_name}/jobs/adzuna-app-key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "adzuna_app_key" {
  secret_id     = aws_secretsmanager_secret.adzuna_app_key.id
  secret_string = "CHANGE-ME-YOUR-ADZUNA-APP-KEY"
}

resource "aws_secretsmanager_secret" "reed_api_key" {
  name                    = "${var.project_name}/jobs/reed-api-key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "reed_api_key" {
  secret_id     = aws_secretsmanager_secret.reed_api_key.id
  secret_string = "CHANGE-ME-YOUR-REED-API-KEY"
}

# Non-sensitive config — stored in SSM Parameter Store
resource "aws_ssm_parameter" "redis_url" {
  name        = "/${var.project_name}/redis/url"
  description = "Redis connection URL"
  type        = "SecureString"
  value       = "redis://CHANGE-ME-REDIS-ENDPOINT:6379/0"
}

resource "aws_ssm_parameter" "cors_origins" {
  name        = "/${var.project_name}/app/cors-origins"
  description = "CORS allowed origins (comma-separated)"
  type        = "String"
  value       = "https://CHANGE-ME-AMPLIFY-URL.amplifyapp.com"
}
