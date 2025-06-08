# Terraform Infrastructure Documentation

This section contains documentation for our Terraform infrastructure management.

## Structure

```
terraform/
├── environments/          # Environment-specific configurations
│   ├── dev/               # Development environment
│   └── prod/              # Production environment
└── modules/               # Reusable Terraform modules
    ├── cloudfront/        # CloudFront distribution module
    ├── iam/               # IAM roles and policies
    ├── lambda-edge/       # Lambda@Edge authentication
    ├── lambda-edge-config/ # Lambda@Edge configuration generator
    ├── route53/           # DNS management
    ├── route53-cross-account/ # Cross-account Route53 access
    └── s3/                # S3 bucket management
```

## Key Concepts

### Environment Separation

- **Development**: Testing and development workloads
- **Production**: Live documentation site (docs.factfiber.ai)

### Module Architecture

Our Terraform infrastructure uses a modular approach where each component is
isolated into reusable modules. This allows for:

- **Consistency**: Same module used across environments
- **Maintainability**: Changes in one place affect all usages
- **Testing**: Modules can be tested independently

### Security Model

- **Cross-Account Access**: Route53 managed in separate AWS account
- **Least Privilege**: IAM roles with minimal required permissions
- **Infrastructure Roles**: Dedicated roles for Terraform operations

## Getting Started

1. **Setup AWS Profiles**: Configure authentication
2. **Initialize Terraform**: Run `terraform init` in environment directory
3. **Plan Changes**: Review with `terraform plan`
4. **Apply Changes**: Deploy with `terraform apply`

## Related Documentation

- [AWS Infrastructure Setup](../aws/setup-guide.md)
- [Operations Runbook](../aws/operations-runbook.md)
- [Security Review](../../tmp/security-review.md)
