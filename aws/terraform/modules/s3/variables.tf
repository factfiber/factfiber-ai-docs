variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "factfiber"
}

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "version_retention_days" {
  description = "Number of days to retain old object versions"
  type        = number
  default     = 30
}

variable "log_retention_days" {
  description = "Number of days to retain CloudFront logs"
  type        = number
  default     = 7
}

variable "cloudfront_distribution_arn" {
  description = "ARN of the CloudFront distribution for bucket policy"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
