"""Exercise the actual executable CLI in fresh processes, synthetic scratch only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from test_library import CLI, MODULE, ViewParser


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="owned-library-exercise-"))
    root = base / "owned"
    log = []

    def run(*arguments, selected=root, expected=0):
        command = [str(CLI), "--root", str(selected), *arguments]
        result = subprocess.run(command, capture_output=True)
        log.append({"command": command, "exit_code": result.returncode,
                    "stdout": result.stdout.decode("utf-8"), "stderr": result.stderr.decode("utf-8")})
        if result.returncode != expected:
            raise AssertionError(log[-1])
        return result.stdout

    run("init")
    source = base / "working.md"
    original = "# Synthetic working document\r\nCafe: caf\u00e9.\r\n".encode("utf-8")
    source.write_bytes(original)
    created = json.loads(run("create", "--file", str(source), "--title", "Working document", "--author", "Synthetic reviewer"))
    note_id = created["id"]
    assert run("read", note_id) == original
    replacement = base / "correction.md"
    replacement.write_bytes(b"# Reviewed working document\nCorrected by human.\n")
    run("update", note_id, "--file", str(replacement), "--expect-revision", "1", "--author", "Synthetic reviewer", "--reason", "Human correction")
    assert run("read", note_id, "--revision", "1") == original
    assert run("read", note_id) == replacement.read_bytes()
    assert len(json.loads(run("history", note_id))) == 2
    assert len(json.loads(run("search", "corrected"))) == 1
    raw = base / "evidence.md"
    raw.write_bytes(b"# Synthetic raw evidence\r\n</pre><script>alert(1)</script>\r\n")
    imported = json.loads(run("import", "--file", str(raw), "--title", "Evidence", "--author", "Synthetic reviewer", "--origin", "synthetic:fixture-v1"))
    run("update", imported["id"], "--file", str(replacement), "--expect-revision", "1", "--author", "Synthetic reviewer", "--reason", "Forbidden raw overwrite", expected=2)
    run("create", "--file", str(replacement), "--title", "Evidence annotation", "--author", "Synthetic reviewer", "--corrects", imported["id"], "--reason", "Human annotation; evidence unchanged")
    assert len(json.loads(run("list"))) == 3
    destination = base / "exported"
    exported = json.loads(run("export", "--destination", str(destination)))
    assert exported["notes"] == 3 and exported["revisions"] == 4
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    after = {str(p.relative_to(destination)): p.read_bytes() for p in destination.rglob("*") if p.is_file()}
    assert before == after
    assert run("read", imported["id"], selected=destination) == raw.read_bytes()
    assert run("history", note_id, selected=destination) == run("history", note_id)
    output = args.evidence / "reading.html"
    run("view", "--output", str(output))
    parsed = ViewParser()
    parsed.feed(output.read_text(encoding="utf-8"))
    assert len(parsed.scripts) == 1 and "alert" not in parsed.scripts[0]
    assert not any(tag in {"img", "iframe", "object"} for tag, _ in parsed.tags)
    summary = {"synthetic_only": True, "scratch": str(base), "notes": 3, "revisions": 4,
               "implementation_sha256": hashlib.sha256(MODULE.read_bytes()).hexdigest(),
               "entry_point_sha256": hashlib.sha256(CLI.read_bytes()).hexdigest(),
               "fresh_process_reopen": True, "exact_export_bytes": True, "raw_update_rejected": True,
               "html_structure_and_injection_checked": True, "browser_ui_acceptance": False,
               "html": str(output), "html_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
               "source_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in before.items()}}
    (args.evidence / "cli-exercise.json").write_text(json.dumps(log, ensure_ascii=True, indent=2) + "\n", encoding="ascii")
    (args.evidence / "exercise-summary.json").write_text(json.dumps(summary, ensure_ascii=True, indent=2) + "\n", encoding="ascii")
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
