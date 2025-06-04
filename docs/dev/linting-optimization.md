# Linting Optimization Guide

This guide explains how to optimize your development workflow by managing
MkDocs validation time during pre-commit hooks.

## The Problem

MkDocs validation with `--strict` mode can take 30+ seconds on large
documentation sets, significantly slowing down the commit process. This is
especially frustrating when making small code changes that don't affect
documentation.

## Available Solutions

### 1. Fast Pre-commit Mode (Recommended for Development)

The fastest option for day-to-day development:

```bash
# Switch to fast mode (no MkDocs validation)
make pre-commit-fast

# Run your commits as normal
git add .
git commit -m "feat: implement new feature"

# Manually validate docs before pushing
make docs-validate
```

**Pros:**

- Pre-commit runs in < 5 seconds
- No delay during frequent commits
- Still catches Python/YAML/Markdown issues

**Cons:**

- Must remember to validate docs before pushing
- Could miss documentation build errors

### 2. Incremental Validation Mode (Balanced Approach)

Uses smart detection to only run MkDocs when documentation files change:

```bash
# Switch to optimized mode
make pre-commit-opt

# Commits run fast when only Python files change
git add src/module.py
git commit -m "fix: resolve issue"  # Fast - skips MkDocs

# Commits validate when docs change
git add docs/guide.md
git commit -m "docs: update guide"  # Runs MkDocs validation
```

**Pros:**

- Automatic detection of when validation is needed
- Fast for code-only changes
- Still validates when it matters

**Cons:**

- Adds small overhead for detection logic
- Might miss edge cases

### 3. Full Validation Mode (For Final Commits)

The original configuration with complete validation:

```bash
# Switch back to full mode
make pre-commit-full

# All commits run full validation
git commit -m "chore: prepare release"
```

**Use when:**

- Making final commits before pushing
- Preparing releases
- Working primarily on documentation

## Recommended Workflow

### For Feature Development

1. Start with fast mode:

   ```bash
   make pre-commit-fast
   ```

2. Make frequent commits during development

3. Before pushing, validate documentation:

   ```bash
   make docs-validate
   make pre-commit-full  # Switch back for safety
   git push
   ```

### For Documentation Work

Use incremental mode for the best balance:

```bash
make pre-commit-opt
```

### For CI/CD and Releases

Always use full validation:

```bash
make pre-commit-full
```

## Quick Commands Reference

| Command | Time | Use Case |
|---------|------|----------|
| `make lint-fast` | ~5s | Quick check during development |
| `make lint-python` | ~3s | Python-only validation |
| `make docs-validate` | ~30s | Manual MkDocs check |
| `make lint` | ~35s | Full validation before push |

## Environment Variables

You can also control validation through environment variables:

```bash
# Skip MkDocs in current session
export SKIP_MKDOCS_VALIDATION=1
git commit -m "feat: quick fix"

# Re-enable for important commits
unset SKIP_MKDOCS_VALIDATION
```

## CI/CD Considerations

The GitHub Actions workflow always runs full validation regardless of local
settings. This ensures documentation integrity even if developers use fast mode
locally.

## Tips

1. **Use Aliases**: Add to your shell profile:

   ```bash
   alias gcf='make pre-commit-fast && git commit'
   alias gcp='make docs-validate && git push'
   ```

2. **Git Hooks**: Create a pre-push hook to ensure validation:

   ```bash
   #!/bin/bash
   # .git/hooks/pre-push
   make docs-validate
   ```

3. **VS Code Integration**: Add tasks to `.vscode/tasks.json`:

   ```json
   {
     "label": "Fast Lint",
     "type": "shell",
     "command": "make lint-fast",
     "problemMatcher": []
   }
   ```

## Summary

- **Development**: Use `make pre-commit-fast` for speed
- **Before Push**: Run `make docs-validate`
- **Documentation Work**: Use `make pre-commit-opt`
- **Releases**: Use `make pre-commit-full`

This approach balances development speed with documentation quality assurance.
