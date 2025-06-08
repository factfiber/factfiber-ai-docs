# Outputs for Lambda@Edge configuration module

output "lambda_package_path" {
  description = "Path to the packaged Lambda function with embedded configuration"
  value       = data.archive_file.lambda_with_config.output_path
}

output "lambda_package_hash" {
  description = "Base64 SHA256 hash of the Lambda package"
  value       = data.archive_file.lambda_with_config.output_base64sha256
}

output "config_file_path" {
  description = "Path to the generated configuration file"
  value       = local_file.lambda_config.filename
}
