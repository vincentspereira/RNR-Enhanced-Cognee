#!/usr/bin/env python3
"""
CI gate: fail if any production source file contains non-ASCII characters
that would cause UnicodeEncodeError on Windows cp1252 consoles.

Excludes:
  - Tests (tests/)
  - Documentation (docs/, *.md, *.rst)
  - Archives (.archive/)
  - Notebooks (*.ipynb, notebooks/)
  - Fixtures and data files (*.json, *.csv, *.txt unless they're source)
  - Comments and docstrings within triple-quotes

Usage:
    python scripts/check_ascii_output.py [path ...]
    python scripts/check_ascii_output.py cognee/ src/ bin/

Exit codes:
    0 - all clear
    1 - violations found (prints each file + line + character)
"""

import sys
import os
import re
from pathlib import Path

# Directories to skip entirely
SKIP_DIRS = {
    "tests", ".archive", "notebooks", "docs", "evals",
    "__pycache__", ".venv", "venv", "env", "node_modules",
    "dist", "build", ".git", "graphify-out", "migrations",
    "cognee-frontend",
}

# File extensions to check
CHECK_EXTENSIONS = {".py", ".sh"}

# Patterns that look like Unicode output symbols in Python string literals or print calls
# We look for these outside of comments and docstrings
UNICODE_PATTERNS = [
    # Common Unicode symbols used in output
    r"[✓✔✗✖❌]",  # check marks, crosses
    r"[☀-⛿]",  # misc symbols (includes warning sign)
    r"[✀-➿]",  # dingbats
    r"[\U0001f300-\U0001f9ff]",  # emoji range
    r"[←-⇿]",  # arrows
    r"[ℹ]",  # info symbol
    r"[✨]",  # sparkles
]

COMBINED_PATTERN = re.compile("|".join(UNICODE_PATTERNS))


def is_in_docstring_or_comment(line: str, char_pos: int) -> bool:
    """Rough heuristic: skip violations in comment lines or after #."""
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return True
    # Check if char is after a # comment marker
    hash_pos = line.find("#")
    if hash_pos != -1 and char_pos > hash_pos:
        return True
    return False


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_number, line_content, offending_char) tuples."""
    violations = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return violations

    # Remove triple-quoted strings from analysis
    # Replace them with blank lines of the same length to preserve line numbers
    in_triple = False
    triple_char = ""
    cleaned_lines = []
    for line in content.splitlines(keepends=True):
        if not in_triple:
            # Check if triple quote starts
            for tq in ('"""', "'''"):
                if tq in line:
                    idx = line.find(tq)
                    after = line[idx + 3:]
                    if tq in after:
                        # Triple quote opens and closes on same line
                        line = line[:idx] + " " * (len(line) - idx)
                    else:
                        in_triple = True
                        triple_char = tq
                        line = line[:idx] + " " * (len(line) - idx)
                    break
        else:
            if triple_char in line:
                idx = line.find(triple_char)
                line = " " * (idx + 3) + line[idx + 3:]
                in_triple = False
            else:
                line = " " * len(line)
        cleaned_lines.append(line)

    for lineno, line in enumerate(cleaned_lines, start=1):
        match = COMBINED_PATTERN.search(line)
        if match:
            char = match.group()
            char_pos = match.start()
            if not is_in_docstring_or_comment(line, char_pos):
                violations.append((lineno, line.rstrip(), char))
    return violations


def check_path(target: Path) -> dict[Path, list]:
    """Recursively check all Python/shell files under target."""
    results = {}
    if target.is_file():
        if target.suffix in CHECK_EXTENSIONS:
            v = check_file(target)
            if v:
                results[target] = v
    elif target.is_dir():
        for root, dirs, files in os.walk(target):
            # Skip excluded directories
            dirs[:] = [
                d for d in dirs
                if d not in SKIP_DIRS and not d.startswith(".")
            ]
            for fname in files:
                fpath = Path(root) / fname
                if fpath.suffix in CHECK_EXTENSIONS:
                    v = check_file(fpath)
                    if v:
                        results[fpath] = v
    return results


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["."]
    all_violations = {}
    for t in targets:
        p = Path(t)
        if not p.exists():
            print(f"WARN: path does not exist: {p}", file=sys.stderr)
            continue
        all_violations.update(check_path(p))

    if not all_violations:
        print("OK ASCII check passed: no Unicode output symbols found in production code.")
        sys.exit(0)

    print(f"ERR ASCII check FAILED: found Unicode output symbols in {len(all_violations)} file(s).")
    print("Fix: replace Unicode with ASCII equivalents (OK/WARN/ERR/[DOC]/[MEM] etc.)")
    print()
    for filepath, violations in sorted(all_violations.items()):
        for lineno, line, char in violations:
            codepoint = ord(char)
            # Print the codepoint only (not the char itself) to avoid Windows cp1252 errors
            safe_line = line.encode("ascii", errors="replace").decode("ascii")
            print(f"  {filepath}:{lineno}: U+{codepoint:04X} (character replaced with ? below)")
            print(f"    {safe_line[:120]}")
    sys.exit(1)


if __name__ == "__main__":
    main()
