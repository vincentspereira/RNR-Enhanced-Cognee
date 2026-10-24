#!/usr/bin/env python3
"""Read-only, fail-closed review of GitHub checks on one immutable revision.

This checks hosted evidence and branch protection, not owner/installed-host
acceptance. It never merges, changes settings, dispatches work or prints tokens.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote


POLICY_FILE = Path(__file__).resolve().parents[1] / ".github/release-checks.json"
SHA = re.compile(r"[0-9a-f]{40}\Z")


def validate_policy(policy: dict) -> dict:
    fields = {"schema_version", "repository", "branch", "app_id", "app_slug", "required_checks"}
    if not isinstance(policy, dict) or set(policy) != fields or policy["schema_version"] != 1:
        raise ValueError("Unsupported release policy")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", policy["repository"]):
        raise ValueError("Invalid repository policy")
    if (not isinstance(policy["app_id"], int) or isinstance(policy["app_id"], bool)
            or policy["app_id"] <= 0 or policy["app_slug"] != "github-actions"):
        raise ValueError("Use the verified GitHub Actions application identity")
    if policy["branch"] != "main":
        raise ValueError("This release policy protects main")
    checks = policy["required_checks"]
    if (not isinstance(checks, list) or not checks or len(checks) > 100
            or any(not isinstance(name, str) or not name.isascii() or not name.strip()
                   or len(name) > 200 or any(ord(c) < 32 for c in name) for name in checks)
            or len(set(checks)) != len(checks)):
        raise ValueError("Required checks must be unique bounded names")
    return policy


def evaluate_checks(sha: str, records: list, policy: dict) -> list[dict]:
    """Only the newest matching check from the configured app can satisfy a name."""
    if not SHA.fullmatch(sha) or not isinstance(records, list):
        raise ValueError("Invalid revision or check collection")
    results = []
    for name in policy["required_checks"]:
        candidates = []
        for item in records:
            if not isinstance(item, dict) or item.get("name") != name or item.get("head_sha") != sha:
                continue
            app = item.get("app")
            if not isinstance(app, dict) or (app.get("id"), app.get("slug")) != (
                    policy["app_id"], policy["app_slug"]):
                continue
            if not isinstance(item.get("id"), int) or isinstance(item["id"], bool) or item["id"] <= 0:
                raise ValueError("Malformed required check identity")
            candidates.append(item)
        if not candidates:
            results.append({"name": name, "passed": False, "reason": "missing_trusted_exact_revision_check"})
            continue
        latest_id = max(item["id"] for item in candidates)
        newest = [item for item in candidates if item["id"] == latest_id]
        states = {(item.get("status"), item.get("conclusion")) for item in newest}
        if len(states) != 1:
            raise ValueError("Inconsistent required check snapshot")
        latest = newest[0]
        passed = latest.get("status") == "completed" and latest.get("conclusion") == "success"
        # Do not echo arbitrary provider strings, URLs, annotations or error text.
        reason = "success" if passed else "not_completed_successfully"
        results.append({"name": name, "check_id": latest_id, "passed": passed, "reason": reason})
    return results


def gh_json(endpoint: str, *, paginate: bool = False):
    command = ["gh", "api", "--hostname", "github.com", endpoint]
    if paginate:
        command.append("--paginate")
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=True)
        if paginate:
            # gh 2.45 supports --paginate but not --slurp. Decode each complete
            # page, refusing trailing garbage instead of silently losing pages.
            decoder = json.JSONDecoder()
            pages = []
            position = 0
            while position < len(result.stdout):
                if result.stdout[position].isspace():
                    position += 1
                    continue
                page, position = decoder.raw_decode(result.stdout, position)
                pages.append(page)
            return pages
        return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise ValueError("GitHub evidence unavailable; check gh access privately") from exc


def checked_sha(value) -> str:
    sha = value.get("sha") if isinstance(value, dict) else None
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise ValueError("GitHub did not return an immutable revision")
    return sha


def read_checks(endpoint: str, api) -> list:
    pages = api(endpoint, paginate=True)
    if not isinstance(pages, list) or not pages:
        raise ValueError("Missing paginated check evidence")
    records = []
    totals = []
    for page in pages:
        if (not isinstance(page, dict) or not isinstance(page.get("check_runs"), list)
                or type(page.get("total_count")) is not int or page["total_count"] < 0):
            raise ValueError("Malformed paginated check evidence")
        records.extend(page["check_runs"])
        totals.append(page["total_count"])
    ids = {item.get("id") for item in records if isinstance(item, dict) and type(item.get("id")) is int}
    if len(set(totals)) != 1 or len(ids) != totals[0]:
        raise ValueError("Incomplete or changing check evidence; retry the review")
    return records


def assess_release(ref: str, policy: dict, api=gh_json) -> dict:
    validate_policy(policy)
    if not isinstance(ref, str) or not ref or len(ref) > 250 or any(ord(c) < 32 for c in ref):
        raise ValueError("Use a bounded revision or branch reference")
    root = "repos/" + policy["repository"]
    endpoint = root + "/commits/" + quote(ref, safe="")
    base_endpoint = root + "/commits/" + policy["branch"]
    sha = checked_sha(api(endpoint))
    base = checked_sha(api(base_endpoint))
    check_endpoint = root + "/commits/" + sha + "/check-runs?filter=all&per_page=100"
    records = read_checks(check_endpoint, api)
    checks = evaluate_checks(sha, records, policy)
    protection = api(root + "/branches/" + policy["branch"] + "/protection")
    required = protection.get("required_status_checks") if isinstance(protection, dict) else None
    if not isinstance(required, dict):
        required = {}
    actual = required.get("checks", [])
    if not isinstance(actual, list):
        raise ValueError("Malformed required-check protection")
    expected = {(name, policy["app_id"]) for name in policy["required_checks"]}
    actual_pairs = set()
    for check in actual:
        if not isinstance(check, dict) or not isinstance(check.get("context"), str):
            raise ValueError("Malformed protected check identity")
        actual_pairs.add((check["context"], check.get("app_id")))
    # Additional requirements need review, never silent omission from readiness.
    contexts = required.get("contexts")
    protected = (actual_pairs == expected and isinstance(contexts, list)
                 and set(contexts) == set(policy["required_checks"])
                 and required.get("strict") is True
                 and isinstance(protection, dict)
                 and isinstance(protection.get("enforce_admins"), dict)
                 and protection["enforce_admins"].get("enabled") is True)
    comparison = api(root + "/compare/" + base + "..." + sha)
    up_to_date = (isinstance(comparison, dict) and type(comparison.get("behind_by")) is int
                  and comparison["behind_by"] == 0
                  and comparison.get("status") in {"ahead", "identical"})
    unchanged = checked_sha(api(endpoint)) == sha and checked_sha(api(base_endpoint)) == base
    final_checks = evaluate_checks(sha, read_checks(check_endpoint, api), policy)
    checks_unchanged = checks == final_checks
    ready = (all(item["passed"] for item in checks) and protected and up_to_date
             and unchanged and checks_unchanged)
    return {"repository": policy["repository"], "revision": sha, "base_revision": base,
            "checks": checks, "protection_matches": protected, "up_to_date": up_to_date,
            "references_unchanged": unchanged, "checks_unchanged": checks_unchanged,
            "hosted_checks_ready": ready,
            "installed_host_and_owner_acceptance": "not_assessed",
            "merge_authorized_by_this_report": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, help="Candidate branch or immutable 40-character commit")
    args = parser.parse_args(argv)
    try:
        policy = validate_policy(json.loads(POLICY_FILE.read_text(encoding="ascii")))
        report = assess_release(args.ref, policy)
    except (ValueError, OSError, TypeError, KeyError):
        print(json.dumps({"hosted_checks_ready": False, "error": "Evidence unavailable or invalid; no release clearance"}))
        return 2
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["hosted_checks_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
