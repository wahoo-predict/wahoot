#!/bin/bash
# Auto-setup script - runs automatically or can be run manually
# This installs pre-commit hooks so formatting runs automatically

set -e

echo "🔧 Setting up WaHoo development environment..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
fi

# Install pre-commit hooks
echo "🔗 Installing pre-commit hooks..."
pre-commit install

echo "✅ Setup complete! Pre-commit hooks are now active."
echo ""
echo "Hooks will run automatically on every commit."
echo "To test: pre-commit run --all-files"

