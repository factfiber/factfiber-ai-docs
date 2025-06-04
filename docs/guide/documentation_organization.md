# Documentation Organization Standards

This document outlines the recommended documentation organization for FactFiber
repositories, addressing the questions about directory structure, content
placement, and automation.

## Recommended Directory Structure

Based on analysis of existing patterns (particularly timbuktu) and best
practices, here's the standardized structure:

```text
docs/
├── index.md                    # Repository landing page
├── guide/                      # Cross-cutting documentation
│   ├── index.md               # Navigation hub
│   ├── getting-started.md     # Installation and basic usage
│   ├── architecture.md        # System design and decisions
│   ├── development.md         # Development and contribution guide
│   └── documentation_standards.md  # This standards guide
├── reference/                  # Technical reference documentation
│   ├── code/                  # Auto-generated code documentation (pdoc)
│   │   └── (pdoc HTML output)
│   └── components/            # Manual component documentation
│       └── {package_name}/    # Mirrors source code structure
│           ├── index.md      # Package overview
│           ├── core/         # Core module documentation
│           ├── utils/        # Utilities documentation
│           └── algorithms/   # Algorithm-specific docs
└── assets/                    # Images, diagrams, media
    ├── images/
    └── diagrams/
```

## Key Changes from Current Patterns

### 1. **`reference/components/` instead of `src/`**

- **Rationale**: "reference/components" is clearer about purpose (manual
  technical docs)
- **Content**: Component-specific documentation that mirrors source structure
- **Mirrors**: `src/timbuktu/adapt/` →
  `docs/reference/components/timbuktu/adapt/`

### 2. **`reference/code/` instead of `code/` or `api/`**

- **Rationale**: "code" is more accurate than "api" for auto-generated docs
- **Content**: pdoc-generated HTML documentation from source code
- **Auto-generated**: Should not be manually edited
- **Avoids confusion**: "api" suggests REST/HTTP APIs to many developers

### 3. **Root Documentation Strategy**

The repository root (`docs/index.md`) serves as the landing page and should
include:

#### **Essential Content**

- **Project Overview**: 1-2 sentence description of what the project does
- **Purpose Statement**: Why this project exists and who it's for
- **Quick Start Link**: Direct link to `guide/getting-started.md`
- **Key Features**: 3-5 bullet points of main capabilities
- **Navigation Sections**: Clear links to guide/, reference/, and code docs

#### **Recommended Structure**

```markdown
# Project Name

Brief description of what this project does and why it matters.

## Quick Start
- [Getting Started](guide/getting-started.md) - Setup and first steps
- [Architecture Overview](guide/architecture.md) - System design

## Key Features
- Feature 1: Brief description
- Feature 2: Brief description
- Feature 3: Brief description

## Documentation Sections
- **[User Guide](guide/)** - Tutorials and cross-cutting documentation
- **[Technical Reference](reference/)** - Component docs and code reference
- **[Code Documentation](reference/code/)** - Auto-generated API reference

## Contributing
See [Development Guide](guide/development.md) for contribution guidelines.
```

#### **What NOT to Include**

- Long detailed explanations (save for guide/architecture.md)
- Installation instructions (link to getting-started.md instead)
- Code examples (save for guide/ sections)
- Duplicate navigation (MkDocs handles this)

## Documentation Patterns by Repository Type

### Applications vs Libraries

Different types of repositories require different documentation approaches:

#### **Applications** (e.g., timbuktu - Hydra-based ML application)

**Root `index.md` should emphasize**:

- **What the application does** and its main purpose
- **How to run it** (link to getting-started.md)
- **Key workflows** and use cases
- **Configuration options** (especially Hydra configs)

**Example structure**:

```markdown
# Timbuktu Context Graph System

Machine learning application for adaptive context graph processing with
real-time inference capabilities.

## Quick Start
- [Installation & Setup](guide/getting-started.md) - Install and run your
  first model
- [Configuration Guide](guide/configuration.md) - Hydra configs and
  parameters
- [Training Workflow](guide/training.md) - How to train models

## Key Capabilities
- Real-time context graph adaptation
- CUDA-accelerated inference
- Configurable optimization algorithms
- Production deployment ready

## Documentation Sections
- **[User Guide](guide/)** - How to use the application
- **[Technical Reference](reference/)** - System internals and components
- **[Code Documentation](reference/code/)** - API reference for developers
```

**Guide section should include**:

- `getting-started.md` - Installation and first run
- `configuration.md` - Hydra configuration files and options
- `training.md` - How to train models
- `inference.md` - How to run inference
- `deployment.md` - Production deployment
- `troubleshooting.md` - Common issues and solutions

#### **Libraries** (e.g., ingolstadt - Python code library)

**Root `index.md` should emphasize**:

- **What problems the library solves**
- **How to install and import it**
- **Basic usage examples**
- **Key APIs and classes**

**Example structure**:

```markdown
# Ingolstadt Library

Python library for [specific functionality] with high-performance
implementations and clean APIs.

## Installation
```bash
pip install ingolstadt
# or
poetry add ingolstadt
```

## Quick Example

```python
from ingolstadt import CoreProcessor
processor = CoreProcessor()
result = processor.process(data)
```

## Key Features

- High-performance data processing
- Clean, intuitive API
- Extensive type hints
- Comprehensive test coverage

## Documentation Sections

- **[User Guide](guide/)** - Tutorials and usage patterns
- **[Technical Reference](reference/)** - Detailed API documentation
- **[Code Documentation](reference/code/)** - Complete API reference

**Guide section should include**:

- `getting-started.md` - Installation and basic usage
- `tutorials.md` - Step-by-step examples
- `api-overview.md` - Key classes and functions
- `advanced-usage.md` - Complex usage patterns
- `contributing.md` - How to contribute to the library
- `changelog.md` - Version history and breaking changes

### Key Differences Summary

| Aspect | Applications | Libraries |
|--------|-------------|-----------|
| **Primary Users** | End users, operators | Other developers |
| **Root Focus** | How to run and configure | How to install and use |
| **Getting Started** | Installation + first run | Installation + import + example |
| **Configuration** | Extensive config docs | API configuration options |
| **Examples** | Workflows and use cases | Code snippets and tutorials |
| **Deployment** | Production deployment guides | Integration patterns |

## Content Organization Guidelines

### `docs/guide/` - Cross-Cutting Documentation

**Purpose**: Documentation that spans multiple components or provides
high-level guidance.

**Include**:

- **Getting Started**: Installation, setup, basic usage
- **Architecture**: System design, component relationships, decisions
- **Development**: Contribution guide, development setup, testing
- **Tutorials**: Step-by-step workflows
- **Best Practices**: Usage patterns and recommendations

**Example Structure**:

```text
guide/
├── index.md                   # Guide navigation
├── getting-started.md         # Setup and first steps
├── architecture.md            # System design overview
├── development.md             # Development workflow
├── algorithms/                # Algorithm-specific guides
│   ├── context-graphs.md     # High-level algorithm docs
│   └── optimization.md       # Mathematical foundations
└── deployment.md             # Production deployment
```

### `docs/reference/` - Component Documentation

**Purpose**: Detailed technical documentation organized by code structure.

**Include**:

- **Component overviews**: Purpose and scope of each package
- **Implementation details**: Technical specifications
- **Usage examples**: Code examples for each component
- **Configuration**: Component-specific configuration options

**Example Structure** (for timbuktu):

```text
reference/
├── index.md                   # Reference overview
└── timbuktu/
    ├── index.md              # Package overview
    ├── adapt/                # Adaptation system
    │   ├── index.md         # Adaptation overview
    │   ├── context-graph.md # Context graph details
    │   └── algorithms.md    # Adaptation algorithms
    ├── assess/               # Assessment system
    ├── config/               # Configuration system
    ├── cudautil/             # CUDA utilities
    ├── datatypes/            # Data structures
    └── infer/                # Inference system
```

### `docs/api/` - Auto-Generated Documentation

**Purpose**: Comprehensive API reference generated from code docstrings.

**Configuration**:

- Generated by pdoc from source code
- Include mathematical notation support
- Include Mermaid diagram support
- Auto-updated on code changes

**Do Not**:

- Manually edit files in this directory
- Include in version control (add to .gitignore)
- Use for high-level documentation

## Configuration Requirements

### pdoc Configuration in `pyproject.toml`

**Remove obsolete configurations**:

```toml
# REMOVE THIS - obsolete exec configuration
"pdoc" = "poetry run bash -c 'shopt -s globstar; \\
  pdoc -o docs/code --math --mermaid src/**/*.py'"
```

**Use modern configuration**:

```toml
[tool.poetry.scripts]
docs-code = "bash -c 'pdoc -o docs/reference/code --math --mermaid src/**/*.py'"
docs-serve = "mkdocs serve --dev-addr 0.0.0.0:8000"
docs-build = "mkdocs build"

[tool.pdoc]
output_directory = "docs/reference/code"
include_undocumented = true
show_source = true
math = true
mermaid = true
```

### MkDocs Configuration

**Standardized `mkdocs.yml`**:

- Material theme with FactFiber blue branding
- Mathematical notation support (MathJax)
- Mermaid diagram support
- Code highlighting and copy buttons
- Search with enhanced configuration

**Template available**:
[`docs/guide/templates/mkdocs.yml`](templates/mkdocs.yml)

## Automation Strategy

### GitHub Actions per Repository (Recommended)

**Each repository should have**:

- `.github/workflows/docs.yml` for automated documentation builds
- Triggered on code changes and documentation updates
- Generates pdoc documentation automatically
- Deploys to GitHub Pages

**Benefits**:

- Repository-specific control
- Faster builds (only affected repository)
- Independent deployment cycles
- Clear ownership and maintenance

**Template available**:
[`docs/guide/templates/github-workflows-docs.yml`](templates/github-workflows-docs.yml)

### Central Documentation Portal Integration

**The central portal**:

- Imports documentation via git references
- Provides unified search and navigation
- Handles authentication and access control
- Aggregates multiple repositories

**Webhook integration**:

- Repositories notify portal of documentation updates
- Portal automatically pulls latest documentation
- Real-time synchronization across repositories

## Migration Path for Existing Repositories

### For timbuktu (Example)

**Current Structure**:

```text
docs/
├── code/          # pdoc output
├── guide/         # ✅ Keep as-is
└── src/           # → Move to reference/components/
```

**Migration Steps**:

1. `mkdir -p docs/reference/components docs/reference/code`
2. `mv docs/src/* docs/reference/components/`
3. `mv docs/code/* docs/reference/code/`
4. Update `mkdocs.yml` navigation paths
5. Update pdoc output directory in `pyproject.toml` to `docs/reference/code`
6. Update script name from `docs-api` to `docs-code`
7. Update internal links in documentation
8. Test build process

### For New Repositories

**Use Templates**:

1. Copy template files from portal repository
2. Customize for your project
3. Create initial content structure
4. Set up GitHub Actions workflow
5. Register with documentation portal

## Content Guidelines

### Google-Style Docstrings (In Code)

**Required for all public APIs**:

```python
def process_context_graph(graph: ContextGraph,
                         threshold: float = 0.5) -> ProcessingResult:
    """
    Process context graph with adaptive learning.

    This function applies the core context graph processing algorithm,
    including adaptation, assessment, and inference steps.

    Args:
        graph: Input context graph with nodes and edges.
        threshold: Confidence threshold for processing decisions.
            Values should be between 0.0 and 1.0.

    Returns:
        ProcessingResult containing adapted graph and metrics:
            - adapted_graph: Updated context graph
            - confidence_scores: Per-node confidence values
            - processing_time: Execution time in seconds

    Raises:
        ValueError: If threshold is outside valid range [0.0, 1.0].
        ProcessingError: If graph processing fails.

    Example:
        >>> graph = ContextGraph.from_data(training_data)
        >>> result = process_context_graph(graph, threshold=0.8)
        >>> print(f"Processed {len(result.adapted_graph.nodes)} nodes")

    Note:
        This function modifies the input graph in-place for performance.
        Use graph.copy() if you need to preserve the original.
    """
```

### Documentation Content Standards

**Architecture Documentation**:

- Include Mermaid diagrams for system overview
- Explain design decisions and trade-offs
- Document component interactions
- Include performance characteristics

**Development Documentation**:

- Clear setup instructions
- Testing procedures
- Contribution guidelines
- Code style requirements

**Reference Documentation**:

- Purpose and scope of each component
- Usage examples with real code
- Configuration options
- Integration patterns

## Benefits of This Organization

### 1. **Clarity and Discoverability**

- Clear separation between guides, reference, and API docs
- Intuitive navigation structure
- Consistent organization across repositories

### 2. **Maintainability**

- Auto-generated API docs stay synchronized
- Manual documentation has clear ownership
- Standardized tooling and processes

### 3. **Integration**

- Seamless portal integration
- Unified search across repositories
- Consistent user experience

### 4. **Automation**

- Automated builds and deployments
- Real-time synchronization
- Quality checks and validation

## Next Steps

1. **Review this proposal** with the team
2. **Pilot with timbuktu repository** migration
3. **Create migration guides** for other repositories
4. **Train team members** on new documentation workflow
5. **Establish maintenance procedures** for ongoing quality

---

This organization provides a solid foundation for scalable, maintainable
documentation across all FactFiber repositories while maintaining consistency
and quality standards.
