#!/bin/bash
#
# Git pre-commit hook to format Python files
# Install: cp Utils/pre_commit_hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
#

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Get list of staged Python files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep "\.py$")

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

echo "Running WaHoo formatter on staged files..."

# Run formatter on staged files
python3 "$PROJECT_ROOT/Utils/format.py" $STAGED_FILES

if [ $? -ne 0 ]; then
    echo "❌ Formatting failed. Please fix the issues and try again."
    echo "   You can run: python3 Utils/format.py <file> to auto-fix most issues."
    exit 1
fi

# Re-stage formatted files
git add $STAGED_FILES

echo "✓ Formatting complete"
exit 0

