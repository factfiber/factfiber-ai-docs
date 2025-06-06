variable "route53_aws_profile" {
  description = "AWS profile for the account containing Route53 (k8)"
  type        = string
  default     = "k8"
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID for factfiber.ai"
  type        = string
  default     = "Z04527812OYH5L6PJJUT7"
}

variable "external_id" {
  description = "External ID for cross-account role assumption"
  type        = string
  default     = "factfiber-docs-route53-access"
}
