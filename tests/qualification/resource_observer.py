"""Observe explicitly selected synthetic Linux services and a qualification command.

Never reads process arguments, environment values or file contents. RSS includes
shared pages; PSS apportions them when Linux grants access. Not an OS isolation
test, leak detector, machine-wide budget or production capacity certification.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time


def process_stat(path: Path) -> dict:
    raw = path.read_text()
    fields = raw[raw.rindex(")") + 2:].split()
    return {"ppid": int(fields[1]), "ticks": int(fields[11]) + int(fields[12]),
            "started": int(fields[19]), "rss_bytes": int(fields[21]) * os.sysconf("SC_PAGE_SIZE")}


def descendants(rows: dict, root: int) -> set:
    selected = {root} if root in rows else set()
    while True:
        added = {pid for pid, value in rows.items() if value["ppid"] in selected} - selected
        if not added:
            return selected
        selected.update(added)


def sample(roots: dict, expected: dict, proc: Path = Path("/proc")) -> dict:
    rows = {}
    for path in proc.glob("[0-9]*/stat"):
        try:
            rows[int(path.parent.name)] = process_stat(path)
        except (OSError, ValueError, IndexError):
            continue  # A short-lived child can exit between listing and reading.
    result = {}
    for name, root in roots.items():
        members = descendants(rows, root)
        alive = root in rows and rows[root]["started"] == expected[name]
        if not alive:
            members = set()  # Never attribute an unrelated process after PID reuse.
        pss = []
        for pid in members:
            try:
                lines = (proc / str(pid) / "smaps_rollup").read_text().splitlines()
                pss.append(next(int(line.split()[1]) * 1024 for line in lines if line.startswith("Pss:")))
            except (OSError, ValueError, StopIteration):
                pass
        result[name] = {"root_present": alive, "processes": len(members),
            "rss_bytes": sum(rows[p]["rss_bytes"] for p in members),
            "pss_bytes": sum(pss) if len(pss) == len(members) and members else None,
            "cpu_ticks": {str(pid) + ":" + str(rows[pid]["started"]): rows[pid]["ticks"] for pid in members}}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--process", action="append", default=[], metavar="LABEL=PID")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=2)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not .25 <= args.interval <= 30 or args.output.exists() or args.output.is_symlink():
        parser.error("Supply a command, a new output file and an interval between 0.25 and 30 seconds")
    roots, expected = {}, {}
    for item in args.process:
        name, pid = item.split("=", 1)
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", name) or name == "workload" or name in roots:
            parser.error("Use unique service labels; workload is reserved")
        roots[name] = int(pid)
        if roots[name] <= 1 or roots[name] == os.getpid() or list(roots.values()).count(roots[name]) > 1 or Path("/proc", pid).stat().st_uid != os.getuid():
            parser.error("Select existing disposable services owned by this operator")
        expected[name] = process_stat(Path("/proc", pid, "stat"))["started"]
    started = time.monotonic()
    child = subprocess.Popen(command)
    roots["workload"] = child.pid
    expected["workload"] = process_stat(Path("/proc", str(child.pid), "stat"))["started"]
    samples, metrics, previous = 0, {}, {}
    try:
        while child.poll() is None:
            current = sample(roots, expected)
            samples += 1
            for name, values in current.items():
                data = metrics.setdefault(name, {"initial_rss_bytes": values["rss_bytes"],
                    "peak_rss_bytes": 0, "peak_pss_bytes": None, "cpu_seconds_observed": 0,
                    "samples_with_missing_root": 0, "samples_without_complete_pss": 0})
                data["peak_rss_bytes"] = max(data["peak_rss_bytes"], values["rss_bytes"])
                data["last_rss_bytes"] = values["rss_bytes"]
                if values["pss_bytes"] is not None:
                    data["peak_pss_bytes"] = max(data["peak_pss_bytes"] or 0, values["pss_bytes"])
                else:
                    data["samples_without_complete_pss"] += 1
                data["samples_with_missing_root"] += not values["root_present"]
                for ident, ticks in values["cpu_ticks"].items():
                    prior = previous.get((name, ident), ticks if samples == 1 else 0)
                    data["cpu_seconds_observed"] += max(0, ticks - prior) / os.sysconf("SC_CLK_TCK")
                    previous[name, ident] = ticks
            time.sleep(args.interval)
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
    result = {"workload_exit_code": child.returncode, "seconds": round(time.monotonic()-started, 2),
        "samples": samples, "interval_seconds": args.interval, "services": metrics,
        "scope": "Explicit Linux fixture process trees plus qualification workload; no chat server, Hermes or GPU",
        "limits": ["RSS double-counts shared pages", "PSS requires read permission",
                   "Short-lived processes between samples can be missed", "CPU is observed lifetime deltas",
                   "No production capacity or memory-leak conclusion"]}
    with args.output.open("x", encoding="ascii") as handle:
        handle.write(json.dumps(result, ensure_ascii=True, indent=2) + "\n")
    return child.returncode or int(any(v["samples_with_missing_root"] for k, v in metrics.items() if k != "workload"))


if __name__ == "__main__":
    raise SystemExit(main())
