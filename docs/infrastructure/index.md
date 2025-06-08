# Infrastructure Documentation

Welcome to the FactFiber documentation infrastructure documentation.
This section covers all aspects of our infrastructure setup, deployment,
and operations.

## Overview

Our documentation infrastructure is built on AWS using modern cloud-native practices:

- **AWS S3**: Static site hosting with versioning and lifecycle management
- **CloudFront**: Global CDN with Lambda@Edge authentication
- **Lambda@Edge**: GitHub OAuth-based access control
- **Route53**: DNS management with cross-account architecture
- **Terraform**: Infrastructure as Code for reproducible deployments

## Architecture

```mermaid
graph TB
    Users[Users] --> CF[CloudFront Distribution]
    CF --> LE[Lambda@Edge Auth]
    LE --> S3[S3 Documentation Bucket]
    LE --> GH[GitHub OAuth]

    R53[Route53] --> CF
    GA[GitHub Actions] --> S3
    GA --> CF

    subgraph "Cross-Account"
        R53
    end

    subgraph "Main Infrastructure Account"
        CF
        LE
        S3
        GA
    end
```

## Documentation Sections

### [AWS Infrastructure](aws/)

Complete AWS setup and configuration documentation:

- Setup guides and prerequisites
- Security configuration and best practices
- Operations and maintenance procedures
- Troubleshooting and monitoring

### [Terraform](terraform/)

Infrastructure as Code documentation:

- Module architecture and design
- Environment management (dev/prod)
- Deployment procedures and automation
- State management and backends

### [Operations](../operations/)

Day-to-day operational procedures:

- Deployment workflows
- Monitoring and alerting
- Incident response procedures
- Backup and disaster recovery

## Quick Start

1. **Prerequisites**: Ensure you have AWS CLI and Terraform installed
2. **Authentication**: Configure AWS profiles per [setup guide](aws/setup-guide.md)
3. **Deploy Infrastructure**: Follow [deployment guide](aws/operations-runbook.md)
4. **Configure DNS**: Set up [custom domain](aws/acm-certificate-setup.md)

## Security

Our infrastructure follows AWS Well-Architected Framework security principles:

- **Identity and Access Management**: Least privilege IAM roles
- **Data Protection**: Encryption at rest and in transit
- **Infrastructure Protection**: Network security and monitoring
- **Detective Controls**: Logging and alerting
- **Incident Response**: Automated monitoring and manual procedures

See our [Security Review](../tmp/security-review.md) for detailed security analysis.

## Contributing

When making infrastructure changes:

1. **Review Documentation**: Ensure changes align with documented standards
2. **Test Changes**: Use development environment first
3. **Security Review**: Consider security implications
4. **Update Documentation**: Keep documentation current with changes

For detailed procedures, see our [contributing guide](../dev/contributing.md).
