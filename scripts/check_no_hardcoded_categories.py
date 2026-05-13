#!/usr/bin/env python3
"""
CI gate: fail if production code contains hardcoded category names
that violate the CLAUDE.md "no hardcoded categories" rule.

Hardcoded categories are things like "ats", "oma", "smc" used as string
literals, class names, or enum members. Categories must be loaded
dynamically from .enhanced-cognee-config.json or environment variables.

Excludes:
  - Tests (tests/)
  - Documentation (docs/, *.md)
  - Archives (.archive/)
  - Config files (*.json, *.yaml, *.yml, *.env, *.toml)
  - This script itself

Usage:
    python scripts/check_no_hardcoded_categories.py [path ...]
    python scripts/check_no_hardcoded_categories.py src/ bin/ cognee/

Exit codes:
    0 - all clear
    1 - violations found
"""

import sys
import os
import re
from pathlib import Path

SKIP_DIRS = {
    "tests", ".archive", "docs", "evals", "__pycache__",
    ".venv", "venv", "env", "node_modules", "dist", "build",
    ".git", "graphify-out", "migrations", "cognee-frontend",
}

SKIP_FILES = {
    "check_no_hardcoded_categories.py",  # skip this script itself
}

CHECK_EXTENSIONS = {".py", ".sh"}

# Patterns that indicate hardcoded category names
# These patterns look for the category names used as identifiers or string literals
# in ways that suggest they are hardcoded rather than loaded from config.

PATTERNS = [
    # Class names with hardcoded categories
    (r"\bclass\s+(ATS|OMA|SMC|Ats|Oma|Smc)\w*\b", "hardcoded class name"),
    # Enum members
    (r"\b(ATS|OMA|SMC)\s*=\s*[\"\'](ats|oma|smc)[\"\']\b", "hardcoded enum member"),
    # String literals for category routing
    (r'["\'](?:ats|oma|smc)["\'](?:\s*[:=,)]|\s*in\s)', "hardcoded category string literal"),
    # Direct attribute access like MemoryCategory.ATS
    (r"\bMemoryCategory\.(ATS|OMA|SMC)\b", "hardcoded MemoryCategory enum access"),
    # Agent class names
    (r"\b(ATSAgent|OMAAgent|SMCAgent)\b", "hardcoded agent class name"),
    # Directory paths in code (string literals referencing the agent dirs)
    (r'["\']src/agents/(?:ats|oma|smc)["\']', "hardcoded agent directory path"),
    # Import paths
    (r"from\s+src\.agents\.(?:ats|oma|smc)\b", "hardcoded agent module import"),
    (r"import\s+src\.agents\.(?:ats|oma|smc)\b", "hardcoded agent module import"),
]

COMPILED = [(re.compile(p, re.IGNORECASE), desc) for p, desc in PATTERNS]


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_number, line_content, description) tuples."""
    violations = []
    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return violations

    for lineno, line in enumerate(lines, start=1):
        # Skip comment-only lines
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        for pattern, desc in COMPILED:
            if pattern.search(line):
                violations.append((lineno, line.rstrip(), desc))
                break  # one violation per line is enough
    return violations


def check_path(target: Path) -> dict[Path, list]:
    results = {}
    if target.is_file():
        if target.suffix in CHECK_EXTENSIONS and target.name not in SKIP_FILES:
            v = check_file(target)
            if v:
                results[target] = v
    elif target.is_dir():
        for root, dirs, files in os.walk(target):
            dirs[:] = [
                d for d in dirs
                if d not in SKIP_DIRS and not d.startswith(".")
            ]
            for fname in files:
                if fname in SKIP_FILES:
                    continue
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
        print("OK Categories check passed: no hardcoded category names found in production code.")
        sys.exit(0)

    print(f"ERR Categories check FAILED: found hardcoded categories in {len(all_violations)} file(s).")
    print("Fix: load categories dynamically from .enhanced-cognee-config.json or env vars.")
    print()
    for filepath, violations in sorted(all_violations.items()):
        for lineno, line, desc in violations:
            print(f"  {filepath}:{lineno}: [{desc}]")
            print(f"    {line[:120]}")
    sys.exit(1)


if __name__ == "__main__":
    main()
