# CloudFront module for FactFiber documentation CDN

# Origin Access Control for S3
resource "aws_cloudfront_origin_access_control" "docs" {
  name                              = "${var.project_name}-${var.environment}-oac"
  description                       = "OAC for ${var.project_name} documentation"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront distribution
resource "aws_cloudfront_distribution" "docs" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100" # US, Canada, Europe

  origin {
    domain_name              = var.s3_bucket_regional_domain_name
    origin_id                = "S3-${var.s3_bucket_id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.docs.id
  }

  # Default cache behavior
  default_cache_behavior {
    target_origin_id       = "S3-${var.s3_bucket_id}"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {
      query_string = false
      headers      = ["Origin", "Access-Control-Request-Headers", "Access-Control-Request-Method"]

      cookies {
        forward = "none"
      }
    }

    # Lambda@Edge association for authentication
    dynamic "lambda_function_association" {
      for_each = var.lambda_edge_enabled ? [1] : []
      content {
        event_type   = "viewer-request"
        lambda_arn   = var.lambda_edge_arn
        include_body = false
      }
    }

    min_ttl     = 0
    default_ttl = 86400    # 24 hours
    max_ttl     = 31536000 # 1 year
  }

  # Custom error pages
  custom_error_response {
    error_code            = 403
    response_code         = 403
    response_page_path    = "/error/403.html"
    error_caching_min_ttl = 300
  }

  custom_error_response {
    error_code            = 404
    response_code         = 404
    response_page_path    = "/error/404.html"
    error_caching_min_ttl = 300
  }

  # Geo restrictions - US primary with EU
  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["US", "CA", "GB", "DE", "FR", "NL", "CH", "IE", "ES", "IT"]
    }
  }

  # SSL certificate
  viewer_certificate {
    cloudfront_default_certificate = var.acm_certificate_arn == "" ? true : false
    acm_certificate_arn            = var.acm_certificate_arn != "" ? var.acm_certificate_arn : null
    ssl_support_method             = var.acm_certificate_arn != "" ? "sni-only" : null
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  # Logging configuration
  logging_config {
    bucket          = var.logs_bucket_domain_name
    prefix          = "cloudfront/"
    include_cookies = false
  }

  # Custom domain aliases
  aliases = var.domain_aliases

  # Tags
  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-cdn"
    Environment = var.environment
  })

  # Wait for OAC to be ready
  depends_on = [aws_cloudfront_origin_access_control.docs]
}

# CloudWatch alarms for monitoring
resource "aws_cloudwatch_metric_alarm" "origin_4xx_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-cf-4xx-errors"
  alarm_description   = "CloudFront 4xx error rate too high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4xxErrorRate"
  namespace           = "AWS/CloudFront"
  period              = "300"
  statistic           = "Average"
  threshold           = "5"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DistributionId = aws_cloudfront_distribution.docs.id
  }

  alarm_actions = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "origin_5xx_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-cf-5xx-errors"
  alarm_description   = "CloudFront 5xx error rate too high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "5xxErrorRate"
  namespace           = "AWS/CloudFront"
  period              = "300"
  statistic           = "Average"
  threshold           = "1"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DistributionId = aws_cloudfront_distribution.docs.id
  }

  alarm_actions = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  tags = var.tags
}
