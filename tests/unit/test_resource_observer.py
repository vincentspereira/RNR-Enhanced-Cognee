"""Resource accounting must not attribute unrelated or recycled Linux PIDs."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


spec = importlib.util.spec_from_file_location("resource_observer",
    Path(__file__).resolve().parents[1] / "qualification/resource_observer.py")
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


def fixture_process(root, pid, parent, started, *, pss=24):
    directory = root / str(pid)
    directory.mkdir()
    values = ["0"] * 22
    for index, value in {0: "S", 1: parent, 11: 20, 12: 10, 19: started, 21: 3}.items():
        values[index] = str(value)
    (directory / "stat").write_text(str(pid) + " (fixture worker) " + " ".join(values))
    (directory / "smaps_rollup").write_text("Pss: " + str(pss) + " kB\n")


def test_process_tree_excludes_siblings_and_sums_proportional_memory(tmp_path):
    fixture_process(tmp_path, 10, 1, 7)
    fixture_process(tmp_path, 11, 10, 8)
    fixture_process(tmp_path, 12, 11, 9)
    fixture_process(tmp_path, 20, 1, 10)
    result = observer.sample({"fixture": 10}, {"fixture": 7}, tmp_path)["fixture"]
    assert result["root_present"] and result["processes"] == 3
    assert result["pss_bytes"] == 3 * 24 * 1024
    assert result["rss_bytes"] == 9 * os.sysconf("SC_PAGE_SIZE")
    assert result["cpu_ticks"] == {"10:7": 30, "11:8": 30, "12:9": 30}


def test_recycled_root_and_unreadable_pss_are_explicit(tmp_path):
    fixture_process(tmp_path, 10, 1, 8)
    replaced = observer.sample({"fixture": 10}, {"fixture": 7}, tmp_path)["fixture"]
    assert not replaced["root_present"] and replaced["processes"] == 0
    # An unavailable/malformed PSS sample must not become a false zero.
    (tmp_path / "10/smaps_rollup").write_text("Pss: unavailable\n")
    result = observer.sample({"fixture": 10}, {"fixture": 8}, tmp_path)["fixture"]
    assert result["root_present"] and result["pss_bytes"] is None


def test_observer_preserves_a_failing_workload_exit_and_records_no_arguments(tmp_path):
    output = tmp_path / "result.json"
    result = subprocess.run([sys.executable, observer.__file__, "--interval", ".25",
        "--output", str(output), "--", sys.executable, "-c", "raise SystemExit(3)"],
        capture_output=True, text=True, timeout=5, check=False)
    assert result.returncode == 3
    report = json.loads(output.read_text())
    assert report["workload_exit_code"] == 3 and "command" not in report and "environment" not in report
