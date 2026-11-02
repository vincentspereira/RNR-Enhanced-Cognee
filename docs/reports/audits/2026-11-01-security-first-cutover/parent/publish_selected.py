"""Publish only selected reviewed source and regular sanitised evidence files."""
import hashlib
import json
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "docs/reports/audits/2026-11-01-security-first-cutover"
BRANCH = "codex/enhanced-cognee-security-first-cutover-20261101"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


assert git("branch", "--show-current") == BRANCH
assert git("remote", "get-url", "origin") == "https://github.com/vincentspereira/RNR-Enhanced-Cognee.git"
assert git("diff", "--name-only") == ""  # All task paths are new; no existing tracked edits.
assert git("diff", "--cached", "--name-only") == ""
inputs = json.loads((BASE / "parent/publication-input-manifest.json").read_text())["files"]
for name, expected in inputs.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name

selected = set(inputs)
selected.update({
    "integrations/hermes/deployment/prepare_security_first_cutover.py",
    "tests/unit/test_security_first_cutover.py",
    "tests/unit/test_security_first_cutover_review_regressions.py",
})
suffixes = {".py", ".md", ".json", ".xml", ".log", ".patch", ".txt", ".zip"}


def select_regular(directory):
    # Shallow only: never descend synthetic sandbox/fixture trees or follow links.
    for path in directory.iterdir():
        if stat.S_ISREG(path.lstat().st_mode) and path.suffix in suffixes:
            selected.add(str(path.relative_to(ROOT)))


select_regular(BASE)
for directory in ("implementation", "route-review", "review-round1", "repair-round1", "review-round2", "parent"):
    select_regular(BASE / directory)
for directory in ("red-regressions", "green-S01", "green-regressions", "original-current-source", "reviewer-obsolete-fixture", "green-current-inventory"):
    select_regular(BASE / "repair-round1" / directory)
for directory in ("historical-run", "fresh-run", "payload-run"):
    select_regular(BASE / "review-round2" / directory)
for name in selected:
    assert stat.S_ISREG((ROOT / name).lstat().st_mode), name
    assert not (ROOT / name).is_symlink(), name

inventory_path = BASE / "parent/publication-inventory.json"
assert not inventory_path.exists()
with inventory_path.open("x") as handle:
    json.dump({"selected_paths": sorted(selected),
               "excluded": "Synthetic sandbox/fixture directories and special files remain preserved locally; no blind recursive staging",
               "sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sorted(selected)}}, handle, indent=2)
    handle.write("\n")
selected.add(str(inventory_path.relative_to(ROOT)))
subprocess.run(["git", "add", "--", *sorted(selected)], cwd=ROOT, check=True)
staged = set(git("diff", "--cached", "--name-only").splitlines())
assert staged == selected
for name, expected in inputs.items():
    staged_bytes = subprocess.check_output(["git", "show", ":" + name], cwd=ROOT)
    assert hashlib.sha256(staged_bytes).hexdigest() == expected, name
maintained = [name for name in selected if name.startswith(("integrations/", "tests/")) or
              name in {str((BASE / "OWNER-NEXT-PLAN.md").relative_to(ROOT)),
                       str((BASE / "SOURCE-ACCEPTANCE.md").relative_to(ROOT))}]
scoped = subprocess.run(["git", "diff", "--cached", "--check", "--", *sorted(maintained)], cwd=ROOT, capture_output=True, text=True)
assert scoped.returncode == 0, scoped.stdout + scoped.stderr
full = subprocess.run(["git", "diff", "--cached", "--check"], cwd=ROOT, capture_output=True, text=True)
full_path = BASE / "parent/publication-full-whitespace.log"
assert not full_path.exists()
full_path.write_text(full.stdout + full.stderr)
# Keep full original evidence bytes; never rewrite logs/XML to suppress whitespace findings.
print(json.dumps({"selected_regular_files": len(selected), "scoped_source_and_owner_docs_whitespace_exit": scoped.returncode,
                  "full_evidence_whitespace_exit": full.returncode,
                  "whitespace_report": str(full_path), "accepted_input_blobs_verified": len(inputs)}, indent=2))
subprocess.run(["git", "commit", "-m", "[verified] Prepare security-first API cutover artifacts and owner plan"], cwd=ROOT, check=True)
print("COMMIT", git("rev-parse", "HEAD"))
