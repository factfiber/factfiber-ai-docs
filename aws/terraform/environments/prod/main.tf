# Production environment for FactFiber documentation

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
    profile        = "factfiber-docs-deploy"
    bucket         = "ff-crypto-tf-state"
    # repo/component/stage
    key            = "factfiber.ai/factfiber-ai-docs/prod"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "ff-crypto-tf-state-lock"
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
  environment = "prod"

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

# Data sources for SSM parameters
data "aws_ssm_parameter" "github_client_id" {
  name = "/factfiber/docs/github-client-id"
}

data "aws_ssm_parameter" "github_client_secret" {
  name            = "/factfiber/docs/github-client-secret"
  with_decryption = true
}

data "aws_ssm_parameter" "jwt_secret" {
  name            = "/factfiber/docs/jwt-secret"
  with_decryption = true
}

# SSM parameter for GitHub private repository token
resource "aws_ssm_parameter" "github_private_repo_token" {
  name        = "/factfiber/docs/github-private-repo-token"
  description = "GitHub PAT for accessing private dependencies in CI/CD"
  type        = "SecureString"
  value       = "placeholder-set-manually"  # To be updated manually after creation

  lifecycle {
    ignore_changes = [value]  # Don't overwrite the manually set value
  }

  tags = merge(local.common_tags, {
    Name = "GitHub Private Repo Token"
    Note = "Update value manually with GitHub PAT that has 'repo' scope"
  })
}

# Lambda@Edge for authentication
module "lambda_edge" {
  source = "../../modules/lambda-edge"

  providers = {
    aws.us_east_1 = aws.us_east_1
  }

  environment          = local.environment
  lambda_source_file   = "${path.root}/../../../lambda/auth/index.js"
  github_client_id     = data.aws_ssm_parameter.github_client_id.value
  github_client_secret = data.aws_ssm_parameter.github_client_secret.value
  github_org          = var.github_org
  allowed_teams       = var.allowed_teams
  public_paths        = []  # Require authentication for all paths
  jwt_secret          = data.aws_ssm_parameter.jwt_secret.value
  cookie_domain       = var.cookie_domain
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
  domain_aliases                 = ["docs.factfiber.ai"]
  acm_certificate_arn           = aws_acm_certificate.docs.arn
  lambda_edge_enabled           = true
  lambda_edge_arn               = module.lambda_edge.lambda_arn
  alarm_sns_topic_arn           = aws_sns_topic.alerts.arn
  tags                          = local.common_tags
}

# ACM Certificate for HTTPS (must be in us-east-1 for CloudFront)
resource "aws_acm_certificate" "docs" {
  provider                  = aws.us_east_1
  domain_name               = "docs.factfiber.ai"
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "docs.factfiber.ai"
  })
}

# Route53 DNS configuration (cross-account)
# Temporarily commented out due to permission issues - will handle manually
# module "route53" {
#   source = "../../modules/route53"
#
#   cloudfront_domain_name    = module.cloudfront.distribution_domain_name
#   cloudfront_hosted_zone_id = module.cloudfront.distribution_hosted_zone_id
#   cross_account_role_arn    = var.route53_cross_account_role_arn
#   external_id               = var.route53_external_id
#   create_www_redirect       = false
#
#   # ACM certificate validation
#   acm_certificate_arn               = aws_acm_certificate.docs.arn
#   acm_certificate_domain_validation = aws_acm_certificate.docs.domain_validation_options
#
#   tags = local.common_tags
# }

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

output "docs_custom_domain" {
  description = "Custom domain for documentation"
  value       = "https://docs.factfiber.ai"
}
