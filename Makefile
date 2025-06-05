# FactFiber Documentation Infrastructure Makefile
# Provides convenient commands for development and validation

.PHONY: help lint lint-fast lint-python docs-validate pre-commit-fast pre-commit-full clean

help:
    @echo "FactFiber Documentation Infrastructure - Development Commands"
    @echo ""
    @echo "Linting & Validation:"
    @echo "  make lint          - Run pre-commit validation (smart incremental MkDocs)"
    @echo "  make lint-fast     - Run fast pre-commit (no MkDocs validation)"
    @echo "  make lint-full     - Run full pre-commit (always validate MkDocs)"
    @echo "  make lint-python   - Run only Python linting (ruff, mypy)"
    @echo "  make docs-validate - Run only MkDocs validation"
    @echo ""
    @echo "Pre-commit Management:"
    @echo "  make pre-commit-fast - Switch to fast pre-commit config"
    @echo "  make pre-commit-full - Switch to full pre-commit config"
    @echo "  make pre-commit-opt  - Switch to optimized incremental config (default)"
    @echo ""
    @echo "Development:"
    @echo "  make docs-serve  - Start MkDocs development server"
    @echo "  make docs-build  - Build documentation"
    @echo "  make api-serve   - Start FastAPI development server"
    @echo "  make clean       - Clean generated files"
    @echo ""
    @echo "Testing:"
    @echo "  make test        - Run all tests"
    @echo "  make test-unit   - Run unit tests only"

# Linting with smart incremental MkDocs validation (default)
lint:
    poetry run pre-commit run --all-files

# Fast linting without MkDocs validation
lint-fast:
    @echo "🚀 Running fast linting (no MkDocs validation)..."
    @cp .pre-commit-config-fast.yaml .pre-commit-config.yaml.tmp
    @mv .pre-commit-config.yaml .pre-commit-config.yaml.bak
    @mv .pre-commit-config.yaml.tmp .pre-commit-config.yaml
    @poetry run pre-commit run --all-files || true
    @mv .pre-commit-config.yaml.bak .pre-commit-config.yaml
    @echo "✅ Fast linting complete"

# Full linting with MkDocs validation (always runs MkDocs)
lint-full:
    @echo "🔍 Running full linting (always validate MkDocs)..."
    @cp .pre-commit-config-full.yaml .pre-commit-config.yaml.tmp
    @mv .pre-commit-config.yaml .pre-commit-config.yaml.bak
    @mv .pre-commit-config.yaml.tmp .pre-commit-config.yaml
    @poetry run pre-commit run --all-files || true
    @mv .pre-commit-config.yaml.bak .pre-commit-config.yaml
    @echo "✅ Full linting complete"

# Python-only linting
lint-python:
    @echo "🐍 Running Python linting..."
    poetry run ruff check src/ tests/
    poetry run ruff format --check src/ tests/
    poetry run mypy src/

# MkDocs validation only
docs-validate:
    @echo "📚 Validating MkDocs..."
    poetry run mkdocs build --strict --quiet
    @echo "✅ MkDocs validation passed"

# Switch to fast pre-commit configuration
pre-commit-fast:
    @echo "⚡ Switching to fast pre-commit configuration..."
    @cp .pre-commit-config-fast.yaml .pre-commit-config.yaml
    @echo "✅ Now using fast pre-commit (no MkDocs validation)"
    @echo "⚠️  Remember to run 'make docs-validate' before pushing!"

# Switch to full pre-commit configuration
pre-commit-full:
    @echo "🔧 Switching to full pre-commit configuration..."
    @cp .pre-commit-config-full.yaml .pre-commit-config.yaml
    @echo "✅ Now using full pre-commit (always validates MkDocs)"

# Switch to optimized incremental configuration (default)
pre-commit-opt:
    @echo "🎯 Switching to optimized incremental pre-commit configuration..."
    @cp .pre-commit-config-optimized.yaml .pre-commit-config.yaml
    @echo "✅ Now using optimized pre-commit (incremental MkDocs validation - default)"

# Documentation development
docs-serve:
    poetry run mkdocs serve --dev-addr 0.0.0.0:8000

docs-build:
    poetry run mkdocs build

# API development
api-serve:
    poetry run ff-docs serve-api --reload --host 0.0.0.0 --port 8080

# Testing
test:
    poetry run pytest tests/ -v

test-unit:
    poetry run pytest tests/unit/ -v

# Clean generated files
clean:
    @echo "🧹 Cleaning generated files..."
    @rm -rf site/ htmlcov/ .coverage coverage.xml
    @rm -rf docs/reference/code/*
    @find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    @find . -type f -name "*.pyc" -delete
    @echo "✅ Clean complete"

# Install git hooks
install-hooks:
    poetry run pre-commit install
    @echo "✅ Pre-commit hooks installed"
