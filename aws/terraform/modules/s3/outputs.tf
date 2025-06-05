output "docs_bucket_id" {
  description = "The ID of the documentation S3 bucket"
  value       = aws_s3_bucket.docs.id
}

output "docs_bucket_arn" {
  description = "The ARN of the documentation S3 bucket"
  value       = aws_s3_bucket.docs.arn
}

output "docs_bucket_regional_domain_name" {
  description = "The regional domain name of the documentation S3 bucket"
  value       = aws_s3_bucket.docs.bucket_regional_domain_name
}

output "logs_bucket_id" {
  description = "The ID of the logs S3 bucket"
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_domain_name" {
  description = "The domain name of the logs S3 bucket"
  value       = aws_s3_bucket.logs.bucket_domain_name
}
