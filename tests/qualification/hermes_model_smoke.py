"""Opt-in synthetic chat check using the owner's existing configured cloud route.

Never collected by pytest/CI. Requires explicit --use-configured-cloud. The
everyday profile is read only for its existing model route/key; the key is passed
to one child process and is not saved into the test profile or printed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
import uuid


QUERIES = {
    "recall": "For the entirely fictional Cedar qualification project, what standing review interval did we decide on? Use the saved evidence and cite the memory record.",
    "correct": "A clear correction to our entirely fictional Cedar qualification project planning decision: the standing review cycle is nine days, replacing the previous eleven-day cycle. Explain the corrected schedule in one sentence.",
    "uncertain": "For the entirely fictional Cedar qualification project, I heard the review cycle may be either nine days or monthly. I have not decided which is correct. What should we do?",
}


def main():
    import yaml
    from dotenv import dotenv_values
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=QUERIES)
    parser.add_argument("--use-configured-cloud", action="store_true", required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    home = Path.home() / ".hermes"
    profile = home / "profiles/enhanced-cognee-test"
    root = Path.home() / "agent-workspace/enhanced-cognee-test-runtime"
    marker = json.loads((profile / "enhanced-cognee-qualification.json").read_text())
    assert marker.get("synthetic_only") is True
    source = yaml.safe_load((home / "config.yaml").read_text())
    model = source["model"]
    assert urlsplit(model["base_url"]).scheme == "https"
    assert not urlsplit(model["base_url"]).username
    variable = model["key_env"]
    key = dotenv_values(home / ".env")[variable]
    assert key
    path = profile / "config.yaml"
    assert not path.is_symlink()
    previous = path.read_text()
    config = yaml.safe_load(previous)
    config["model"] = {k: v for k, v in model.items() if k in {"default", "provider", "base_url", "api_mode", "key_env"}}
    configured_provider = source.get("providers", {}).get(model["provider"], {})
    config["providers"] = {model["provider"]: {k: v for k, v in configured_provider.items()
        if k in {"name", "base_url", "model", "key_env", "models", "discover_models"}}}
    config["fallback_providers"] = []
    sys.path.insert(0, str(repo / "integrations/hermes"))
    # Import the client without importing the package's Hermes provider module.
    import importlib.util
    spec = importlib.util.spec_from_file_location("qualification_memory_client", repo / "integrations/hermes/enhanced_cognee/client.py")
    client_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client_module)
    token = json.loads((root / "secrets/profile-token.json").read_text())["ENHANCED_COGNEE_ACCESS_TOKEN"]
    client = client_module.MemoryClient("http://127.0.0.1:28080", token, 5)
    records = client.request("POST", "/v1/memories/recall", {"query": "Cedar qualification project review cycle", "limit": 5})["results"]
    candidates = [r for r in records if "cedar qualification" in r["content"].lower()]
    assert len(candidates) == 1, "Seed the invented Cedar decision with a capture test first"
    before = candidates[0]
    count = client.request("GET", "/v1/memories/status")["active_records"]
    trace = root / ("model-" + args.scenario + "-" + uuid.uuid4().hex + ".jsonl")
    diagnostic = trace.with_suffix(".stderr")
    env = dict(os.environ, **{variable: key})
    # Built-in provider env references can differ from the named custom route.
    if model["provider"] == "zai":
        env["ZAI_API_KEY"] = key
    cli = Path.home() / "agent-workspace/hermes-agent/.hermes/bin/hermes"
    try:
        path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False))
        out_fd = os.open(trace, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        err_fd = os.open(diagnostic, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(out_fd, "w") as out, os.fdopen(err_fd, "w") as err:
            result = subprocess.run([str(cli), "-p", "enhanced-cognee-test", "chat", "--oneshot", "--quiet",
                "--format", "stream-json", "--toolsets", "memory", "--max-turns", "6", "--run-budget", "90",
                "--in", str(root / "fixture-workspace"), "--query", QUERIES[args.scenario]],
                cwd=cli.parents[2], env=env, stdout=out, stderr=err, timeout=150)
    finally:
        path.write_text(previous)
    events = []
    for line in trace.read_text().splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    final = next((v for v in reversed(events) if v.get("type") == "result"), {})
    assert result.returncode == 0 and final.get("exit_code") == 0, "Hermes did not complete the synthetic chat"
    tools = [v["name"] for v in events if v.get("type") == "tool_use"]
    after = client.request("GET", "/v1/memories/" + before["id"])
    if args.scenario == "correct":
        assert "enhanced_correct" in tools and after["version"] == before["version"] + 1
        # A historical explanation can legitimately mention the superseded
        # interval. Check the current decision clause, rather than banning every
        # occurrence of the old word anywhere in the corrected explanation.
        assert re.search(r"standing planning decision is (?:a )?nine-day review cycle", after["content"].lower())
    else:
        assert after["version"] == before["version"]
        assert client.request("GET", "/v1/memories/status")["active_records"] == count
        if args.scenario == "recall":
            interval = re.search(r"standing planning decision is (?:an? )?([a-z]+)-day review cycle", before["content"].lower())
            assert interval and interval[1] in final.get("text", "").lower()
        else:
            assert "enhanced_clarify" in tools and "?" in final.get("text", "")
            assert not {"enhanced_remember", "enhanced_correct", "enhanced_retract"}.intersection(tools)
    print(json.dumps({"scenario": args.scenario, "passed": True, "model": model["default"],
                      "tool_calls": tools, "current_version": after["version"],
                      "duration_ms": final.get("duration_ms"), "tokens": final.get("tokens"),
                      "test_model_settings_restored": path.read_text() == previous}, ensure_ascii=True))


if __name__ == "__main__":
    main()
