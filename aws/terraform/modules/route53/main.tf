# Route53 configuration for docs.factfiber.ai
# Uses cross-account access to manage records in the k8 account

# Provider for the Route53 account using assumed role
provider "aws" {
  alias = "route53"

  assume_role {
    role_arn     = var.cross_account_role_arn
    external_id  = var.external_id
    session_name = "factfiber-docs-route53"
  }
}

# Data source to get the hosted zone from Route53 account
data "aws_route53_zone" "factfiber" {
  provider = aws.route53
  name     = "factfiber.ai"
}

resource "aws_route53_record" "docs" {
  provider = aws.route53
  zone_id  = data.aws_route53_zone.factfiber.zone_id
  name     = "docs.factfiber.ai"
  type     = "A"

  alias {
    name                   = var.cloudfront_domain_name
    zone_id                = var.cloudfront_hosted_zone_id
    evaluate_target_health = false
  }
}

# ACM Certificate validation records
resource "aws_route53_record" "cert_validation" {
  provider = aws.route53
  for_each = {
    for dvo in var.acm_certificate_domain_validation : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.factfiber.zone_id
}

# ACM Certificate validation
resource "aws_acm_certificate_validation" "docs" {
  certificate_arn         = var.acm_certificate_arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]

  timeouts {
    create = "5m"
  }
}

# Optional: www.docs.factfiber.ai redirect
resource "aws_route53_record" "docs_www" {
  provider = aws.route53
  count    = var.create_www_redirect ? 1 : 0
  zone_id  = data.aws_route53_zone.factfiber.zone_id
  name     = "www.docs.factfiber.ai"
  type     = "A"

  alias {
    name                   = var.cloudfront_domain_name
    zone_id                = var.cloudfront_hosted_zone_id
    evaluate_target_health = false
  }
}
