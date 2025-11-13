#!/usr/bin/env python3
"""
Lightweight format checker for pre-commit hook.

Checks:
- File length (≤500 LOC)
- Class naming (CamelCase)

This is a minimal version that works with pre-commit framework.
For full formatting, use: python3 Utils/format.py
"""

import ast
import sys
from pathlib import Path
from typing import List


MAX_LOC = 500


def count_lines(file_path: Path) -> int:
    """Count non-empty, non-comment lines."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        loc = 0
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                loc += 1

        return loc
    except Exception:
        return 0


def check_class_naming(file_path: Path) -> List[str]:
    """Check that class names use CamelCase."""
    issues = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                if not class_name[0].isupper():
                    issues.append(
                        f"{file_path}:{node.lineno}: Class '{class_name}' should start with uppercase (CamelCase)"
                    )
                elif "_" in class_name:
                    issues.append(
                        f"{file_path}:{node.lineno}: Class '{class_name}' should use CamelCase, not snake_case"
                    )

    except SyntaxError as e:
        issues.append(f"{file_path}:{e.lineno}: Syntax error: {e.msg}")
    except Exception as e:
        issues.append(f"{file_path}: Error parsing file: {e}")

    return issues


def main():
    """Check files passed from pre-commit."""
    if len(sys.argv) < 2:
        return 0

    all_issues = []

    for file_path_str in sys.argv[1:]:
        file_path = Path(file_path_str)

        if not file_path.exists() or file_path.suffix != ".py":
            continue

        # Check file length
        loc = count_lines(file_path)
        if loc > MAX_LOC:
            all_issues.append(f"{file_path}:1: File has {loc} lines (max: {MAX_LOC})")

        # Check class naming
        class_issues = check_class_naming(file_path)
        all_issues.extend(class_issues)

    if all_issues:
        print("\n".join(all_issues))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
