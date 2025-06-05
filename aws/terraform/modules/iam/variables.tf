variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "factfiber"
}

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "github_org" {
  description = "GitHub organization name"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket to grant access to"
  type        = string
}

variable "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution for invalidation"
  type        = string
}

variable "create_oidc_provider" {
  description = "Whether to create the GitHub OIDC provider"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
