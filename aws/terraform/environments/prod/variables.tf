variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
  default     = "fc-aws-infra"
}

variable "github_client_id" {
  description = "GitHub OAuth App client ID"
  type        = string
  sensitive   = true
}

variable "github_client_secret" {
  description = "GitHub OAuth App client secret"
  type        = string
  sensitive   = true
}

variable "github_org" {
  description = "GitHub organization name"
  type        = string
  default     = "factfiber"
}

variable "github_repo" {
  description = "GitHub repository name for Actions"
  type        = string
  default     = "factfiber-ai-docs"
}

variable "allowed_teams" {
  description = "List of GitHub teams allowed to access documentation"
  type        = list(string)
  default     = ["platform-team", "docs-team", "admin-team", "developers"]
}

variable "domain_aliases" {
  description = "Custom domain aliases for CloudFront distribution"
  type        = list(string)
  default     = ["docs.factfiber.ai"]
}

variable "acm_certificate_arn" {
  description = "ARN of ACM certificate for custom domain (must be in us-east-1)"
  type        = string
  default     = ""
}

variable "alert_email" {
  description = "Email address for CloudWatch alerts"
  type        = string
}

variable "route53_cross_account_role_arn" {
  description = "ARN of the cross-account role in the Route53 account"
  type        = string
}

variable "route53_external_id" {
  description = "External ID for Route53 cross-account access"
  type        = string
  default     = "factfiber-docs-route53-access"
}

variable "jwt_secret" {
  description = "Secret key for JWT token signing"
  type        = string
  sensitive   = true
  default     = ""
}

variable "cookie_domain" {
  description = "Domain for authentication cookies"
  type        = string
  default     = ".factfiber.ai"
}
