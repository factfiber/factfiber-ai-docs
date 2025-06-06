variable "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  type        = string
}

variable "cloudfront_hosted_zone_id" {
  description = "CloudFront distribution hosted zone ID"
  type        = string
}

variable "cross_account_role_arn" {
  description = "ARN of the cross-account role to assume for Route53 access"
  type        = string
}

variable "external_id" {
  description = "External ID for cross-account role assumption"
  type        = string
  default     = "factfiber-docs-route53-access"
}

variable "create_www_redirect" {
  description = "Create www subdomain redirect"
  type        = bool
  default     = false
}
