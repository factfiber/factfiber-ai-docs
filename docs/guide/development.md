# Development Guide

This guide covers development setup, contribution guidelines, testing procedures,
and code standards for the FactFiber Documentation Infrastructure.

## Development Setup

### Prerequisites

- **Python 3.13+**: Required for compatibility with latest language features
- **Git**: Version control and repository management
- **Docker**: Container runtime for local development
- **Kubernetes**: Container orchestration (optional, for full stack)
- **DevSpace**: Development workflow tool for Kubernetes

### Local Environment Setup

#### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/factfiber/factfiber-ai-docs.git
cd factfiber-ai-docs

# Install in development mode
pip install -e .[dev]

# Install pre-commit hooks (REQUIRED)
pre-commit install
```

#### 2. Environment Configuration

```bash
# Copy example environment
cp .env.example .env

# Configure required variables
export GITHUB_TOKEN="your_github_personal_access_token"
export GITHUB_ORG="factfiber"
export AUTH_SECRET_KEY="your_jwt_secret_key"
export ENVIRONMENT="development"
```

#### 3. Development Services

**Option A: Local Development**

```bash
# Start FastAPI server with hot-reloading (defaults to 127.0.0.1)
ff-docs serve-api --reload

# Or bind to all interfaces for network access
ff-docs serve-api --reload --host 0.0.0.0 --port 8000

# Start MkDocs development server (separate terminal)
docs-serve

# Or bind to all interfaces
docs-serve --dev-addr 0.0.0.0:8001

# Generate API documentation
docs-code
```

**Option B: DevSpace (Kubernetes)**

```bash
# Install DevSpace
curl -s -L "https://github.com/loft-sh/devspace/releases/latest" | sed -nE 's!.*"([^"]*devspace-linux-amd64)".*!https://github.com\1!p' | xargs -n 1 curl -L -o devspace && chmod +x devspace

# Start development environment
./devspace dev

# Access services:
# - FastAPI: http://localhost:8000
# - FastAPI Docs: http://localhost:8000/docs
# - MkDocs: http://localhost:8001
```

### Development Workflow

#### 1. Code Changes

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test
# ... development work ...

# Run pre-commit checks
pre-commit run --all-files

# Run tests
pytest tests/ -v

# Generate updated documentation
docs-code
docs-build
```

#### 2. Testing Your Changes

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# API tests
pytest tests/integration/test_api.py -v

# Test coverage
pytest --cov=ff_docs --cov-report=html
```

#### 3. Documentation Updates

```bash
# Update code documentation
docs-code

# Test documentation build
docs-build

# Serve locally to verify
docs-serve
```

## Code Standards

### Code Style Guidelines

Following the standards established in `CLAUDE.md`:

#### **Line Length**

- **Maximum: 80 characters**
- Use black for automatic formatting
- Break long lines sensibly

#### **Type Annotations**

```python
# REQUIRED - All function signatures must have type annotations
def process_repository(
    repo_url: str,
    config: ProcessingConfig,
    timeout: int = 300
) -> ProcessingResult:
    """Process repository with given configuration."""
    pass

# Use proper imports for complex types
from typing import Dict, List, Optional, Union
from pathlib import Path
```

#### **Docstring Standards**

```python
def enroll_repository(
    repository_url: str,
    documentation_path: str = "docs/",
    access_permissions: Optional[List[str]] = None
) -> EnrollmentResult:
    """
    Enroll a new repository in the documentation system.

    This function validates repository access, sets up webhooks, and
    configures documentation synchronization for the specified repository.

    Args:
        repository_url: GitHub repository URL in format
            'https://github.com/org/repo'.
        documentation_path: Path to documentation directory within
            repository. Defaults to 'docs/'.
        access_permissions: List of GitHub teams that should have access.
            If None, uses repository's default team permissions.

    Returns:
        EnrollmentResult containing:
            - success: Boolean indicating enrollment success
            - repository_id: Unique identifier for enrolled repository
            - webhook_url: Configured webhook endpoint URL
            - errors: List of any errors encountered during enrollment

    Raises:
        RepositoryAccessError: If repository is not accessible or
            user lacks required permissions.
        WebhookConfigurationError: If webhook setup fails.
        ValidationError: If repository doesn't meet documentation standards.

    Example:
        >>> result = enroll_repository(
        ...     "https://github.com/factfiber/new-project",
        ...     access_permissions=["docs-team", "platform-team"]
        ... )
        >>> print(f"Enrolled: {result.success}")
        True

    Note:
        Repository must follow FactFiber documentation standards.
        See documentation_standards.md for requirements.
    """
```

#### **Error Handling**

```python
# Use specific exceptions with clear messages
def validate_repository_access(repo_url: str) -> bool:
    try:
        response = github_client.get_repo(repo_url)
        return response.status_code == 200
    except GitHubAPIError as e:
        msg = f"Failed to access repository {repo_url}: {e}"
        raise RepositoryAccessError(msg) from e
    except Exception as e:
        msg = f"Unexpected error validating {repo_url}: {e}"
        raise ValidationError(msg) from e
```

### Import Organization

```python
# Standard library imports
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Third-party imports
import httpx
import pydantic
from fastapi import FastAPI, HTTPException
from github import Github

# Local imports
from ff_docs.config import settings
from ff_docs.models import RepositoryConfig
from ff_docs.utils import validate_url
```

### Function Complexity

- **Maximum arguments: 5** (use `# noqa: PLR0913` only when justified)
- **Use dataclasses** for complex parameter groups:

```python
@dataclass
class RepositoryEnrollmentRequest:
    repository_url: str
    documentation_path: str = "docs/"
    access_permissions: Optional[List[str]] = None
    webhook_events: List[str] = field(default_factory=lambda: ["push", "pull_request"])

def enroll_repository(request: RepositoryEnrollmentRequest) -> EnrollmentResult:
    """Enroll repository using structured request."""
    pass
```

## Testing Standards

### Test Organization

```text
tests/
├── unit/                       # Unit tests
│   ├── test_config.py         # Configuration tests
│   ├── test_auth.py           # Authentication tests
│   └── test_models.py         # Data model tests
├── integration/                # Integration tests
│   ├── test_api.py            # API endpoint tests
│   ├── test_webhooks.py       # Webhook processing tests
│   └── test_github.py         # GitHub integration tests
├── fixtures/                   # Test data and fixtures
│   ├── repository_configs.py  # Sample configurations
│   └── webhook_payloads.json  # Example webhook data
└── conftest.py                # Pytest configuration
```

### Test Best Practices

#### **Test Structure**

```python
def test_repository_enrollment_success():
    """Test successful repository enrollment process."""
    # Arrange - Set up test data
    repo_url = "https://github.com/factfiber/test-repo"
    request = RepositoryEnrollmentRequest(
        repository_url=repo_url,
        access_permissions=["docs-team"]
    )

    # Act - Execute the function under test
    result = enroll_repository(request)

    # Assert - Verify the results
    assert result.success is True
    assert result.repository_id is not None
    assert result.webhook_url.startswith("https://")
    assert len(result.errors) == 0
```

#### **Mocking External Dependencies**

```python
@pytest.mark.asyncio
async def test_github_webhook_processing(mock_github_client):
    """Test GitHub webhook processing with mocked GitHub API."""
    # Mock GitHub API responses
    mock_github_client.get_repo.return_value = MockRepository()

    # Test webhook processing
    payload = {
        "action": "push",
        "repository": {"full_name": "factfiber/test-repo"}
    }

    result = await process_github_webhook(payload)

    assert result.processed is True
    mock_github_client.get_repo.assert_called_once()
```

#### **Testing Error Conditions**

```python
def test_repository_enrollment_invalid_url():
    """Test repository enrollment with invalid URL."""
    request = RepositoryEnrollmentRequest(
        repository_url="not-a-valid-url"
    )

    with pytest.raises(ValidationError) as exc_info:
        enroll_repository(request)

    assert "Invalid repository URL" in str(exc_info.value)
```

### Running Tests

#### **Local Testing**

```bash
# All tests
pytest tests/ -v

# Specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v

# With coverage
pytest --cov=ff_docs --cov-report=html --cov-report=term

# Specific test file
pytest tests/unit/test_auth.py -v

# Specific test function
pytest tests/unit/test_auth.py::test_jwt_token_generation -v
```

#### **DevSpace Testing**

```bash
# Run tests in development container
devspace run test

# Interactive testing session
devspace enter
pytest tests/ -v --pdb
```

## Contributing

### Contribution Workflow

#### 1. **Before Starting**

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/descriptive-name

# Verify development environment
pre-commit run --all-files
pytest tests/unit/ -v
```

#### 2. **Development Process**

- **Write tests first** for new functionality
- **Follow code standards** outlined above
- **Update documentation** for API changes
- **Keep commits focused** and well-described

#### 3. **Before Submitting**

```bash
# Run full test suite
pytest tests/ -v

# Check code quality
pre-commit run --all-files

# Update documentation
docs-code
docs-build

# Verify no regressions
docs-serve  # Manual verification
```

#### 4. **Pull Request Guidelines**

- **Clear description** of changes and motivation
- **Link to issues** being addressed
- **Include tests** for new functionality
- **Update documentation** as needed
- **Small, focused changes** preferred over large PRs

### Code Review Process

#### **Review Checklist**

- [ ] **Functionality**: Does the code work as intended?
- [ ] **Tests**: Are there adequate tests with good coverage?
- [ ] **Documentation**: Are docstrings and docs updated?
- [ ] **Standards**: Does code follow style guidelines?
- [ ] **Security**: Are there any security considerations?
- [ ] **Performance**: Any performance implications?

#### **Review Response**

- **Address all feedback** constructively
- **Ask questions** for unclear feedback
- **Update tests** based on review suggestions
- **Squash commits** before merging if requested

## Debugging and Troubleshooting

### Common Development Issues

#### **Import Errors**

```bash
# Verify installation
pip list | grep ff-docs

# Reinstall in development mode
pip uninstall ff-docs
pip install -e .[dev]

# Check Python path
python -c "import sys; print(sys.path)"
```

#### **Authentication Issues**

```bash
# Verify GitHub token
gh auth status

# Test token permissions
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# Check environment variables
env | grep GITHUB
```

#### **Documentation Build Failures**

```bash
# Debug MkDocs configuration
mkdocs config

# Verbose build output
mkdocs build --verbose

# Check for broken links
mkdocs build --strict
```

### Debugging Tools

#### **FastAPI Development**

```python
# Enable debug mode
app = FastAPI(debug=True)

# Add request logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use pdb for debugging
import pdb; pdb.set_trace()
```

#### **Database Debugging**

```bash
# DevSpace database access
devspace run shell
# Inside container:
# Check database connectivity, run queries, etc.
```

## Performance Considerations

### Development Performance

#### **Fast Development Cycle**

- **Use DevSpace** for rapid iteration
- **Enable hot-reloading** for both FastAPI and MkDocs
- **Parallel testing** with pytest-xdist
- **Incremental documentation builds**

#### **Resource Management**

```bash
# Monitor resource usage
docker stats
kubectl top pods

# Optimize container resources
# See devspace.yaml for configuration
```

### Code Performance

#### **Async Best Practices**

```python
# Use async/await for I/O operations
async def process_repository_async(repo_url: str) -> ProcessingResult:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.github.com/repos/{repo_url}")
        return ProcessingResult(data=response.json())

# Batch operations when possible
async def process_multiple_repositories(repo_urls: List[str]) -> List[ProcessingResult]:
    tasks = [process_repository_async(url) for url in repo_urls]
    return await asyncio.gather(*tasks)
```

#### **Memory Optimization**

```python
# Use generators for large datasets
def process_large_repository(repo_path: Path) -> Iterator[ProcessedFile]:
    for file_path in repo_path.rglob("*.md"):
        yield process_markdown_file(file_path)

# Limit concurrent operations
semaphore = asyncio.Semaphore(10)  # Max 10 concurrent operations
```

## Security Guidelines

### Development Security

#### **Secret Management**

```bash
# NEVER commit secrets to repository
# Use environment variables or secret management

# Example .env (not committed)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
AUTH_SECRET_KEY=your-secret-key
DATABASE_PASSWORD=secure-password
```

#### **Input Validation**

```python
# Always validate inputs with Pydantic
class RepositoryRequest(BaseModel):
    repository_url: HttpUrl  # Validates URL format
    documentation_path: str = Field(regex=r"^[a-zA-Z0-9/_-]+/$")

    @validator('repository_url')
    def validate_github_url(cls, v):
        if not str(v).startswith('https://github.com/'):
            raise ValueError('Must be a GitHub repository URL')
        return v
```

#### **Authentication in Development**

```python
# Use test tokens for development
# Create separate GitHub app for development
# Never use production credentials in development
```

## Documentation Maintenance

### Keeping Documentation Current

#### **Automated Updates**

- **Pre-commit hooks** regenerate API docs
- **GitHub Actions** rebuild on code changes
- **Webhook integration** keeps portal current

#### **Manual Review Process**

- **Monthly documentation review** for accuracy
- **Update examples** with current API usage
- **Review external links** for validity
- **Update dependency versions** in examples

### Documentation Quality

#### **Writing Standards**

- **Clear, concise language**
- **Complete, working examples**
- **Up-to-date screenshots** and diagrams
- **Cross-references** between related topics

#### **Review Checklist**

- [ ] **Accuracy**: Information is current and correct
- [ ] **Completeness**: All necessary information included
- [ ] **Clarity**: Easy to understand and follow
- [ ] **Examples**: Working code examples provided
- [ ] **Links**: All internal and external links work

---

Following this development guide ensures consistent, high-quality contributions to
the FactFiber Documentation Infrastructure while maintaining security and
performance standards.
