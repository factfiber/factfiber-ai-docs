variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "factfiber"
}

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "s3_bucket_id" {
  description = "ID of the S3 bucket serving as origin"
  type        = string
}

variable "s3_bucket_regional_domain_name" {
  description = "Regional domain name of the S3 bucket"
  type        = string
}

variable "logs_bucket_domain_name" {
  description = "Domain name of the S3 bucket for logs"
  type        = string
}

variable "domain_aliases" {
  description = "List of custom domain aliases for CloudFront"
  type        = list(string)
  default     = []
}

variable "acm_certificate_arn" {
  description = "ARN of ACM certificate for custom domain (must be in us-east-1)"
  type        = string
  default     = ""
}

variable "lambda_edge_enabled" {
  description = "Whether to enable Lambda@Edge authentication"
  type        = bool
  default     = true
}

variable "lambda_edge_arn" {
  description = "ARN of Lambda@Edge function for viewer request"
  type        = string
  default     = ""
}

variable "alarm_sns_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarms"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
