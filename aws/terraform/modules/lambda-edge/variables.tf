variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "factfiber"
}

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "lambda_source_file" {
  description = "Path to Lambda function source file"
  type        = string
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
}

variable "allowed_teams" {
  description = "List of GitHub teams allowed to access documentation"
  type        = list(string)
  default     = ["platform-team", "docs-team", "admin-team"]
}

variable "public_paths" {
  description = "List of paths that don't require authentication"
  type        = list(string)
  default     = ["/", "/index.html", "/error/*", "/favicon.ico"]
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 7
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
