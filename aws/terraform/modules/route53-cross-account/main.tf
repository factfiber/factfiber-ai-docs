# Cross-account Route53 configuration for docs.factfiber.ai
# This creates the necessary IAM role in the Route53 account to allow
# the infrastructure account to manage DNS records

# Provider for the Route53 account (k8 profile)
provider "aws" {
  alias   = "route53_account"
  profile = var.route53_aws_profile
  region  = "us-east-1"
}

# Data source to get the Route53 account ID
data "aws_caller_identity" "route53" {
  provider = aws.route53_account
}

# Data source to get the infrastructure account ID
data "aws_caller_identity" "infra" {}

# IAM role in Route53 account that trusts the infrastructure account
resource "aws_iam_role" "route53_cross_account" {
  provider = aws.route53_account
  name     = "FactFiberDocsRoute53CrossAccount"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.infra.account_id}:root"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.external_id
          }
        }
      }
    ]
  })

  tags = {
    Purpose   = "Cross-account Route53 access for FactFiber docs"
    ManagedBy = "terraform"
  }
}

# Policy to allow managing specific Route53 records
resource "aws_iam_role_policy" "route53_permissions" {
  provider = aws.route53_account
  name     = "Route53RecordManagement"
  role     = aws_iam_role.route53_cross_account.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "route53:GetHostedZone",
          "route53:ListResourceRecordSets",
          "route53:ChangeResourceRecordSets",
          "route53:GetChange"
        ]
        Resource = [
          "arn:aws:route53:::hostedzone/${var.hosted_zone_id}",
          "arn:aws:route53:::change/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "route53:ListHostedZones"
        ]
        Resource = "*"
      }
    ]
  })
}

output "cross_account_role_arn" {
  description = "ARN of the cross-account role to assume"
  value       = aws_iam_role.route53_cross_account.arn
}

output "external_id" {
  description = "External ID for assuming the role"
  value       = var.external_id
}
