# Contributing Guidelines

Thank you for your interest in contributing to FactFiber.ai! This document
outlines our contribution process and standards.

## Code of Conduct

We are committed to fostering a welcoming and inclusive environment. All
contributors must adhere to our code of conduct.

## How to Contribute

### 1. Issues and Bug Reports

- **Search existing issues** before creating a new one
- **Use issue templates** when available
- **Provide detailed information** including steps to reproduce
- **Tag appropriately** (bug, enhancement, documentation, etc.)

### 2. Feature Requests

- **Discuss major changes** in an issue before implementing
- **Provide use cases** and rationale for the feature
- **Consider backwards compatibility** and breaking changes

### 3. Pull Requests

#### Before You Start

- Fork the repository
- Create a feature branch from `main`
- Set up your development environment following [Getting Started](getting-started.md)

#### Development Process

- Follow the coding standards in `CLAUDE.md`
- Write comprehensive tests for new functionality
- Update documentation as needed
- Ensure all pre-commit checks pass

#### Pull Request Guidelines

- **Use descriptive titles** following conventional commit format
- **Fill out the PR template** completely
- **Keep PRs focused** - one feature or fix per PR
- **Include tests** that verify your changes work correctly
- **Update documentation** for user-facing changes

## Code Standards

### Code Quality

- **100% test coverage** for new code
- **Type annotations** on all function signatures
- **Docstrings** for all public functions and classes
- **Linting compliance** - all pre-commit checks must pass

### Documentation

- **Update relevant documentation** for any changes
- **Include code examples** in docstrings where helpful
- **Follow Google docstring style**

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat: add new repository aggregation feature
fix: resolve memory leak in context graph processing
docs: update installation instructions
style: fix linting issues in authentication module
refactor: simplify configuration management
test: add integration tests for API endpoints
```

## Review Process

### Code Review

- **All code must be reviewed** before merging
- **Address all feedback** before requesting re-review
- **Reviewers focus on**:
  - Code correctness and performance
  - Test coverage and quality
  - Documentation completeness
  - Adherence to project standards

### Approval Requirements

- **One approval required** from a project maintainer
- **All CI checks must pass**
- **No conflicts** with target branch

## Testing Guidelines

### Test Coverage

- **Write tests first** when possible (TDD approach)
- **Cover edge cases** and error conditions
- **Include integration tests** for complex features
- **Performance tests** for critical paths

### Test Organization

```text
tests/
├── unit/           # Fast, isolated unit tests
├── integration/    # Integration tests
├── fixtures/       # Shared test data and utilities
└── conftest.py     # Pytest configuration
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src

# Run specific test file
poetry run pytest tests/unit/test_example.py -v
```

## Documentation Standards

### Documentation Types

- **README files** - Project overview and quick start
- **API documentation** - Generated from docstrings
- **User guides** - Step-by-step instructions
- **Architecture docs** - System design and decisions

### Writing Guidelines

- **Use clear, concise language**
- **Include practical examples**
- **Keep content up-to-date**
- **Link between related sections**

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** - Breaking changes
- **MINOR** - New features (backwards compatible)
- **PATCH** - Bug fixes (backwards compatible)

### Release Workflow

1. Update version numbers
2. Update CHANGELOG.md
3. Create release PR
4. Tag release after merge
5. Deploy to production

## Getting Help

### Resources

- **[Getting Started](getting-started.md)** - Development setup
- **[Architecture](architecture.md)** - System design
- **GitHub Issues** - Questions and discussions

### Communication

- **GitHub Issues** - Technical questions and bug reports
- **Pull Request Comments** - Code-specific discussions
- **Project Discussions** - General questions and ideas

Thank you for contributing to FactFiber.ai! 🎉
