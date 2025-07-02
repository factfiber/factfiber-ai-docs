# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working
with code in this repository.

## Active Issues and Tasks

**IMPORTANT**: For current issues and active investigations, see `tmp/issues/CLAUDE.md`

This file tracks:

- Active issues being worked on
- Associated documentation and test files
- Current investigation status
- Next steps for each issue

## Current Working State

### Sprint 4: Authentication & Security - COMPLETED ✅

Successfully implemented comprehensive authentication and security system:

### Sprint 5: Documentation Pipeline & Content Management - COMPLETED ✅

Successfully implemented real-time documentation synchronization system:

✅ **Completed in Sprint 5:**

- GitHub webhook handler for real-time documentation sync
- Content synchronization service with repository cloning and processing
- Markdown link rewriting system for unified navigation
- pdoc integration for automatic API documentation generation
- Unified MkDocs configuration generation
- Global search with repository access filtering
- Complete documentation pipeline from webhook to unified site

### Sprint 6: Frontend & User Experience + DevSpace - IN PROGRESS 🚧

Building comprehensive user interface and DevSpace development workflow:

✅ **Completed in Sprint 6:**

- DevSpace Kubernetes development workflow with hot-reloading
- Complete development environment with multiple profiles
- Docker containerization optimized for development
- Kubernetes manifests for full development stack

🚧 **In Progress - Sprint 6:**

- React TypeScript frontend with Material-UI v5
- Repository management interface with enrollment/unenrollment
- User dashboard with system status and activity feed
- Advanced search UI with filtering and faceted search
- Mobile responsive design with PWA features
- Frontend production Dockerfile and DevSpace integration

✅ **SPRINT 6 COMPLETED: Frontend & User Experience + DevSpace** 🎉

### Sprint 7: Production OAuth Authentication & SSL/TLS - COMPLETED ✅

Successfully implemented production-ready OAuth authentication system with SSL/TLS:

✅ **Completed in Sprint 7:**

- Complete GitHub OAuth2 flow with Lambda@Edge authentication
- SSL/TLS certificate setup using AWS ACM for docs.factfiber.ai
- OAuth callback handler with token exchange and user validation
- Team-based access control using actual GitHub organization teams
- Secure cookie management with proper domain and security settings
- SSM Parameter Store integration for secure credential management
- Comprehensive troubleshooting documentation and setup guides
- CloudFront custom domain configuration with certificate validation

**Production Features:**

- `https://docs.factfiber.ai` - Custom domain with valid SSL certificate
- `Lambda@Edge Authentication` - Request interception at CloudFront edge
- `GitHub Team Validation` - Membership verification in organization teams
- `Secure Session Management` - HttpOnly, Secure, SameSite cookies
- `State Parameter Support` - Redirect to original page after authentication

**Security Implementation:**

- All OAuth credentials stored securely in AWS SSM Parameter Store
- Team membership validated against: factfiber-ai-dev, factfiber-ai-learn, factfiber.ai, ff-analytics, ff-operations
- Authentication required for all documentation paths
- Proper error handling and access denied responses

✅ **Completed in Sprint 4:**

- JWT authentication system with secure token handling
- GitHub OAuth integration for user authentication
- OAuth2-Proxy integration for enterprise deployments
- Role-based access control (RBAC) with team-based permissions
- Comprehensive authentication middleware for FastAPI
- Secured API endpoints with permission-based access control
- Authentication routes (/auth/login, /auth/me, /auth/status, etc.)

**Authentication Methods:**

- `JWT` - JSON Web Token authentication for API access
- `OAuth2-Proxy` - Enterprise GitHub OAuth integration
- `GitHub API` - Direct GitHub token authentication

**Permission System:**

- Team-based permissions: factfiber-ai-dev, factfiber-ai-learn, factfiber.ai, ff-analytics, ff-operations
- Resource-level access control: docs:read, docs:write, repos:manage
- Repository-specific access validation

**Security Features:**

- Secure JWT token generation and validation
- GitHub team membership verification
- Request-level authentication middleware
- CORS configuration for web client integration

### Sprint 3: FastAPI Integration - COMPLETED ✅

Successfully implemented comprehensive REST API for repository management:

✅ **Completed in Sprint 3:**

- FastAPI server with complete REST endpoints (/repos/, /repos/config,
  /repos/discover, /repos/enroll, /repos/unenroll, /repos/enroll-all)
- CLI command `ff-docs serve-api` to start FastAPI server
- GitHub token optional configuration for basic testing
- Comprehensive Pydantic models for request/response validation
- Error handling with proper HTTP status codes
- Health check endpoints at /health/

### Sprint 5 Implementation: Documentation Pipeline & Content Management

**Successfully implemented comprehensive documentation pipeline for
unified multi-repository system:**

✅ **Completed in Sprint 5:**

- **Real-time GitHub Webhook Handler** (`/webhooks/github`) - Secure
  webhook processing with signature validation
- **Content Synchronization Service** - Automated repository cloning,
  git operations, and content processing
- **Transparent Link Rewriting System** - Preserves author workflow
  while enabling unified navigation
- **pdoc API Documentation Integration** - Automatic Python package
  discovery and HTML generation
- **Unified MkDocs Configuration Generator** - Dynamic config creation
  for all enrolled repositories
- **Global Search with Security Filtering** - Cross-repository search
  respecting GitHub permissions

**API Endpoints:**

- `POST /webhooks/github` - GitHub webhook handler for real-time
  documentation sync
- `GET /webhooks/sync/status/{repo}` - Repository synchronization
  status tracking
- `POST /webhooks/build/unified-config` - Generate unified MkDocs
  configuration
- `GET /docs/search` - Global search with repository access filtering

**Architecture Implementation:**

```text
GitHub Push → Webhook → Content Sync → Link Rewriting → Unified Config
     ↓             ↓           ↓              ↓              ↓
  Real-time     Validate    Clone &        Transform      Dynamic
   Updates      Enrollment  Process        Links          MkDocs
```

**Key Innovation**: Transparent link rewriting enables authors to write
normal MkDocs links (`[Setup Guide](../guide/setup.md)`) while the system
automatically converts them to unified format (`/projects/timbuktu/guide/setup/`)
without requiring any changes to repository documentation.

**Production Ready**: Complete documentation pipeline ready for
Sprint 6 frontend development.

## Project Overview

This is a Python-based documentation infrastructure project for
FactFiber.ai, focused on building a centralized multi-repository
documentation system using MkDocs. The project includes configuration,
deployment scripts, and templates for managing documentation across
multiple repositories.

## Development Commands

**ALWAYS USE POETRY FOR RUNNING COMMANDS AND INSTALLING PACKAGES**
when poetry.lock/pyproject.toml exists:

- Install dependencies: `poetry install`
- Add dependency: `poetry add package-name`
- Run development server: `poetry run mkdocs serve`
- Build documentation: `poetry run mkdocs build`
- Test: `poetry run pytest tests/ -v`
- Single test: `poetry run pytest tests/path/to/test_file.py::test_function -v`

## Documentation Generation Commands

**API Documentation with pdoc:**

- **CRITICAL**: Always use `--docformat google` flag (our standard)
- **RECOMMENDED**: Include `--math --mermaid --include-undocumented` for complete coverage
- Generate API docs: `poetry run docs-code` (uses enhanced configuration)
- Direct command:
  `poetry run pdoc --docformat google --math --mermaid --include-undocumented --html --output-dir docs/reference/code src/ff_docs`
- Serve API docs: `poetry run pdoc --docformat google --math --mermaid --http localhost:8080 src/ff_docs`

**Pre-commit Integration:**

- Run mkdocs-incremental: `poetry run mkdocs-incremental`
- Full pre-commit check: `poetry run pre-commit run --all-files`

## Linting and Formatting

- **ALWAYS run pre-commit for full linting**: `poetry run pre-commit run --all-files`
- For checking specific files only: `poetry run pre-commit run --files path/to/file.py`
- Individual linters (use pre-commit instead when possible):
  - Ruff check: `poetry run ruff check path/to/file.py`
  - Ruff format: `poetry run ruff format path/to/file.py`
  - Type check: `poetry run mypy src/`

### Systematic Linting Error Fixing Strategy

When facing multiple linting errors, use this systematic approach:

1. **Create a TODO list** to track progress through all errors
2. **Group errors by type** (T201, S603/S607, B904, EM102, etc.) for
   efficient batch fixing
3. **Fix errors in order of complexity** - start with simple ones like
   type annotations
4. **Test Black/Ruff interaction** after each fix to ensure noqa comments
   stay in place

### Common Linting Error Types and Fixes

**T201 (Print statements):**

```python
# Scripts: Add blanket suppression at top
# ruff: noqa: T201

# Library code: Use logging instead
import logging
logger = logging.getLogger(__name__)
logger.info("Processing %d items", count)  # Use % formatting for logging
```

**S603/S607 (Subprocess security):**

```python
# Add targeted noqa for legitimate subprocess calls
result = subprocess.run(  # noqa: S603
    ["cmake", "--version"],  # noqa: S607
    capture_output=True,
    text=True,
    check=True,
)
```

**B904 (Exception chaining):**

```python
# Always chain exceptions
try:
    risky_operation()
except OSError as e:
    msg = f"Operation failed: {e}"
    raise CustomError(msg) from e  # Chain with 'from e'
```

**EM102 (F-string in exception message):**

```python
# Extract f-string to variable first
try:
    operation()
except Error as e:
    msg = f"Failed processing {item}: {e}"  # Extract to variable
    raise ProcessingError(msg) from e  # Pass variable to exception
```

**RUF013 (Implicit Optional):**

```python
# Use explicit union syntax
def func(param: str | None = None) -> int | None:  # Not Optional[str]
    pass
```

**TRY301 (Exception raise within try):**

```python
# Extract error raising to helper function
def _raise_validation_error(self, message: str) -> None:
    """Raise validation error with consistent format."""
    raise ValidationError(f"Validation failed: {message}")

# Use in try block
if not condition:
    self._raise_validation_error("Invalid input")
```

### Common Linting Issues to Avoid

1. **Missing Type Annotations** - Annotate ALL function parameters and returns
2. **Using `Any` Type** - Use proper types with TYPE_CHECKING imports
3. **Unused Arguments** - Add `# noqa: ARG001` for placeholder functions
4. **Missing Issue Links** - Include issue references in all TODOs
5. **Line Length** - Keep lines under 80 characters
6. **Import Order** - Follow the import order specified in user's CLAUDE.md
7. **Magic Numbers** - Extract to named constants at module level
8. **Complex Exception Handling** - Use helper functions for error raising
9. **Subprocess Security** - Always use targeted noqa for legitimate calls
10. **Exception Chaining** - Always use `from e` when re-raising exceptions

### Black/Ruff Interaction: Handling Long Lines with `# noqa`

**CRITICAL**: When Black reformats long lines, `# noqa` comments must be
placed on the FIRST line of the reformatted statement.

```python
# WRONG - noqa on the wrong line after Black reformats
print(
    f"Very long message that exceeds 80 characters and gets reformatted"
)  # noqa: T201  ← This won't work!

# CORRECT - noqa on the first line
print(  # noqa: T201
    f"Very long message that exceeds 80 characters and gets reformatted"
)

# WRONG - noqa misplaced on function definition
def some_function(  # noqa: ARG001
    unused_param: str, other_param: int
) -> None:
    pass

# CORRECT - noqa on the line with the unused parameter
def some_function(
    unused_param: str,  # noqa: ARG001
    other_param: int,
) -> None:
    pass

# WRONG - noqa after Black reformats variable assignment
very_long_variable_name = some_very_long_function_call(
    arg1, arg2, arg3
)  # noqa: F841  ← Won't work after Black reformatting

# CORRECT - noqa on the first line
very_long_variable_name = some_very_long_function_call(  # noqa: F841
    arg1, arg2, arg3
)
```

## Code Style Guidelines

### Line Length

- **Maximum line length: 80 characters**
- For long docstrings: Use shorter, more concise descriptions
- For long comments: Break into multiple lines or use temporary variables
- For long function calls: Use temporary variables for clarity

### Copyright Header

All Python files should use the copyright header with the current year:

```python
# Copyright 2025 Fact Fiber Inc. All rights reserved.
```

### Style Guidelines

- Line length: 80 characters
- Quotes: Double quotes
- No trailing spaces
- Docstring style: Google. Docstrings should start with a new-line
- Imports: Use `from module import function` format, sort with\n  `isort`
- **Types: Type annotations are REQUIRED on ALL function signatures**
  - Use Python 3.13+ typing syntax
  - All parameters and return values must be typed
  - Never skip type annotations even for "simple" or "temporary" functions
- Error handling: Use explicit exceptions with messages
- Naming: snake_case for functions/variables, PascalCase for classes
- **NEVER DISABLE CODE COMPLEXITY LINTERS** - instead, break down complex
  functions into smaller, more focused functions

### Function Complexity (PLR0913)

- **Maximum arguments per function: 5**
- For functions with more than 5 arguments, use `# noqa: PLR0913` only when justified
- Consider dataclasses for complex parameter groups
- Use keyword-only arguments with `*` separator for clarity

### Boolean Arguments (FBT001, FBT002)

- **Avoid positional boolean arguments**
- Use keyword-only arguments with `*` separator

### Exception Handling (BLE001)

- **Never catch bare `Exception`**
- Catch specific exception types

### Test Best Practices

- **Use assertions, not skips, for test setup validation**
- **ALWAYS seed random functions**: All random operations in tests MUST use
  explicit seeds for determinism
- **⚠️ NEVER MASK TEST FAILURES ⚠️**: Do NOT use `assert True` or other
  mechanisms to artificially pass failing tests
- **Break down complex tests**: Extract setup, execution, and verification
  into separate helper functions
- **Bug Reproduction Tests**: When looking for a bug, write tests that
  **FAIL** when the bug is present and **PASS** when the bug is fixed

### Type Annotations

- Use nptyping for numpy array types when applicable:

  ```python
  from nptyping import Int32, Float64, NDArray
  ```

- For dictionaries, always specify key and value types:

  ```python
  indices_map: dict[int, list[int]] = {}
  ```

- **Use dataclasses where appropriate**: For complex data structures,
  especially in test code, prefer dataclasses over manually defined classes

## Environment Variables

### Defining Environment Variables

- **All environment variable names should be defined as constants in a
  constants module**
- Use the `ENV_` prefix for environment variable constants
- Always import from constants module instead of hardcoding strings

## Git Practices

- **CRITICAL: NEVER use `--no-verify` flag with git commands**
  - This bypasses all pre-commit hooks and linting checks
  - All linting errors MUST be fixed before committing
  - If pre-commit fails, fix the errors, don't bypass them
- Always fix linting issues before committing code
- Run pre-commit hooks manually with `poetry run pre-commit run` before committing
- Address all linting issues rather than bypassing the checks
- Use the systematic linting error fixing strategy outlined above

## CI/CD Workflow

- Before committing, always run:
  1. Tests: `poetry run pytest tests/`
  2. Linting: `poetry run pre-commit run --all-files`
- Git commits:
  - Use commitizen-style messages: `feat:`, `fix:`, `docs:`, `style:`, etc.
  - **🚫 CRITICAL: NO AI ATTRIBUTIONS IN COMMIT MESSAGES 🚫**
    - **NEVER include Claude attribution, co-author tags, or any
      AI-generated markers**
    - This is a strict company copyright policy requirement
    - All commit messages must appear as human-authored
    - Violating this policy can create legal and intellectual
      property issues
  - Ensure all code follows company copyright guidelines

## End-of-Sprint Protocol

⚠️ **MANDATORY**: At the end of every sprint, **ALWAYS** run
comprehensive linting before checking in code:

```bash
poetry run pre-commit run --all-files
```

This ensures:

- Code quality standards are maintained across sprints
- No linting errors accumulate over time
- Clean git history with properly formatted code
- Consistent code style across all sprint deliverables

**Never commit sprint completion without running full linting first.**

## Project Architecture

This documentation infrastructure project follows these patterns:

### Configuration Management

- Use YAML configuration files for MkDocs and deployment settings
- Template-based configuration generation for consistency across repositories
- Environment-specific configuration profiles (development, staging, production)

### Repository Integration

- Multi-repository documentation aggregation using mkdocs-multirepo-plugin
- Automated synchronization from source repositories
- Git submodules or API-based content fetching strategies

### Deployment and CI/CD

- GitHub Actions workflows for automated builds and deployments
- Kubernetes deployment with DevSpace for development workflow ✅ IMPLEMENTED
- Docker containerization for consistent environments
- Integration with OAuth2-Proxy for authentication

### Key Components

- `mkdocs.yml`: Main MkDocs configuration
- `templates/`: Reusable configuration templates
- `scripts/`: Automation scripts for repository enrollment and management
- `kubernetes/`: Kubernetes manifests and Helm charts
- `.github/workflows/`: CI/CD pipeline definitions

## Documentation Standards

- Follow Material for MkDocs conventions
- Use Markdown with extensions for enhanced formatting
- Include mathematical notation support via KaTeX
- Support for diagrams using Mermaid and PlantUML
- Maintain consistent navigation structure across all documentation
