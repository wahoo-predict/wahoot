#!/usr/bin/env python3
"""
WaHoo Code Formatter

Formats Python files according to project style guidelines:
- snake_case for variables, parameters, and database fields
- CamelCase for class names
- Target <=500 LOC per file
- Black for auto-formatting (PEP8/flake8 compliant)

Usage:
    python3 Utils/format.py <file_or_directory>
    python3 Utils/format.py --check  # Check only, don't modify
    python3 Utils/format.py --all    # Format all Python files in project
"""

import argparse
import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


# Maximum lines of code per file
MAX_LOC = 500

# Directories to skip
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}

# File patterns to skip
SKIP_PATTERNS = {".pyc", ".pyo", ".pyd"}


def get_python_files(path: Path) -> List[Path]:
    """Recursively get all Python files from a path."""
    python_files = []
    
    if path.is_file() and path.suffix == ".py":
        return [path]
    elif path.is_dir():
        for root, dirs, files in os.walk(path):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            
            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    python_files.append(file_path)
    
    return python_files


def count_lines(file_path: Path) -> int:
    """Count non-empty, non-comment lines in a Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        loc = 0
        for line in lines:
            stripped = line.strip()
            # Count non-empty lines that aren't just comments
            if stripped and not stripped.startswith("#"):
                loc += 1
        
        return loc
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
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
                # Check if class name starts with uppercase and follows CamelCase
                if not class_name[0].isupper():
                    issues.append(f"Class '{class_name}' should start with uppercase (CamelCase)")
                elif "_" in class_name:
                    issues.append(f"Class '{class_name}' should use CamelCase, not snake_case")
    
    except SyntaxError as e:
        issues.append(f"Syntax error: {e}")
    except Exception as e:
        issues.append(f"Error parsing file: {e}")
    
    return issues


def format_with_black(file_path: Path, check_only: bool = False) -> Tuple[bool, str]:
    """
    Format a file using black.
    
    Returns:
        (success, message) tuple
    """
    try:
        cmd = ["black", "--line-length", "88", str(file_path)]
        if check_only:
            cmd.append("--check")
            cmd.append("--diff")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            if check_only:
                return True, "File is already formatted"
            return True, "File formatted successfully"
        else:
            if check_only:
                return False, result.stdout + result.stderr
            # Try to format anyway
            result = subprocess.run(
                ["black", "--line-length", "88", str(file_path)],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return True, "File formatted successfully"
            return False, result.stderr or "Unknown error"
    
    except FileNotFoundError:
        return False, "black not found. Install with: pip install black"
    except Exception as e:
        return False, f"Error running black: {e}"


def format_file(file_path: Path, check_only: bool = False, verbose: bool = True) -> bool:
    """
    Format a single Python file and check style guidelines.
    
    Returns:
        True if file passes all checks, False otherwise
    """
    if verbose:
        print(f"\n{'Checking' if check_only else 'Formatting'}: {file_path}")
    
    all_passed = True
    
    # Check file length
    loc = count_lines(file_path)
    if loc > MAX_LOC:
        print(f"  ⚠️  WARNING: File has {loc} lines (max: {MAX_LOC})")
        all_passed = False
    elif verbose:
        print(f"  ✓ Lines of code: {loc}/{MAX_LOC}")
    
    # Check class naming
    class_issues = check_class_naming(file_path)
    if class_issues:
        for issue in class_issues:
            print(f"  ⚠️  {issue}")
        all_passed = False
    elif verbose:
        print(f"  ✓ Class naming: OK")
    
    # Format with black
    success, message = format_with_black(file_path, check_only=check_only)
    if not success:
        print(f"  ❌ Black formatting: {message}")
        all_passed = False
    elif verbose:
        if check_only and "already formatted" in message:
            print(f"  ✓ Black formatting: OK")
        else:
            print(f"  ✓ Black formatting: {message}")
    
    return all_passed


def main():
    """Main entry point for the formatter."""
    parser = argparse.ArgumentParser(
        description="Format Python files according to WaHoo style guidelines"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=[],
        help="Files or directories to format (default: current directory)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check formatting without modifying files"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Format all Python files in the project"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Show detailed output (default: True)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output"
    )
    
    args = parser.parse_args()
    
    if args.quiet:
        args.verbose = False
    
    # Determine which files to format
    files_to_format = []
    
    if args.all:
        # Format all Python files in the project
        project_root = Path(__file__).parent.parent
        files_to_format = get_python_files(project_root)
    elif args.paths:
        # Format specified paths
        for path_str in args.paths:
            path = Path(path_str)
            if not path.exists():
                print(f"Error: Path does not exist: {path}", file=sys.stderr)
                sys.exit(1)
            files_to_format.extend(get_python_files(path))
    else:
        # Default: format current directory
        files_to_format = get_python_files(Path.cwd())
    
    if not files_to_format:
        print("No Python files found to format.")
        sys.exit(0)
    
    # Remove duplicates and sort
    files_to_format = sorted(set(files_to_format))
    
    if args.verbose:
        mode = "checking" if args.check else "formatting"
        print(f"{mode.capitalize()} {len(files_to_format)} file(s)...")
    
    # Format each file
    passed = 0
    failed = 0
    
    for file_path in files_to_format:
        if format_file(file_path, check_only=args.check, verbose=args.verbose):
            passed += 1
        else:
            failed += 1
    
    # Summary
    if args.verbose or failed > 0:
        print(f"\n{'='*60}")
        print(f"Summary: {passed} passed, {failed} failed")
        print(f"{'='*60}")
    
    if args.check and failed > 0:
        print("\nRun without --check to auto-fix formatting issues.")
        sys.exit(1)
    elif failed > 0:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()

