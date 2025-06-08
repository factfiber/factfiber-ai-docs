# pdoc Documentation Standards

## Overview

FactFiber uses Google-style docstrings as our standard for API documentation.
This document outlines the requirements and best practices for generating API
documentation with pdoc.

## Critical Requirements

### ⚠️ ALWAYS Use Enhanced Configuration

**CRITICAL**: All pdoc commands MUST include our enhanced flag set for complete,
properly formatted documentation.

**Required Flags:**

- `--docformat google` - Parse Google-style docstrings correctly
- `--math` - Enable mathematical notation rendering
- `--mermaid` - Enable Mermaid diagram support
- `--include-undocumented` - Ensure complete API coverage

```bash
# ✅ CORRECT - Enhanced configuration (recommended)
poetry run docs-code

# ✅ CORRECT - Full command with all flags
poetry run pdoc --docformat google --math --mermaid --include-undocumented --html --output-dir docs/reference/code src/package

# ❌ WRONG - Missing critical flags
poetry run pdoc --html --output-dir docs/reference/code src/package
```

## Standard Commands

### Generate API Documentation (Recommended)

```bash
poetry run docs-code
```

### Generate API Documentation (Direct Command)

```bash
poetry run pdoc --docformat google --math --mermaid --include-undocumented --html --output-dir docs/reference/code src/ff_docs
```

### Serve Documentation Locally

```bash
poetry run pdoc --docformat google --math --mermaid --http localhost:8080 src/ff_docs
```

### Benefits of Enhanced Configuration

1. **`--docformat google`**: Proper Google-style docstring parsing
2. **`--math`**: Renders LaTeX mathematical expressions
3. **`--mermaid`**: Supports Mermaid diagrams in docstrings
4. **`--include-undocumented`**: Documents all modules, even those without docstrings (helps identify missing documentation)

## Integration

### Pre-commit Integration

Our pre-commit hooks automatically include the `--docformat google` flag when generating documentation.

### Automated Pipeline

The `PdocGenerator` class in `src/ff_docs/pipeline/pdoc_integration.py`
automatically includes the Google docformat flag in all generated documentation.

### Repository Configuration

When setting up new repositories, ensure your `.factfiber-docs.yml` includes:

```yaml
pdoc:
  enabled: true
  docformat: google  # This ensures the pipeline uses Google format
  packages:
    - src/your_package
```

## Docstring Format

We use Google-style docstrings. Here's the standard format:

```python
def example_function(param1: str, param2: int) -> bool:
    """
    Brief description of the function.

    Longer description if needed. This can span multiple lines and
    provide detailed information about the function's behavior.

    Args:
        param1: Description of the first parameter.
        param2: Description of the second parameter.

    Returns:
        Description of the return value.

    Raises:
        ValueError: Description of when this exception is raised.
        TypeError: Description of when this exception is raised.

    Example:
        Basic usage example:

        >>> result = example_function("hello", 42)
        >>> print(result)
        True
    """
    return len(param1) > param2
```

## Quality Standards

### Required Documentation

- All public functions, classes, and methods must have docstrings
- All parameters and return values must be documented
- All exceptions must be documented

### Documentation Quality

- Use clear, concise language
- Provide examples for complex functions
- Include type information in docstrings (complementing type hints)
- Document any side effects or important behavioral notes

## Troubleshooting

### Common Issues

1. **Missing `--docformat google` flag**
   - **Symptom**: Docstrings not parsed correctly, arguments not recognized
   - **Solution**: Always include `--docformat google` in pdoc commands

2. **Docstring format not recognized**
   - **Symptom**: Documentation appears as plain text
   - **Solution**: Verify Google docstring format, check indentation

3. **Missing documentation**
   - **Symptom**: Functions appear without documentation
   - **Solution**: Ensure all public functions have proper docstrings

## Integration with ingolstadt

When using ingolstadt for documentation generation, ensure your configuration includes:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pdoc-generation
        name: Generate API documentation
        entry: poetry run pdoc --docformat google --html --output-dir docs/reference/code
        language: system
        files: ^src/.*\.py$
```

This ensures that the ingolstadt team's tools will generate documentation using our Google docstring standard.

## References

- [Google Style Python Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [pdoc Documentation](https://pdoc.dev/)
- [FactFiber Documentation Standards](documentation_standards.md)
