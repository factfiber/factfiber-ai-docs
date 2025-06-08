# ACM Certificate Setup for docs.factfiber.ai

To use the custom domain `docs.factfiber.ai`, you need an ACM certificate in the us-east-1 region.

## Option 1: Request New Certificate (Recommended)

```bash
# Request certificate using DNS validation
aws acm request-certificate \
    --domain-name docs.factfiber.ai \
    --validation-method DNS \
    --profile fc-aws-infra \
    --region us-east-1
```

### DNS Validation Process

After requesting the certificate, get the validation records:

```bash
# Get the certificate ARN from the previous command output
CERT_ARN="arn:aws:acm:us-east-1:YOUR_ACCOUNT:certificate/YOUR_CERT_ID"

# Get validation records
aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --profile fc-aws-infra \
    --region us-east-1 \
    --query 'Certificate.DomainValidationOptions[0].ResourceRecord'
```

Add the CNAME validation record to Route53:

```bash
# The validation will provide a CNAME record like:
# Name: _abc123.docs.factfiber.ai
# Value: _def456.acm-validations.aws.

# Add it using the k8 profile (where Route53 is hosted)
aws route53 change-resource-record-sets \
    --hosted-zone-id Z04527812OYH5L6PJJUT7 \
    --profile k8 \
    --change-batch '{
      "Changes": [{
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "_abc123.docs.factfiber.ai",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [{
            "Value": "_def456.acm-validations.aws."
          }]
        }
      }]
    }'
```

Wait for validation (usually takes a few minutes):

```bash
# Check certificate status
aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --profile fc-aws-infra \
    --region us-east-1 \
    --query 'Certificate.Status'
```

## Option 2: Use Wildcard Certificate

If factfiber.ai already has a wildcard certificate (`*.factfiber.ai`) in us-east-1, you can use that.

```bash
# List existing certificates
aws acm list-certificates \
    --profile fc-aws-infra \
    --region us-east-1 \
    --query 'CertificateSummaryList[?contains(DomainName, `factfiber.ai`)]'
```

## Terraform Configuration

Once you have the certificate ARN, add it to your `terraform.tfvars`:

```hcl
# ACM certificate for custom domain
acm_certificate_arn = "arn:aws:acm:us-east-1:YOUR_ACCOUNT:certificate/YOUR_CERT_ID"
```

## Important Notes

1. **Region Requirement**: The certificate MUST be in us-east-1 for CloudFront
2. **Validation Time**: DNS validation usually completes within 5-30 minutes
3. **Auto-renewal**: ACM certificates auto-renew as long as the validation DNS records remain in place
4. **Multiple Domains**: You can request a certificate with multiple domains:

   ```bash
   aws acm request-certificate \
       --domain-name docs.factfiber.ai \
       --subject-alternative-names www.docs.factfiber.ai \
       --validation-method DNS \
       --profile fc-aws-infra \
       --region us-east-1
   ```

## Troubleshooting

### Certificate Not Validating

1. Ensure DNS records are correctly added
2. Check DNS propagation: `dig _abc123.docs.factfiber.ai CNAME`
3. Verify the CNAME record ends with a dot (.)

### Certificate Not Available in CloudFront

1. Ensure certificate is in us-east-1 region
2. Check certificate status is "ISSUED"
3. Verify domain names match CloudFront aliases exactly
