"""Two explicit qualification batches; no installation or fleet activation.

Source runs current unit and Hermes/operator/backup regressions. Installed runs
the pinned native candidate conversation/access acceptance on Ubuntu-Hermes.
A green report never qualifies outstanding recovery, credential or fleet gates.
Private reports and fixtures must use a new directory outside this checkout.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def counts(path):
    suites = list(ET.parse(path).getroot().iter("testsuite"))
    if not suites:
        raise ValueError("No qualification suites")
    result = {key: sum(int(s.get(key, "0")) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    if (any(value < 0 for value in result.values()) or result["tests"] == 0
            or sum(result[k] for k in ("failures", "errors", "skipped")) > result["tests"]):
        raise ValueError("Invalid qualification counts")
    result["passed"] = result["tests"] - sum(result[k] for k in ("failures", "errors", "skipped"))
    return result


def environment():
    # Do not forward arbitrary owner credentials or dotenv settings to tests.
    names = {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT", "WSL_DISTRO_NAME",
             "RNR_RESTIC", "RNR_PWSH", "RNR_BACKUP_V12_SUPPORT"}
    env = {key: value for key, value in os.environ.items() if key in names}
    env.update(ENHANCED_LOAD_DOTENV="0", COGNEE_TELEMETRY_ENABLED="0", TELEMETRY_DISABLED="1",
               COGNEE_LOG_FILE="false", HF_HUB_OFFLINE="1", LITELLM_LOCAL_MODEL_COST_MAP="True",
               PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    return env


def run_pytest(name, selection, artifacts, env):
    report = artifacts / (name + ".xml")
    # AF_UNIX fixture sockets have a 108-byte path budget. Retain a short,
    # private fixture root rather than nesting it below a long report path.
    fixtures = tempfile.mkdtemp(prefix="ecq-")
    command = [sys.executable, "-m", "pytest", *selection, "-q", "-p", "no:cacheprovider",
               "--override-ini=addopts=", "--color=no", "--junitxml=" + str(report),
               "--basetemp=" + fixtures]
    with (artifacts / (name + ".log")).open("x", encoding="utf-8") as output:
        try:
            process = subprocess.run(command, cwd=ROOT, env=env, stdout=output, stderr=output,
                                     check=False, timeout=1800)
        except subprocess.TimeoutExpired:
            return dict(name=name, complete=False, category="test_timeout", retained_fixtures=fixtures)
    result = dict(name=name, exit_code=process.returncode, retained_fixtures=fixtures)
    try:
        result.update(counts(report))
        result["complete"] = process.returncode == 0 and not any(
            result[k] for k in ("failures", "errors", "skipped"))
    except (OSError, ValueError, ET.ParseError):
        result.update(complete=False, category="missing_or_invalid_report")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", choices=("source", "installed"))
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--revision", help="Full published candidate revision; required for the installed batch")
    args = parser.parse_args(argv)
    path = args.artifacts.expanduser().absolute()
    if path != path.resolve() or path.is_relative_to(ROOT):
        parser.error("Use a new private directory outside the source checkout, without symlinks")
    if args.batch == "installed" and os.environ.get("WSL_DISTRO_NAME") != "Ubuntu-Hermes":
        parser.error("Installed qualification must run inside Ubuntu-Hermes")
    if args.batch == "installed" and (not args.revision or len(args.revision) != 40
                                      or any(c not in "0123456789abcdef" for c in args.revision)):
        parser.error("Supply --revision with the full published candidate commit")
    path.mkdir(mode=0o700, exist_ok=False)
    os.chmod(path, 0o700)
    env = environment()
    results = []
    if args.batch == "source":
        unit = dict(env, PYTHONPATH=str(ROOT / "tests/support/network_guard"))
        results.append(run_pytest("units", ["tests/unit"], path, unit))
        print(json.dumps(results[-1]), flush=True)
        files = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "tests/qualification").glob("test_hermes_*.py"))
        files += ["tests/qualification/test_cognee_encrypted_collection.py",
                  "scripts/qualification/test_backup_v12.py"]
        results.append(run_pytest("hermes-and-recovery", files, path, env))
        print(json.dumps(results[-1]), flush=True)
    else:
        # The launcher verifies each archived public file before root execution.
        # No production service/profile switch or general-purpose command input.
        with (path / "installed.log").open("x", encoding="utf-8") as output:
            process = subprocess.run(["bash", "scripts/qualification/run_hermes_launch_native.sh",
                                      str(ROOT), args.revision], cwd=ROOT, env=env,
                                     stdout=output, stderr=output, check=False, timeout=1800)
        try:
            result = json.loads((path / "installed.log").read_text())
            if not isinstance(result, dict) or result.get("complete") is not True or process.returncode != 0:
                raise ValueError("Native acceptance incomplete")
        except (OSError, ValueError):
            result = {"complete": False, "category": "native_acceptance_incomplete_see_private_log"}
        results.append(dict(result, name="native-candidate-conversations-and-access", exit_code=process.returncode))
    summary = dict(batch=args.batch, complete=all(r.get("complete") is True for r in results),
                   lanes=results, created_utc=datetime.now(timezone.utc).isoformat(),
                   installed_host_qualified=False, fleet_launch_approved=False)
    (path / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="ascii")
    print(json.dumps(summary))
    return 0 if summary["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
