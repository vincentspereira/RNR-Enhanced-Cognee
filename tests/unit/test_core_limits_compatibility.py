"""Exercise the core LLM limiter against real limits storage/strategy APIs."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest


@pytest.mark.parametrize("enabled,interval,expected", [
    (True, 60, [True, True, False]), (True, 30, [True, True, True, True, False]),
    (False, 60, [True, True, True, True, True]),
])
def test_core_moving_window_admits_and_refuses_actual_hits(monkeypatch, enabled, interval, expected):
    # Isolate only settings/logging; storage and strategy use the real package.
    config = ModuleType("cognee.infrastructure.llm.config")
    config.get_llm_config = lambda: SimpleNamespace(llm_rate_limit_enabled=enabled,
        llm_rate_limit_requests=2, llm_rate_limit_interval=interval)
    logging = ModuleType("cognee.shared.logging_utils")
    logging.get_logger = lambda: SimpleNamespace(info=lambda message: None)
    monkeypatch.setitem(sys.modules, config.__name__, config)
    monkeypatch.setitem(sys.modules, logging.__name__, logging)
    path = Path(__file__).resolve().parents[2] / "cognee/infrastructure/llm/structured_output_framework/litellm_instructor/llm/rate_limiter.py"
    spec = importlib.util.spec_from_file_location("qualified_core_limiter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    limiter = module.llm_rate_limiter()
    assert module.llm_rate_limiter() is limiter
    assert [limiter.hit_limit() for _ in expected] == expected
    assert limiter._storage.check()
