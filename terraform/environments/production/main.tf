# Zappix Demo Production Environment
# Deploys frontend to S3/CloudFront and backend to ECS

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment to use S3 backend for state
  # backend "s3" {
  #   bucket         = "zappix-terraform-state"
  #   key            = "zappix-demo2/production/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "zappix-demo2"
      Environment = "production"
      ManagedBy   = "terraform"
    }
  }
}

# Provider for ACM certificates (must be us-east-1 for CloudFront)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "frontend_domain" {
  description = "Domain for the frontend"
  type        = string
  default     = "zappix2.aldea.ai"
}

variable "backend_domain" {
  description = "Domain for the backend"
  type        = string
  default     = "zappix2-backend.aldea.ai"
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID for aldea.ai"
  type        = string
}

variable "certificate_arn" {
  description = "ACM certificate ARN for *.aldea.ai (must be in us-east-1 for CloudFront)"
  type        = string
}

variable "backend_certificate_arn" {
  description = "ACM certificate ARN for backend (can be regional)"
  type        = string
}

# Local variables
locals {
  project_name = "zappix-demo2"
  environment  = "production"
}

# VPC Module
module "vpc" {
  source = "../../modules/vpc"

  project_name = local.project_name
  environment  = local.environment
  aws_region   = var.aws_region
}

# ECR Repository
module "ecr" {
  source = "../../modules/ecr"

  project_name = local.project_name
  environment  = local.environment
}

# S3 + CloudFront for Frontend
module "frontend" {
  source = "../../modules/cloudfront"

  project_name    = local.project_name
  environment     = local.environment
  domain_name     = var.frontend_domain
  hosted_zone_id  = var.hosted_zone_id
  certificate_arn = var.certificate_arn
}

# ALB for Backend
module "alb" {
  source = "../../modules/alb"

  project_name    = local.project_name
  environment     = local.environment
  vpc_id          = module.vpc.vpc_id
  public_subnets  = module.vpc.public_subnet_ids
  domain_name     = var.backend_domain
  hosted_zone_id  = var.hosted_zone_id
  certificate_arn = var.backend_certificate_arn
}

# ECS for Backend
module "ecs" {
  source = "../../modules/ecs"

  project_name        = local.project_name
  environment         = local.environment
  aws_region          = var.aws_region
  vpc_id              = module.vpc.vpc_id
  private_subnets     = module.vpc.private_subnet_ids
  alb_target_group_arn = module.alb.target_group_arn
  alb_security_group_id = module.alb.security_group_id
  ecr_repository_url  = module.ecr.repository_url
}

# Outputs
output "frontend_url" {
  description = "Frontend URL"
  value       = "https://${var.frontend_domain}"
}

output "backend_url" {
  description = "Backend URL"
  value       = "https://${var.backend_domain}"
}

output "frontend_bucket_name" {
  description = "S3 bucket name for frontend"
  value       = module.frontend.bucket_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = module.frontend.distribution_id
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = module.ecr.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = module.ecs.service_name
}

