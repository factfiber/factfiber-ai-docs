# Lambda@Edge module for GitHub OAuth authentication

# Note: Lambda@Edge functions must be deployed in us-east-1
terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 5.0"
      configuration_aliases = [aws.us_east_1]
    }
  }
}

# IAM role for Lambda@Edge execution
resource "aws_iam_role" "lambda_edge" {
  provider = aws.us_east_1
  name     = "${var.project_name}-${var.environment}-lambda-edge-auth"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = [
            "lambda.amazonaws.com",
            "edgelambda.amazonaws.com"
          ]
        }
      }
    ]
  })

  tags = var.tags
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  provider   = aws.us_east_1
  role       = aws_iam_role.lambda_edge.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for Lambda@Edge CloudWatch Logs
resource "aws_iam_role_policy" "lambda_edge_logs" {
  provider = aws.us_east_1
  name     = "${var.project_name}-${var.environment}-lambda-edge-logs"
  role     = aws_iam_role.lambda_edge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Package Lambda function code
data "archive_file" "lambda_auth" {
  type        = "zip"
  source_file = var.lambda_source_file
  output_path = "${path.module}/lambda-auth.zip"
}

# Lambda@Edge function
resource "aws_lambda_function" "auth" {
  provider         = aws.us_east_1
  filename         = data.archive_file.lambda_auth.output_path
  function_name    = "${var.project_name}-${var.environment}-docs-auth"
  role            = aws_iam_role.lambda_edge.arn
  handler         = "index.handler"
  source_code_hash = data.archive_file.lambda_auth.output_base64sha256
  runtime         = "nodejs20.x"
  timeout         = 5
  memory_size     = 128
  publish         = true # Required for Lambda@Edge

  environment {
    variables = {
      GITHUB_CLIENT_ID     = var.github_client_id
      GITHUB_CLIENT_SECRET = var.github_client_secret
      GITHUB_ORG          = var.github_org
      ALLOWED_TEAMS       = join(",", var.allowed_teams)
      PUBLIC_PATHS        = join(",", var.public_paths)
    }
  }

  tags = var.tags
}

# CloudWatch Log Group for Lambda@Edge
# Note: Lambda@Edge logs are created in the region where the function executes
resource "aws_cloudwatch_log_group" "lambda_edge" {
  provider              = aws.us_east_1
  name                  = "/aws/lambda/us-east-1.${aws_lambda_function.auth.function_name}"
  retention_in_days     = var.log_retention_days
  skip_destroy          = false

  tags = var.tags
}

# CloudWatch metric alarm for Lambda errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  provider            = aws.us_east_1
  alarm_name          = "${var.project_name}-${var.environment}-lambda-auth-errors"
  alarm_description   = "Lambda@Edge authentication function errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.auth.function_name
  }

  alarm_actions = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  tags = var.tags
}

# CloudWatch metric alarm for Lambda throttles
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  provider            = aws.us_east_1
  alarm_name          = "${var.project_name}-${var.environment}-lambda-auth-throttles"
  alarm_description   = "Lambda@Edge authentication function throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.auth.function_name
  }

  alarm_actions = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  tags = var.tags
}
