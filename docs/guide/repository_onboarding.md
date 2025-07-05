# Repository Onboarding Guide

This guide walks you through the process of preparing your repository for
integration with the FactFiber unified documentation system.

## Before You Start

Ensure you have:

- [ ] Repository with Python code and existing or planned documentation
- [ ] Poetry for dependency management
- [ ] GitHub repository with appropriate access permissions
- [ ] Understanding of your documentation scope and audience

## Step-by-Step Onboarding

### 1. Repository Structure Setup

Create the standardized documentation directory structure:

```bash
# In your repository root
mkdir -p docs/{guide,reference,api,assets/{images,diagrams}}

# Create required index files
touch docs/index.md
touch docs/guide/index.md
touch docs/reference/index.md
```

### 2. Copy Documentation Standards

Copy the documentation standards into your repository:

```bash
# Download the standards guide
curl -o docs/guide/documentation_standards.md \
  https://raw.githubusercontent.com/factfiber/ff-docs/main/docs/guide/documentation_standards.md
```

### 3. Configure MkDocs

Create `mkdocs.yml` in your repository root:

```yaml
site_name: "Your Project Documentation"
site_description: "Documentation for Your Project"
site_url: "https://docs.factfiber.ai/projects/your-repo/"

theme:
  name: material
  palette:
    - scheme: default
      primary: blue
      accent: blue
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.highlight
    - search.share
    - content.code.copy
    - content.action.edit

plugins:
  - search:
      separator: '[\s\-,:!=\[\]()"`/]+|\.(?!\d)|&[lg]t;|(?!\b)(?=[A-Z][a-z])'
  - mermaid2:
      arguments:
        theme: default

markdown_extensions:
  - admonition
  - codehilite:
      guess_lang: false
  - toc:
      permalink: true
  - pymdownx.arithmatex:
      generic: true
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format

extra_javascript:
  - https://polyfill.io/v3/polyfill.min.js?features=es6
  - https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js

nav:
  - Home: index.md
  - Guide:
    - guide/index.md
    - Getting Started: guide/getting-started.md
    - Architecture: guide/architecture.md
    - Development: guide/development.md
    - Documentation Standards: guide/documentation_standards.md
  - Reference:
    - reference/index.md
    # Add your package-specific navigation here
  - API Reference: api/index.html

edit_uri: blob/main/docs/
```

### 4. Configure pdoc

Add to your `pyproject.toml`:

```toml
[tool.poetry.scripts]
docs-api = "bash -c 'pdoc -o docs/api --math --mermaid src/**/*.py'"
docs-serve = "mkdocs serve --dev-addr 0.0.0.0:8000"
docs-build = "mkdocs build"
docs-clean = "rm -rf docs/api/* site/*"

[tool.pdoc]
output_directory = "docs/api"
include_undocumented = true
show_source = true
math = true
mermaid = true
```

Add required dependencies:

```toml
[tool.poetry.dependencies]
# Your existing dependencies...

[tool.poetry.group.docs.dependencies]
mkdocs = "^1.5.0"
mkdocs-material = "^9.0.0"
mkdocs-mermaid2-plugin = "^1.0.0"
pdoc = "^14.0.0"
pymdown-extensions = "^10.0.0"
```

### 5. Create GitHub Actions Workflow

Create `.github/workflows/docs.yml`:

```yaml
name: Documentation

on:
  push:
    branches: [main, develop]
    paths: ['docs/**', 'src/**', 'mkdocs.yml', 'pyproject.toml']
  pull_request:
    branches: [main]
    paths: ['docs/**', 'src/**', 'mkdocs.yml']

jobs:
  build-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: 1.6.1
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Cache Poetry dependencies
        uses: actions/cache@v3
        with:
          path: .venv
          key: poetry-${{ hashFiles('**/poetry.lock') }}

      - name: Install dependencies
        run: |
          poetry install --with docs

      - name: Generate API documentation
        run: |
          poetry run docs-api

      - name: Build documentation
        run: |
          poetry run docs-build

      - name: Deploy to GitHub Pages
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site
          force_orphan: true
```

### 6. Create Required Content Files

#### `docs/index.md`

```markdown
# Your Project Name

Brief description of your project and its purpose.

## Overview

Provide a high-level overview of what your project does, who it's for, and why it's useful.

## Quick Start

Link to getting started guide:

- [Getting Started](guide/getting-started.md) - Installation and basic usage
- [Architecture](guide/architecture.md) - System design and components
- [API Reference](api/) - Generated API documentation

## Key Features

- Feature 1: Brief description
- Feature 2: Brief description
- Feature 3: Brief description

## Documentation Sections

### [User Guide](guide/)
Cross-cutting documentation including tutorials, architecture, and development guides.

### [Reference](reference/)
Component-specific technical documentation organized by package structure.

### [API Documentation](api/)
Auto-generated API reference from code docstrings.

## Contributing

See [Development Guide](guide/development.md) for information on contributing to this project.
```

#### `docs/guide/index.md`

```markdown
# User Guide

This section contains cross-cutting documentation that spans multiple components or provides high-level guidance.

## Getting Started

- [Installation and Setup](getting-started.md)
- [Basic Usage Examples](getting-started.md#usage)
- [Configuration](getting-started.md#configuration)

## Architecture and Design

- [System Architecture](architecture.md)
- [Design Decisions](architecture.md#design-decisions)
- [Component Overview](architecture.md#components)

## Development

- [Development Setup](development.md)
- [Contributing Guidelines](development.md#contributing)
- [Testing](development.md#testing)
- [Documentation Standards](documentation_standards.md)

## Advanced Topics

Add links to advanced topics as you create them:

- Performance optimization
- Deployment considerations
- Integration patterns
```

#### `docs/reference/index.md`

```markdown
# Technical Reference

This section contains component-specific technical documentation organized by package structure.

## Package Documentation

<!-- Update this based on your actual package structure -->

### Core Components

- [`your_package.core`](your_package/core/) - Core functionality and base classes
- [`your_package.utils`](your_package/utils/) - Utility functions and helpers

### Domain-Specific Modules

- [`your_package.processing`](your_package/processing/) - Data processing components
- [`your_package.models`](your_package/models/) - Model definitions and implementations

## Cross-References

- [API Documentation](../api/) - Auto-generated API reference
- [Architecture Guide](../guide/architecture.md) - High-level system design
- [Development Guide](../guide/development.md) - Development workflows

## Navigation

Each package section includes:

- **Overview**: Purpose and scope of the package
- **Key Concepts**: Important concepts and terminology
- **Usage Examples**: Practical examples and patterns
- **Implementation Details**: Technical specifications and details
```

### 7. Install Dependencies and Test

```bash
# Install documentation dependencies
poetry install --with docs

# Generate API documentation
poetry run docs-api

# Test local documentation server
poetry run docs-serve

# Build static documentation
poetry run docs-build
```

### 8. Configure CI/CD Secrets

If your repository uses the centralized documentation deployment pipeline, set up required GitHub Actions secrets:

```bash
# Deploy all required secrets from AWS infrastructure
./scripts/deploy-github-secrets.sh factfiber/your-repo-name
```

This script automatically configures:

- `AWS_DEPLOY_ROLE_ARN` - IAM role for deployment
- `DOCS_S3_BUCKET` - S3 bucket name
- `CLOUDFRONT_DISTRIBUTION_ID` - CloudFront distribution
- `PRIVATE_REPO_TOKEN` - GitHub PAT for private dependencies

**Prerequisites**:

- AWS CLI configured with `factfiber-docs-deploy` profile
- GitHub CLI (`gh`) authenticated
- Terraform infrastructure deployed in `aws/terraform/environments/prod`

### 9. Register with Documentation Portal

Contact the documentation team to register your repository:

1. **Repository URL**: Provide your repository's GitHub URL
2. **Documentation Path**: Usually `docs/` in your repository
3. **Access Permissions**: Specify which teams should have access
4. **Build Configuration**: Confirm your build process works
5. **CI/CD Status**: Confirm secrets are deployed if using central pipeline

## Centralized Configuration Strategy

**Important**: The FactFiber documentation portal follows a **centralized
configuration** approach to ensure consistency and reduce maintenance overhead.

### What's Centralized

The main portal (`factfiber/factfiber-ai-docs`) provides:

- **Theme Configuration**: Material theme settings, colors, features
- **Plugin Configuration**: Mermaid, search, git-revision-date, minification
- **JavaScript/CSS**: MathJax, Mermaid libraries, custom styling
- **Build Settings**: Strict mode, directory URLs, navigation patterns

### What Repositories Configure

Individual repositories should keep their `mkdocs.yml` **minimal** and focused on:

- **Site metadata**: `site_name`, `site_description`, `site_url`
- **Repository info**: `repo_name`, `repo_url`, `edit_uri`
- **Navigation structure**: Repository-specific content organization
- **Project-specific plugins**: Only if absolutely necessary

### Benefits of Centralization

1. **Consistency**: All documentation looks and behaves the same
2. **Maintenance**: Updates to themes/plugins happen in one place
3. **Quality**: Advanced features (math, diagrams, search) work everywhere
4. **Performance**: Optimized configurations tested at scale

### Repository mkdocs.yml Template

Use this **minimal template** for your repository:

```yaml
site_name: "Your Project Documentation"
site_description: "Documentation for Your Project"
site_url: "https://docs.factfiber.ai/projects/your-repo/"

repo_name: "factfiber/your-repo"
repo_url: "https://github.com/factfiber/your-repo"
edit_uri: "blob/main/docs/"

# Minimal theme (portal will override with full configuration)
theme:
  name: material

# Minimal plugins (portal provides comprehensive plugin set)
plugins:
  - search

# Basic markdown extensions (portal adds advanced features)
markdown_extensions:
  - admonition
  - toc:
      permalink: true

# Your navigation structure
nav:
  - Home: index.md
  - Guide:
      - guide/index.md
      - Getting Started: guide/getting-started.md
      - Architecture: guide/architecture.md
  - Reference:
      - reference/index.md
  - Code Reference: reference/code/index.html
```

**Why minimal?** The portal's multirepo plugin will merge your navigation with the centralized theme, plugins, and features.

## Customization

### Theme Customization

If you need project-specific customization, add **only essential changes** to your `mkdocs.yml`:

```yaml
theme:
  name: material
  palette:
    - scheme: default
      primary: indigo      # Change to your preferred color
      accent: indigo
  features:
    - navigation.instant   # Add instant loading
    - navigation.tracking  # Add URL tracking
```

### Navigation Structure

Customize the navigation structure in `mkdocs.yml`:

```yaml
nav:
  - Home: index.md
  - Guide:
    - guide/index.md
    - Getting Started: guide/getting-started.md
    - Architecture: guide/architecture.md
    - Your Custom Section: guide/custom-section.md
  - Reference:
    - reference/index.md
    - Your Package: reference/your-package/index.md
  - API Reference: api/index.html
```

### Additional Plugins

Add useful plugins to `mkdocs.yml`:

```yaml
plugins:
  - search
  - mermaid2
  - git-revision-date-localized:  # Add last updated dates
      type: date
  - minify:  # Minify HTML/CSS/JS
      minify_html: true
```

## Troubleshooting

### Common Issues

**1. pdoc Generation Fails**

```bash
# Check if source files exist
ls src/

# Verify Python path
poetry run python -c "import sys; print(sys.path)"

# Run pdoc with verbose output
poetry run pdoc -v -o docs/reference/code src/
```

**2. MkDocs Build Fails**

```bash
# Build with verbose output
poetry run mkdocs build --verbose

# Check for broken links
poetry run mkdocs build --strict
```

**3. Link Validation Issues**

When your repository is imported into the central portal, you may see warnings about missing anchors or broken internal links:

```
INFO - Doc file contains a link '#missing-section', but there is no such anchor on this page.
```

**To fix these issues**:

1. **Verify all internal links**: Ensure every `#anchor-link` points to an actual header
2. **Check header formatting**: Headers must use proper markdown (`# Header`, `## Subheader`)
3. **Validate anchor names**: Anchors are auto-generated from headers (spaces become dashes, special characters removed)

```bash
# Example: This header
## Memory Recovery and Cleanup Testing

# Creates this anchor
#memory-recovery-and-cleanup-testing

# So this link works:
[See cleanup testing](#memory-recovery-and-cleanup-testing)
```

1. **Test locally before pushing**:

```bash
poetry run mkdocs serve
# Navigate to your pages and click all internal links
```

**4. Git Revision Date Warnings**

Warnings like `has no git logs, using current timestamp` are normal for:

- Newly created files
- Files in imported repositories (the portal creates a temporary copy)

These warnings don't affect functionality.

**5. GitHub Actions Fail**

- Check that `pyproject.toml` includes docs dependencies
- Verify all required files are committed
- Check GitHub Actions logs for specific error messages
- Ensure repository follows documentation standards exactly

### Getting Help

- Check the [Documentation Standards](documentation_standards.md) guide
- Review working examples in the timbuktu repository
- Contact the documentation team for portal integration issues

## Next Steps

After completing onboarding:

1. **Content Migration**: Move existing documentation to new structure
2. **Code Documentation**: Add Google-style docstrings to your code
3. **Portal Integration**: Work with team to integrate with central portal
4. **Team Training**: Train team members on new documentation workflow
5. **Continuous Improvement**: Regularly review and improve documentation

## Maintenance

### Regular Tasks

- **Update Dependencies**: Keep MkDocs and plugins updated
- **Review Documentation**: Regular content reviews for accuracy
- **Monitor Builds**: Ensure GitHub Actions continue to work
- **User Feedback**: Collect and act on user feedback

### Quality Metrics

Track these metrics to maintain documentation quality:

- **Build Success Rate**: GitHub Actions success rate
- **Link Health**: Broken link detection and fixing
- **Content Freshness**: How recently content was updated
- **User Engagement**: Which sections are most accessed

---

Following this guide ensures your repository integrates seamlessly with the
FactFiber documentation ecosystem while maintaining high standards for content
and user experience.
