# Getting Started

Welcome to FactFiber.ai development! This guide will help you get started
with contributing to our projects.

## Prerequisites

- **Python 3.13+** - Required for all FactFiber.ai projects
- **Poetry** - For dependency management and virtual environments
- **Git** - For version control
- **Docker** (optional) - For containerized development

## Development Environment Setup

### 1. Clone the Repository

Choose the project you want to work on:

```bash
# For the documentation system
git clone https://github.com/factfiber/factfiber-ai-docs.git
cd factfiber-ai-docs

# For other projects
git clone https://github.com/factfiber/[project-name].git
cd [project-name]
```

### 2. Install Dependencies

```bash
# Install all dependencies including development tools
poetry install

# Install pre-commit hooks (REQUIRED)
poetry run pre-commit install
```

### 3. Verify Installation

```bash
# Run tests
poetry run pytest

# Run linting
poetry run pre-commit run --all-files

# Start development server (for documentation projects)
poetry run mkdocs serve
```

## Development Workflow

1. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the coding standards in `CLAUDE.md`
   - Write tests for new functionality
   - Update documentation as needed

3. **Test your changes**

   ```bash
   poetry run pytest
   poetry run pre-commit run --all-files
   ```

4. **Commit and push**

   ```bash
   git add .
   git commit -m "feat: your feature description"
   git push origin feature/your-feature-name
   ```

5. **Create a pull request**
   - Use the GitHub web interface
   - Fill out the PR template
   - Wait for review and approval

## Project Structure

Each FactFiber.ai project follows a consistent structure:

```text
project-name/
├── src/project_name/     # Main package code
├── tests/                # Test files
├── docs/                 # Documentation
├── scripts/              # Automation scripts
├── pyproject.toml        # Project configuration
├── CLAUDE.md            # Development guidelines
└── README.md            # Project overview
```

## Coding Standards

- **Line Length**: 80 characters maximum
- **Type Annotations**: Required on all functions
- **Docstrings**: Google style format
- **Testing**: Comprehensive test coverage required
- **Linting**: Must pass all pre-commit checks

## Getting Help

- **Documentation**: Check project-specific documentation
- **Issues**: Use GitHub issues for bug reports and feature requests
- **Code Review**: All code must be reviewed before merging
- **Questions**: Ask in pull request comments or issues

## Next Steps

- [Contributing Guidelines](contributing.md)
- [Architecture Overview](architecture.md)
- [API Reference](../api/)

---

## Happy coding! 🚀
