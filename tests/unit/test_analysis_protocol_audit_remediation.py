"""Offline protocol parsing regressions using synthetic HTTP responses only."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from src import llm_summarize as llm


@pytest.mark.parametrize("usage", [None, {}, {"total_tokens": None}, {"total_tokens": 0},
                                  {"total_tokens": True}, {"total_tokens": "12"},
                                  {"total_tokens": -2}, {"total_tokens": 2.5},
                                  {"total_tokens": 10**20}, {"total_tokens": 120}])
def test_http_usage_only_reconciles_reliable_integer_totals(tmp_path, monkeypatch, usage):
    payload = {"choices": [{"message": {"content": "Synthetic result"}}]}
    if usage is not None:
        payload["usage"] = usage
    raw = json.dumps(payload).encode()
    requests = []

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, *args, **kwargs):
            requests.append(True)

        def getresponse(self):
            return SimpleNamespace(status=200, read=lambda size: raw)

        def close(self):
            pass

    monkeypatch.setattr(llm, "HTTPSConnection", Connection)
    route = {"base_url": "https://model.invalid", "api_key": "synthetic", "model": "synthetic", "daily_token_cap": 50000}
    budget = llm.TokenBudget(tmp_path / "budget.sqlite3")
    result, tokens = asyncio.run(llm.budgeted_chat(route, budget, "tenant", "project",
                                                 llm.translate_messages("hello", "French"), max_tokens=2000))
    assert result == "Synthetic result"
    assert requests == [True]
    if usage == {"total_tokens": 120}:
        assert tokens == 120
        assert budget.used("tenant", "project") == 120
    else:
        assert tokens is None
        assert budget.used("tenant", "project") > 2000


def test_restart_retains_reservation_after_process_death(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    path = tmp_path / "budget.sqlite3"
    script = ("from src.llm_summarize import TokenBudget; import os,sys; "
              "TokenBudget(sys.argv[1]).reserve('tenant','project',800,1000); os._exit(0)")
    result = subprocess.run([sys.executable, "-c", script, str(path)],
                            cwd=Path(__file__).resolve().parents[2], capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr.decode()
    reopened = llm.TokenBudget(path)
    assert reopened.used("tenant", "project") == 800
    with pytest.raises(ValueError):
        reopened.reserve("tenant", "project", 201, 1000)
