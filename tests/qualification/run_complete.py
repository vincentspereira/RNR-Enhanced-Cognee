"""Run every qualification check and reject failures, errors or skipped tests.

Prepare native SDK builds, dashboard, Chromium, a disposable database and index
stores first. Credentials belong in the operator environment, never arguments.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True,
                        help="New private directory for logs, XML and retained fixtures")
    args = parser.parse_args(argv)
    repo = REPOSITORY_ROOT
    required = ("RNR_QUALIFICATION_DATABASE_URL", "RNR_QUALIFICATION_MODEL_CACHE",
                "RNR_QUALIFICATION_INDEX_SETTINGS")
    missing = [name for name in required if not os.environ.get(name)]
    missing += [name for name in ("node", "go", "cargo", "cc", "pg_dump", "pg_restore", "age", "age-keygen")
                if not shutil.which(name)]
    for name in ("clients/node/dist/index.js", "dashboard/nextjs-dashboard/.next/BUILD_ID"):
        if not (repo / name).is_file():
            missing.append(name)
    if missing:
        parser.error("Prepare complete qualification prerequisites: " + ", ".join(missing))
    artifacts = args.artifacts.expanduser().resolve()
    if artifacts.is_relative_to(repo.resolve()):
        parser.error("Private qualification artifacts must be outside the source checkout")
    artifacts.mkdir(mode=0o700, parents=False, exist_ok=False)
    env = dict(os.environ, RNR_QUALIFICATION_CROSS_LANGUAGE="1", RNR_QUALIFICATION_BROWSER="1",
               ENHANCED_LOAD_DOTENV="0", COGNEE_TELEMETRY_ENABLED="0", COGNEE_LOG_FILE="false")
    xml = artifacts / "qualification.xml"
    with (artifacts / "pytest.log").open("x", encoding="utf-8") as output:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/qualification/", "-q", "-p", "no:cacheprovider",
             "--override-ini=addopts=", "--junitxml=" + str(xml),
             "--basetemp=" + str(artifacts / "fixtures")],
            cwd=repo, env=env, stdout=output, stderr=output, check=False,
        )
    if not xml.is_file():
        print("ERR: qualification did not produce XML; inspect the private pytest.log")
        return result.returncode or 1
    try:
        suites = list(ET.parse(xml).getroot().iter("testsuite"))
        counts = {key: sum(int(s.get(key, "0")) for s in suites)
                  for key in ("tests", "failures", "errors", "skipped")}
        if any(value < 0 for value in counts.values()) or sum(counts[key] for key in ("failures", "errors", "skipped")) > counts["tests"]:
            raise ValueError("Invalid qualification counts")
    except (ET.ParseError, ValueError, OSError):
        print("ERR: invalid qualification XML; inspect the private pytest.log")
        return 1
    counts["passed"] = counts["tests"] - sum(counts[key] for key in ("failures", "errors", "skipped"))
    complete = result.returncode == 0 and counts["tests"] > 0 and not any(
        counts[key] for key in ("failures", "errors", "skipped"))
    summary = dict(counts, complete=complete, pytest_exit_code=result.returncode)
    (artifacts / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="ascii")
    print(json.dumps(summary))
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
