# Development environment for FactFiber documentation

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration for state storage
  backend "s3" {
    profile = "fc-aws-infra"
    bucket  = "ff-crypto-tf-state"
    # repo/component/stage
    key            = "factfiber.ai/factfiber-ai-docs/dev"
    dynamodb_table = "ff-crypto-tf-state-lock"
    region  = "us-east-1"
    encrypt = true
  }
}

# Configure AWS provider
provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = local.common_tags
  }
}

# AWS provider for us-east-1 (required for Lambda@Edge and ACM)
provider "aws" {
  alias   = "us_east_1"
  region  = "us-east-1"
  profile = var.aws_profile

  default_tags {
    tags = local.common_tags
  }
}

locals {
  environment = "dev"

  common_tags = {
    Project     = "factfiber-docs"
    Environment = local.environment
    ManagedBy   = "terraform"
    Owner       = "platform-team"
  }
}

# S3 buckets for documentation hosting
module "s3" {
  source = "../../modules/s3"

  environment                 = local.environment
  cloudfront_distribution_arn = module.cloudfront.distribution_arn
  tags                       = local.common_tags
}

# Lambda@Edge for authentication
module "lambda_edge" {
  source = "../../modules/lambda-edge"

  providers = {
    aws.us_east_1 = aws.us_east_1
  }

  environment          = local.environment
  lambda_source_file   = "${path.root}/../../../lambda/auth/index.js"
  github_client_id     = var.github_client_id
  github_client_secret = var.github_client_secret
  github_org          = var.github_org
  allowed_teams       = var.allowed_teams
  alarm_sns_topic_arn = aws_sns_topic.alerts.arn
  tags                = local.common_tags
}

# CloudFront distribution
module "cloudfront" {
  source = "../../modules/cloudfront"

  environment                    = local.environment
  s3_bucket_id                  = module.s3.docs_bucket_id
  s3_bucket_regional_domain_name = module.s3.docs_bucket_regional_domain_name
  logs_bucket_domain_name        = module.s3.logs_bucket_domain_name
  domain_aliases                 = var.domain_aliases
  acm_certificate_arn           = var.acm_certificate_arn
  lambda_edge_enabled           = true
  lambda_edge_arn               = module.lambda_edge.lambda_arn
  alarm_sns_topic_arn           = aws_sns_topic.alerts.arn
  tags                          = local.common_tags
}

# SNS topic for alerts
resource "aws_sns_topic" "alerts" {
  name         = "factfiber-docs-${local.environment}-alerts"
  display_name = "FactFiber Docs ${local.environment} Alerts"

  tags = local.common_tags
}

# SNS topic subscription
resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# IAM role for GitHub Actions deployment
module "github_actions_role" {
  source = "../../modules/iam"

  environment                = local.environment
  github_org                = var.github_org
  github_repo               = var.github_repo
  s3_bucket_arn             = module.s3.docs_bucket_arn
  cloudfront_distribution_id = module.cloudfront.distribution_id
  tags                      = local.common_tags
}

# Outputs for GitHub Actions
output "s3_bucket_name" {
  description = "Name of the S3 bucket for documentation"
  value       = module.s3.docs_bucket_id
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = module.cloudfront.distribution_id
}

output "cloudfront_domain_name" {
  description = "Domain name of the CloudFront distribution"
  value       = module.cloudfront.distribution_domain_name
}

output "github_actions_role_arn" {
  description = "ARN of the IAM role for GitHub Actions"
  value       = module.github_actions_role.role_arn
}
