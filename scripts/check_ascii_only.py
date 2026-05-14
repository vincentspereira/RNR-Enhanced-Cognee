#!/usr/bin/env python3
"""
check_ascii_only.py - Pre-commit hook to block Unicode in MCP tool output strings.

Scans staged Python files for Unicode characters in:
- Return statements containing strings
- logger.info / logger.warning / logger.error calls
- print() calls

EXIT 0 = clean (no violations)
EXIT 1 = violations found (blocks commit)

Usage:
    python scripts/check_ascii_only.py [file1.py file2.py ...]
    python scripts/check_ascii_only.py  # reads from stdin (pre-commit mode)
"""

import sys
import re

# Unicode symbols commonly misused in output strings
UNICODE_PATTERN = re.compile(
    r'[✓✗✔❌⚠✖✔™'
    r'ℹ✨→←↑↓'
    r'\U0001F4CA\U0001F4C8\U0001F527\U0001F3AF\U0001F680'
    r'\U0001F4A1✅❎☑☒]',
    re.UNICODE
)

# Matches output-producing lines: return "...", logger.xxx(...), print(...)
OUTPUT_STATEMENT_PATTERN = re.compile(
    r'^\s*(return\s+f?["\']|logger\.(info|warning|error|debug)\s*\(|print\s*\()',
    re.MULTILINE
)


def check_file(filepath: str) -> list:
    """Return list of violation messages for the given file."""
    violations = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except Exception as exc:
        return ["WARN Could not read {0}: {1}".format(filepath, exc)]

    for lineno, line in enumerate(lines, 1):
        # Skip pure comment lines and docstring-only lines
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        # Check if this is an output-producing line
        if OUTPUT_STATEMENT_PATTERN.match(line):
            match = UNICODE_PATTERN.search(line)
            if match:
                char = match.group(0)
                violations.append(
                    "ERR {0}:{1}: Unicode character U+{2:04X} "
                    "in output statement (use ASCII equivalents: OK/ERR/WARN/INFO)".format(
                        filepath, lineno, ord(char)
                    )
                )

    return violations


def main():
    files = sys.argv[1:]
    if not files:
        # Pre-commit passes files via stdin when no args
        files = [line.strip() for line in sys.stdin if line.strip().endswith(".py")]

    if not files:
        print("check_ascii_only: no Python files to check")
        sys.exit(0)

    all_violations = []
    for filepath in files:
        all_violations.extend(check_file(filepath))

    if all_violations:
        print("check_ascii_only: {0} violation(s) found:".format(len(all_violations)))
        for v in all_violations:
            print("  {0}".format(v))
        print("Fix: replace Unicode symbols with ASCII equivalents (OK, ERR, WARN, INFO)")
        sys.exit(1)
    else:
        print("check_ascii_only: {0} file(s) checked - OK".format(len(files)))
        sys.exit(0)


if __name__ == "__main__":
    main()
