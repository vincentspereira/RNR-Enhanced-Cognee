"""Release review must not accept stale, missing or untrusted hosted evidence."""
from __future__ import annotations

from copy import deepcopy
import json
import subprocess
from types import SimpleNamespace

import pytest

from scripts.check_release_readiness import POLICY_FILE, assess_release, evaluate_checks, gh_json, validate_policy


CANDIDATE = "a" * 40
BASE = "b" * 40
POLICY = json.loads(POLICY_FILE.read_text())


def runs():
    return [{"id": index + 1, "name": name, "head_sha": CANDIDATE,
             "app": {"id": POLICY["app_id"], "slug": POLICY["app_slug"]},
             "status": "completed", "conclusion": "success"}
            for index, name in enumerate(POLICY["required_checks"])]


def protection():
    return {"enforce_admins": {"enabled": True}, "required_status_checks": {
        "strict": True, "contexts": list(POLICY["required_checks"]),
        "checks": [{"context": name, "app_id": POLICY["app_id"]}
                   for name in POLICY["required_checks"]]}}


def api_fixture(*, records=None, protected=None, pages=None, comparison=None, move=None):
    records = runs() if records is None else records
    protected = protection() if protected is None else protected
    calls = []

    def api(endpoint, *, paginate=False):
        calls.append(endpoint)
        if endpoint.endswith("/commits/candidate"):
            if move == "candidate" and calls.count(endpoint) > 1:
                return {"sha": "c" * 40}
            return {"sha": CANDIDATE}
        if endpoint.endswith("/commits/main"):
            if move == "main" and calls.count(endpoint) > 1:
                return {"sha": "d" * 40}
            return {"sha": BASE}
        if "/check-runs?" in endpoint:
            assert paginate
            return pages if pages is not None else [{"check_runs": records, "total_count": len(records)}]
        if endpoint.endswith("/protection"):
            return protected
        if "/compare/" in endpoint:
            return comparison if comparison is not None else {"behind_by": 0, "status": "ahead"}
        raise AssertionError("Unexpected GitHub evidence request")

    return api


def test_successful_snapshot_does_not_authorize_merge_or_owner_acceptance():
    report = assess_release("candidate", POLICY, api_fixture())
    assert report["hosted_checks_ready"]
    assert report["revision"] == CANDIDATE
    assert report["merge_authorized_by_this_report"] is False
    assert report["installed_host_and_owner_acceptance"] == "not_assessed"


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "skipped", "neutral", "timed_out", None])
def test_only_success_satisfies_a_required_check(conclusion):
    records = runs()
    records[0]["conclusion"] = conclusion
    assert not assess_release("candidate", POLICY, api_fixture(records=records))["hosted_checks_ready"]


def test_in_progress_rerun_overrides_an_older_success():
    records = runs()
    newest = deepcopy(records[0])
    newest.update(id=100, status="in_progress", conclusion=None)
    records.append(newest)
    check = evaluate_checks(CANDIDATE, records, POLICY)[0]
    assert check["check_id"] == 100 and not check["passed"]


def test_failed_rerun_overrides_an_older_success():
    records = runs()
    newest = deepcopy(records[0])
    newest.update(id=100, conclusion="failure")
    records.append(newest)
    assert not evaluate_checks(CANDIDATE, records, POLICY)[0]["passed"]


@pytest.mark.parametrize("app", [{"id": 99, "slug": "github-actions"},
                                 {"id": 15368, "slug": "other-app"}, None])
def test_spoofed_check_name_from_another_app_is_not_accepted(app):
    records = runs()
    records[0]["app"] = app
    assert not evaluate_checks(CANDIDATE, records, POLICY)[0]["passed"]


def test_success_on_another_commit_is_not_accepted():
    records = runs()
    records[0]["head_sha"] = BASE
    assert not evaluate_checks(CANDIDATE, records, POLICY)[0]["passed"]


def test_no_checks_is_not_a_vacuous_success():
    assert not assess_release("candidate", POLICY, api_fixture(records=[]))["hosted_checks_ready"]


def test_failure_on_second_page_is_not_lost():
    records = runs()
    newer = deepcopy(records[0])
    newer.update(id=1000, conclusion="failure")
    pages = [{"total_count": len(records) + 1, "check_runs": records},
             {"total_count": len(records) + 1, "check_runs": [newer]}]
    assert not assess_release("candidate", POLICY, api_fixture(pages=pages))["hosted_checks_ready"]


@pytest.mark.parametrize("pages", [[], [{"check_runs": [], "total_count": 1}],
                                   [{"check_runs": []}], [{"check_runs": {}, "total_count": 0}]])
def test_incomplete_api_evidence_is_refused(pages):
    with pytest.raises(ValueError):
        assess_release("candidate", POLICY, api_fixture(pages=pages))


def test_conflicting_duplicate_check_snapshot_is_refused():
    records = runs()
    duplicate = deepcopy(records[0])
    duplicate["conclusion"] = "failure"
    records.append(duplicate)
    with pytest.raises(ValueError):
        evaluate_checks(CANDIDATE, records, POLICY)


@pytest.mark.parametrize("change", ["admin_bypass", "not_strict", "wrong_app", "missing_check",
                                    "additional_check", "additional_context"])
def test_incomplete_or_changed_protection_is_not_ready(change):
    protected = protection()
    required = protected["required_status_checks"]
    if change == "admin_bypass":
        protected["enforce_admins"]["enabled"] = False
    elif change == "not_strict":
        required["strict"] = False
    elif change == "wrong_app":
        required["checks"][0]["app_id"] = None
    elif change == "missing_check":
        required["checks"].pop()
    elif change == "additional_check":
        required["checks"].append({"context": "another-required-check", "app_id": 99})
    else:
        required["contexts"].append("another-required-check")
    assert not assess_release("candidate", POLICY, api_fixture(protected=protected))["hosted_checks_ready"]


@pytest.mark.parametrize("comparison", [{"behind_by": 1, "status": "diverged"},
                                       {"behind_by": False, "status": "ahead"}, {}])
def test_stale_or_unknown_base_comparison_is_not_ready(comparison):
    assert not assess_release("candidate", POLICY, api_fixture(comparison=comparison))["hosted_checks_ready"]


@pytest.mark.parametrize("move", ["candidate", "main"])
def test_references_moving_during_review_prevent_clearance(move):
    assert not assess_release("candidate", POLICY, api_fixture(move=move))["hosted_checks_ready"]


def test_api_failure_does_not_leak_gh_error_or_grant_clearance():
    def unavailable(*args, **kwargs):
        raise ValueError("Evidence unavailable")

    with pytest.raises(ValueError):
        assess_release("candidate", POLICY, unavailable)


def test_duplicate_policy_check_names_are_refused():
    policy = deepcopy(POLICY)
    policy["required_checks"].append(policy["required_checks"][0])
    with pytest.raises(ValueError):
        validate_policy(policy)


def test_older_gh_paginated_json_pages_are_all_decoded(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(stdout='{"page": 1}\n {"page": 2}\n')

    monkeypatch.setattr(subprocess, "run", run)
    assert gh_json("repos/example/repo/checks", paginate=True) == [{"page": 1}, {"page": 2}]
    assert "--paginate" in calls[0] and "--slurp" not in calls[0]
    assert calls[0][2:4] == ["--hostname", "github.com"]


def test_paginated_json_trailing_garbage_is_not_silently_accepted(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(stdout='{"page":1}\ngarbage'))
    with pytest.raises(ValueError):
        gh_json("repos/example/repo/checks", paginate=True)


def test_gh_error_message_is_redacted(monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["gh"], stderr="private diagnostic must not escape")

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(ValueError) as error:
        gh_json("repos/example/repo/checks")
    assert str(error.value) == "GitHub evidence unavailable; check gh access privately"


def test_rerun_starting_without_a_new_commit_prevents_clearance():
    baseline = api_fixture()
    reads = 0

    def api(endpoint, **kwargs):
        nonlocal reads
        result = baseline(endpoint, **kwargs)
        if "/check-runs?" in endpoint:
            reads += 1
            if reads == 2:
                result = deepcopy(result)
                result[0]["check_runs"][0].update(status="in_progress", conclusion=None)
        return result

    report = assess_release("candidate", POLICY, api)
    assert report["references_unchanged"]
    assert not report["checks_unchanged"]
    assert not report["hosted_checks_ready"]
