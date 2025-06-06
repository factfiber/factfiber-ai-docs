output "docs_fqdn" {
  description = "Fully qualified domain name for docs site"
  value       = aws_route53_record.docs.fqdn
}

output "zone_id" {
  description = "Route53 zone ID"
  value       = data.aws_route53_zone.factfiber.zone_id
}
