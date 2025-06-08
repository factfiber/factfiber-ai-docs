# Variables for Lambda@Edge configuration module

variable "github_client_id" {
  description = "GitHub OAuth App Client ID"
  type        = string
  sensitive   = true
}

variable "github_client_secret" {
  description = "GitHub OAuth App Client Secret"
  type        = string
  sensitive   = true
}

variable "github_org" {
  description = "GitHub organization name"
  type        = string
}

variable "allowed_teams" {
  description = "List of allowed GitHub teams"
  type        = list(string)
  default     = ["platform-team", "docs-team", "admin-team"]
}

variable "public_paths" {
  description = "List of public paths that don't require authentication"
  type        = list(string)
  default     = ["/", "/index.html", "/error/*", "/favicon.ico"]
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

variable "environment" {
  description = "Environment name (prod, staging, dev)"
  type        = string
}

variable "lambda_source_file" {
  description = "Path to the Lambda function source file"
  type        = string
}
