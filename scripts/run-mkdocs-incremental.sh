#!/bin/bash
# Wrapper script for mkdocs-incremental that ensures tmp directory exists

# Create tmp directory if it doesn't exist
mkdir -p tmp

# Run mkdocs-incremental with all passed arguments
exec poetry run mkdocs-incremental "$@"
