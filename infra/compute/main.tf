# ECR Repositories
resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}/backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-backend-ecr"
  }
}

resource "aws_ecr_repository" "ai_worker" {
  name                 = "${var.project_name}/ai-worker"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-ai-worker-ecr"
  }
}

resource "aws_ecr_repository" "worker" {
  name                 = "${var.project_name}/worker"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-worker-ecr"
  }
}

# ECR lifecycle policy — keep last 10 images, expire rest after 14 days
resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Expire untagged after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "ai_worker" {
  repository = aws_ecr_repository.ai_worker.name
  policy     = aws_ecr_lifecycle_policy.backend.policy
}

resource "aws_ecr_lifecycle_policy" "worker" {
  repository = aws_ecr_repository.worker.name
  policy     = aws_ecr_lifecycle_policy.backend.policy
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = var.project_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.project_name}/backend"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "ai_worker" {
  name              = "/ecs/${var.project_name}/ai-worker"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "job_worker" {
  name              = "/ecs/${var.project_name}/job-worker"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "apply_worker" {
  name              = "/ecs/${var.project_name}/apply-worker"
  retention_in_days = 7
}

# IAM Roles
data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Task execution role — used by ECS agent to pull images and read secrets
resource "aws_iam_role" "task_execution" {
  name               = "${var.project_name}-task-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy for reading secrets
resource "aws_iam_policy" "secrets_read" {
  name        = "${var.project_name}-secrets-read"
  description = "Allow ECS tasks to read secrets from Secrets Manager and SSM"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:${var.project_name}/*",
          "arn:aws:ssm:${var.aws_region}:*:parameter/${var.project_name}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "secrets_read" {
  role       = aws_iam_role.task_execution.name
  policy_arn = aws_iam_policy.secrets_read.arn
}

# Task role — used by the application code inside the container
resource "aws_iam_role" "task_role" {
  name               = "${var.project_name}-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

# ALB
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids

  tags = {
    Name = "${var.project_name}-alb"
  }
}

resource "aws_lb_target_group" "backend" {
  name        = "${var.project_name}-backend-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }

  tags = {
    Name = "${var.project_name}-backend-tg"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# Self-signed cert for HTTPS (use ACM or custom domain later)
resource "tls_private_key" "main" {
  algorithm = "RSA"
}

resource "tls_self_signed_cert" "main" {
  private_key_pem = tls_private_key.main.private_key_pem
  subject {
    common_name  = "${var.project_name}.internal"
    organization = var.project_name
  }
  validity_period_hours = 8760
  allowed_uses          = ["server_auth"]
}

resource "aws_iam_server_certificate" "main" {
  name             = "${var.project_name}-cert"
  certificate_body = tls_self_signed_cert.main.cert_pem
  private_key      = tls_private_key.main.private_key_pem

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_iam_server_certificate.main.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# Backend API Task Definition
resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project_name}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = "${aws_ecr_repository.backend.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "PORT", value = "8000" }
      ]

      secrets = [
        { name = "DATABASE_URL", valueFrom = "${var.db_url_secret_arn}" },
        { name = "REDIS_URL", valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/redis/url" },
        { name = "SECRET_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/app/secret-key" },
        { name = "ENCRYPTION_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/app/encryption-key" },
        { name = "CLERK_JWKS_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/clerk/jwks-url" },
        { name = "CLERK_SECRET_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/clerk/secret-key" },
        { name = "GLM_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/ai/glm-api-key" },
        { name = "OPENAI_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/ai/openai-api-key" },
        { name = "JSEARCH_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/jobs/jsearch-api-key" },
        { name = "RAPIDAPI_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/jobs/rapidapi-key" },
        { name = "ADZUNA_APP_ID", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/jobs/adzuna-app-id" },
        { name = "ADZUNA_APP_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/jobs/adzuna-app-key" },
        { name = "REED_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/jobs/reed-api-key" },
        { name = "CORS_ORIGINS", valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/app/cors-origins" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.backend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-backend-task"
  }
}

# Backend API ECS Service (always on, desired_count=1)
resource "aws_ecs_service" "backend" {
  name                               = "${var.project_name}-backend"
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.backend.arn
  desired_count                      = 1
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  tags = {
    Name = "${var.project_name}-backend-service"
  }
}

# AI Worker Task Definition
resource "aws_ecs_task_definition" "ai_worker" {
  family                   = "${var.project_name}-ai-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "ai-worker"
      image     = "${aws_ecr_repository.ai_worker.repository_url}:latest"
      essential = true

      command = ["arq", "app.workers.ai_worker.WorkerSettings"]

      environment = [
        { name = "ENVIRONMENT", value = var.environment }
      ]

      secrets = [
        { name = "DATABASE_URL", valueFrom = "${var.db_url_secret_arn}" },
        { name = "REDIS_URL", valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/redis/url" },
        { name = "SECRET_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/app/secret-key" },
        { name = "CLERK_JWKS_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/clerk/jwks-url" },
        { name = "GLM_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/ai/glm-api-key" },
        { name = "OPENAI_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/ai/openai-api-key" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ai_worker.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-ai-worker-task"
  }
}

# AI Worker Service (on-demand, starts at 0)
resource "aws_ecs_service" "ai_worker" {
  name                               = "${var.project_name}-ai-worker"
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.ai_worker.arn
  desired_count                      = 0
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = true
  }

  tags = {
    Name = "${var.project_name}-ai-worker-service"
  }
}

# Job Worker Task Definition (Playwright)
resource "aws_ecs_task_definition" "job_worker" {
  family                   = "${var.project_name}-job-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "job-worker"
      image     = "${aws_ecr_repository.worker.repository_url}:latest"
      essential = true

      command = ["arq", "app.workers.job_worker.JobWorkerSettings"]

      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "PLAYWRIGHT_CHROMIUM_LAUNCH_ARGS", value = "--disable-dev-shm-usage" }
      ]

      secrets = [
        { name = "DATABASE_URL", valueFrom = "${var.db_url_secret_arn}" },
        { name = "REDIS_URL", valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/redis/url" },
        { name = "SECRET_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/app/secret-key" },
        { name = "ENCRYPTION_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/app/encryption-key" },
        { name = "CLERK_JWKS_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/clerk/jwks-url" },
        { name = "JSEARCH_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/jobs/jsearch-api-key" },
        { name = "RAPIDAPI_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/jobs/rapidapi-key" },
        { name = "ADZUNA_APP_ID", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/jobs/adzuna-app-id" },
        { name = "ADZUNA_APP_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/jobs/adzuna-app-key" },
        { name = "REED_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/jobs/reed-api-key" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.job_worker.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-job-worker-task"
  }
}

resource "aws_ecs_service" "job_worker" {
  name                               = "${var.project_name}-job-worker"
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.job_worker.arn
  desired_count                      = 0
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = true
  }

  tags = {
    Name = "${var.project_name}-job-worker-service"
  }
}

# Apply Worker Task Definition (Playwright + heavier)
resource "aws_ecs_task_definition" "apply_worker" {
  family                   = "${var.project_name}-apply-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "apply-worker"
      image     = "${aws_ecr_repository.worker.repository_url}:latest"
      essential = true

      command = ["arq", "app.workers.apply_worker.ApplyWorkerSettings"]

      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "PLAYWRIGHT_CHROMIUM_LAUNCH_ARGS", value = "--disable-dev-shm-usage" }
      ]

      secrets = [
        { name = "DATABASE_URL", valueFrom = "${var.db_url_secret_arn}" },
        { name = "REDIS_URL", valueFrom = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/redis/url" },
        { name = "SECRET_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/app/secret-key" },
        { name = "ENCRYPTION_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/app/encryption-key" },
        { name = "CLERK_JWKS_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/clerk/jwks-url" },
        { name = "GLM_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/ai/glm-api-key" },
        { name = "OPENAI_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/ai/openai-api-key" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.apply_worker.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-apply-worker-task"
  }
}

resource "aws_ecs_service" "apply_worker" {
  name                               = "${var.project_name}-apply-worker"
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.apply_worker.arn
  desired_count                      = 0
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = true
  }

  tags = {
    Name = "${var.project_name}-apply-worker-service"
  }
}

# Frontend ECR Repository
resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project_name}/frontend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-frontend-ecr"
  }
}

resource "aws_ecr_lifecycle_policy" "frontend" {
  repository = aws_ecr_repository.frontend.name
  policy     = aws_ecr_lifecycle_policy.backend.policy
}

# Frontend CloudWatch Log Group
resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.project_name}/frontend"
  retention_in_days = 7
}

# Frontend ALB Target Group
resource "aws_lb_target_group" "frontend" {
  name        = "${var.project_name}-frontend-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }

  tags = {
    Name = "${var.project_name}-frontend-tg"
  }
}

# ALB Listener Rules — route API traffic to backend, everything else to frontend
resource "aws_lb_listener_rule" "backend_api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/health", "/docs", "/openapi.json", "/api/*"]
    }
  }
}

# Update HTTPS listener default to frontend
resource "aws_lb_listener_rule" "frontend_default" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  condition {
    path_pattern {
      values = ["/*"]
    }
  }
}

# Frontend Task Definition
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "frontend"
      image     = "${aws_ecr_repository.frontend.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "NODE_ENV", value = "production" },
        { name = "PORT", value = "3000" },
        { name = "NEXT_PUBLIC_API_URL", value = "https://${aws_lb.main.dns_name}" },
        { name = "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", value = "pk_test_bmVhdC1zYWlsZmlzaC04MC5jbGVyay5hY2NvdW50cy5kZXYk" },
        { name = "NEXT_PUBLIC_CLERK_SIGN_IN_URL", value = "/auth/login" },
        { name = "NEXT_PUBLIC_CLERK_SIGN_UP_URL", value = "/auth/register" },
        { name = "NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL", value = "/dashboard" },
        { name = "NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL", value = "/onboarding" },
        { name = "NEXT_PUBLIC_BYPASS_AUTH", value = "false" }
      ]

      secrets = [
        { name = "CLERK_SECRET_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/clerk/secret-key" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.frontend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-frontend-task"
  }
}

# Frontend ECS Service
resource "aws_ecs_service" "frontend" {
  name                               = "${var.project_name}-frontend"
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.frontend.arn
  desired_count                      = 1
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }

  tags = {
    Name = "${var.project_name}-frontend-service"
  }
}

data "aws_caller_identity" "current" {}
