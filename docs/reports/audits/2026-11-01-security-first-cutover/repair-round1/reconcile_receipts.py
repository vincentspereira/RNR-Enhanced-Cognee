"""Reconcile actual JUnit case identities, immutable inputs and process receipts."""
import collections
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
AUDIT = OUT.parent
REVIEW = AUDIT / "review-round1"
SOURCE = ROOT / "integrations/hermes/deployment/prepare_security_first_cutover.py"
ORIGINAL = ROOT / "tests/unit/test_security_first_cutover.py"
REGRESSIONS = ROOT / "tests/unit/test_security_first_cutover_review_regressions.py"
SOURCE_PIN = "d9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text("ascii"))


def cases(path):
    # Parse only preserved, locally generated pytest JUnit evidence.
    tree = ET.parse(path)
    result = []
    for case in tree.iter("testcase"):
        state = next((s for s in ("failure", "error", "skipped") if case.find(s) is not None), "passed")
        result.append({"classname": case.get("classname"), "name": case.get("name"), "state": state})
    return result


def keyed(items):
    result = {c["name"]: c for c in items}
    assert len(result) == len(items), "duplicate case identities"
    return result


def main():
    assert sha(SOURCE) == SOURCE_PIN
    assert sha(ORIGINAL) == "4c75858260829750aacb4e659b98a6fac698af88b99dbecb01c8e79683b61777"
    assert sha(REVIEW / "test_independent_challenges.py") == "549b332ca4b469ed17101f9e4e1fc4341bd49551ce82ab38fd569d53a78af12f"
    archive = AUDIT / "parent/round1-source.zip"
    assert sha(archive) == "ff21c524ac91e1fdb426de8c7c4c2ec4533c94bc554252282bf0efedd495196b"
    labels = ["red-regressions", "green-S01", "green-regressions", "original-current-source",
              "reviewer-obsolete-fixture", "green-current-inventory"]
    receipts = {}
    for label in labels:
        receipt = load(OUT / label / "process-receipt.json")
        actual = cases(OUT / label / "junit.xml")
        assert actual == receipt["cases"]
        assert len(actual) == receipt["total"]
        assert sha(OUT / label / "process.log") == receipt["log_sha256"]
        assert sha(OUT / label / "junit.xml") == receipt["junit_sha256"]
        receipts[label] = {k: receipt[k] for k in ("exit_code", "total", "counts", "bindings_sha256")}
    assert receipts["red-regressions"]["counts"] == {"passed": 0, "failure": 3, "error": 0, "skipped": 0}
    assert receipts["green-current-inventory"]["counts"] == {"passed": 176, "failure": 0, "error": 0, "skipped": 0}
    assert receipts["original-current-source"]["counts"] == {"passed": 122, "failure": 1, "error": 0, "skipped": 0}
    assert receipts["reviewer-obsolete-fixture"]["counts"] == {"passed": 48, "failure": 2, "error": 0, "skipped": 0}
    current = cases(OUT / "green-current-inventory/junit.xml")
    current_original = keyed([c for c in current if c["classname"].endswith("test_current_original_cases")])
    current_review = keyed([c for c in current if c["classname"].endswith("test_current_review_cases")])
    current_regressions = keyed([c for c in current if c["classname"].endswith("test_security_first_cutover_review_regressions")])
    assert (len(current_original), len(current_review), len(current_regressions)) == (123, 50, 3)
    baseline_original = keyed(cases(REVIEW / "regressions.xml"))
    baseline_review = keyed(cases(REVIEW / "challenges.xml"))
    obsolete_original = keyed(cases(OUT / "original-current-source/junit.xml"))
    obsolete_review = keyed(cases(OUT / "reviewer-obsolete-fixture/junit.xml"))
    assert baseline_original.keys() == current_original.keys() == obsolete_original.keys()
    assert baseline_review.keys() == current_review.keys() == obsolete_review.keys()
    assert collections.Counter(c["state"] for c in baseline_original.values()) == {"passed": 123}
    assert collections.Counter(c["state"] for c in baseline_review.values()) == {"passed": 47, "failure": 3}
    mapping = []
    original_path = str(ORIGINAL.relative_to(ROOT))
    reviewer_path = str((REVIEW / "test_independent_challenges.py").relative_to(ROOT))
    for group, baseline, obsolete, corrected, original_file, current_file in [
        ("original", baseline_original, obsolete_original, current_original, original_path,
         str((OUT / "test_current_original_cases.py").relative_to(ROOT))),
        ("reviewer", baseline_review, obsolete_review, current_review, reviewer_path,
         str((OUT / "test_current_review_cases.py").relative_to(ROOT)))]:
        for name in sorted(baseline):
            transform = "source/root/output binding only; test body unchanged"
            if name == "test_snapshot_collection_reads_only_units_helper_modules_interpreter":
                transform = "exact reader physical module keys rebound to runtime/lib/python3.12/site-packages; all assertions unchanged"
            elif name.startswith("test_C01_snapshot_rechecks_both_manager_views["):
                transform = "exact_content installed=False -> installed=True; all assertions unchanged"
            elif name.startswith("test_S01_"):
                transform = "unchanged original body called under exact unsafe_path_link Refusal assertion; historical false-PASS assertion is unreachable"
            elif name.startswith("test_L02_"):
                transform = "unchanged original body called under exact inventory_or_loaded_or_candidate_drift Refusal assertion; historical false-PASS assertion is unreachable"
            mapping.append({"group": group, "original_nodeid": original_file + "::" + name,
                            "obsolete_replay_nodeid": (original_file if group == "original" else current_file) + "::" + name,
                            "corrected_nodeid": current_file + "::" + name,
                            "original_state": baseline[name]["state"], "obsolete_fixture_replay_state": obsolete[name]["state"],
                            "corrected_state": corrected[name]["state"], "transformation": transform})
    assert len(mapping) == 173 and len({m["original_nodeid"] for m in mapping}) == 173
    regression_map = {
        "test_S01_alias_dotdot_rejects_hidden_symlink_before_fingerprinting": "test_S01_interpreter_alias_dotdot_must_not_hide_symlink_ancestor",
        "test_L01_exact_installed_module_mapping_is_readable": "test_L01_installed_site_packages_layout_is_readable",
        "test_L02_root_decoys_cannot_authorize_changed_installed_modules": "test_L02_candidate_root_decoys_must_not_substitute_for_runtime_modules"}
    assert set(regression_map) == set(current_regressions)
    red = keyed(cases(OUT / "red-regressions/junit.xml"))
    assert red.keys() == current_regressions.keys()
    new_regressions = [{"nodeid": str(REGRESSIONS.relative_to(ROOT)) + "::" + name,
                        "maps_to_reviewer_nodeid": reviewer_path + "::" + target,
                        "red": red[name]["state"], "green": current_regressions[name]["state"]}
                       for name, target in regression_map.items()]
    value = {"helper_sha256": SOURCE_PIN, "receipts": receipts, "case_mapping": mapping,
             "new_regression_mapping": new_regressions,
             "current_executed_cases": 176, "historical_logical_cases": 173,
             "new_regression_implementations_repeating_review_contracts": 3,
             "reviewer_logical_cases_replayed": 50, "reviewer_cases_deselected": 0,
             "errors": 0, "skips": 0, "distinct_repaired_defects": 2,
             "immutable_baseline_archive_sha256": sha(archive),
             "independent_review_status": "pending fresh review; this is implementer repair evidence only"}
    with (OUT / "case-reconciliation.json").open("x", encoding="ascii") as f:
        json.dump(value, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")
    pins = {str(p.relative_to(ROOT)): sha(p) for p in [SOURCE, ORIGINAL, REGRESSIONS,
        REVIEW / "test_independent_challenges.py", OUT / "copied-original-cases.py", OUT / "copied-review-cases.py",
        OUT / "test_current_original_cases.py", OUT / "test_current_review_cases.py", OUT / "run_tests.py", Path(__file__)]}
    with (OUT / "final-source-test-hashes.json").open("x", encoding="ascii") as f:
        json.dump(pins, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps({"current_groups": {"original": len(current_original), "reviewer": len(current_review),
                       "regressions": len(current_regressions)}, "hashes": pins,
                      "case_mapping_count": len(mapping), "receipts": {k: {n: v[n] for n in ("exit_code", "total", "counts")} for k, v in receipts.items()}}, indent=2))


if __name__ == "__main__":
    main()
