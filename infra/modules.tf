# Module wiring — connects all submodules

module "networking" {
  source      = "./networking"
  project_name = var.project_name
  vpc_cidr    = var.vpc_cidr
  environment = var.environment
}

module "database" {
  source = "./database"

  project_name             = var.project_name
  environment              = var.environment
  db_username              = var.db_username
  db_name                  = var.db_name
  private_subnet_ids       = module.networking.private_subnet_ids
  rds_security_group_id    = module.networking.rds_security_group_id
  redis_security_group_id  = module.networking.redis_security_group_id
}

module "secrets" {
  source       = "./secrets"
  project_name = var.project_name
  environment  = var.environment
}

module "compute" {
  source = "./compute"

  project_name            = var.project_name
  environment             = var.environment
  aws_region              = var.aws_region
  vpc_id                  = module.networking.vpc_id
  public_subnet_ids       = module.networking.public_subnet_ids
  alb_security_group_id   = module.networking.alb_security_group_id
  ecs_security_group_id   = module.networking.ecs_security_group_id
  db_url_secret_arn       = aws_secretsmanager_secret.database_url.arn

  depends_on = [module.database, module.secrets]
}

module "monitoring" {
  source = "./monitoring"

  project_name         = var.project_name
  environment          = var.environment
  aws_region           = var.aws_region
  alert_email          = var.alert_email
  ecs_cluster_name     = module.compute.ecs_cluster_name
  alb_arn_suffix       = module.compute.alb_arn_suffix
  target_group_arn_suffix = module.compute.target_group_arn_suffix
  rds_instance_id      = module.database.rds_instance_id
  redis_cluster_id     = module.database.redis_cluster_id
}
