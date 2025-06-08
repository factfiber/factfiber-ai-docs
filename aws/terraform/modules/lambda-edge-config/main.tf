# Lambda@Edge Configuration Module
# This module generates configuration for Lambda@Edge functions
# Since Lambda@Edge cannot use environment variables, configuration is embedded in the code

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Generate configuration JavaScript file
resource "local_file" "lambda_config" {
  filename = "${path.module}/generated/config.js"
  content = templatefile("${path.module}/templates/config.js.tpl", {
    github_client_id     = var.github_client_id
    github_client_secret = var.github_client_secret
    github_org          = var.github_org
    allowed_teams       = jsonencode(var.allowed_teams)
    public_paths        = jsonencode(var.public_paths)
    jwt_secret          = var.jwt_secret
    cookie_domain       = var.cookie_domain
    environment         = var.environment
  })

  # Ensure directory exists
  depends_on = [null_resource.create_generated_dir]
}

# Create generated directory
resource "null_resource" "create_generated_dir" {
  provisioner "local-exec" {
    command = "mkdir -p ${path.module}/generated"
  }
}

# Package the Lambda function with embedded configuration
data "archive_file" "lambda_with_config" {
  type        = "zip"
  output_path = "${path.module}/lambda-auth-configured.zip"

  source {
    content  = file(var.lambda_source_file)
    filename = "index.js"
  }

  source {
    content  = local_file.lambda_config.content
    filename = "config.js"
  }

  depends_on = [local_file.lambda_config]
}
