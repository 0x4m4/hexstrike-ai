terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ECS Cluster
resource "aws_ecs_cluster" "osint" {
  name = "osint-framework-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECR Repository
resource "aws_ecr_repository" "osint" {
  name = "osint-framework"
}

# ECS Task Definition
resource "aws_ecs_task_definition" "osint" {
  family                   = "osint-framework"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([{
    name      = "osint-framework"
    image     = "${aws_ecr_repository.osint.repository_url}:latest"
    essential = true
    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
      protocol      = "tcp"
    }]
    environment = [
      { name = "DATABASE_URL", value = var.database_url },
      { name = "API_HOST", value = "0.0.0.0" },
      { name = "API_PORT", value = "8000" }
    ]
  }])
}

# ECS Service
resource "aws_ecs_service" "osint" {
  name            = "osint-framework"
  cluster         = aws_ecs_cluster.osint.id
  task_definition = aws_ecs_task_definition.osint.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.osint.id]
  }
}

# ALB
resource "aws_lb" "osint" {
  name               = "osint-framework-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.osint_lb.id]
  subnets            = var.subnet_ids
}

resource "aws_lb_target_group" "osint" {
  name     = "osint-framework-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = var.vpc_id
}

resource "aws_lb_listener" "osint" {
  load_balancer_arn = aws_lb.osint.arn
  port             = "80"
  protocol         = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.osint.arn
  }
}

# Security Groups
resource "aws_security_group" "osint" {
  name        = "osint-framework-sg"
  vpc_id      = var.vpc_id
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    security_groups = [aws_security_group.osint_lb.id]
  }
}

resource "aws_security_group" "osint_lb" {
  name        = "osint-framework-lb-sg"
  vpc_id      = var.vpc_id
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# IAM Roles
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecs-task-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}