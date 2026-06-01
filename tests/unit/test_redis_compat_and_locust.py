"""Phase 5 tail: redis_compat alias + Locust scenario smoke test.

- ``redis_compat`` is a labelled alias of the valkey adapter (routes
  through the same redis-py implementation); test the factory dispatch
  arms and confirm the underlying client is the redis.asyncio.Redis-
  shaped object.
- The Locust file at ``tests/load/locustfile.py`` is a workload spec,
  not a unit-testable thing -- but we can at least confirm it imports
  cleanly (no syntax errors) and exposes the expected ``HttpUser``
  classes.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from src import db_factory
from src.db_adapters import cache_redis_compat


class TestRedisCompatDispatch:
    def test_async_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_CACHE_PROVIDER", "redis_compat")
        # Confirms the dispatch arm hits cache_redis_compat, not
        # something else. Patch redis.asyncio.Redis to avoid live IO.
        with patch("redis.asyncio.Redis", return_value=MagicMock()) as R:
            client = db_factory.get_cache_client()
        assert R.called
        assert client is R.return_value

    def test_sync_factory_dispatch(self, monkeypatch):
        monkeypatch.setenv("ENHANCED_CACHE_PROVIDER", "redis_compat")
        with patch("redis.Redis", return_value=MagicMock()) as R:
            client = db_factory.get_sync_cache_client()
        assert R.called
        assert client is R.return_value

    def test_redis_compat_in_valid_cache_set(self):
        assert "redis_compat" in db_factory._VALID_CACHE

    def test_module_reexports_valkey_factories(self):
        """The alias module just re-exports cache_valkey's factory funcs."""
        from src.db_adapters import cache_valkey

        assert cache_redis_compat.create_async_client is (
            cache_valkey.create_async_client
        )
        assert cache_redis_compat.create_sync_client is (
            cache_valkey.create_sync_client
        )


class TestLocustfileImports:
    """Confirm the load-test workload spec is structurally sound."""

    @pytest.mark.skipif(
        not os.getenv("ENHANCED_RUN_LOCUST_IMPORT"),
        reason=(
            "Executing the locustfile in-process triggers locust/gevent "
            "monkey-patching that can deadlock under pytest-asyncio (this "
            "hung the whole CI unit run). Syntax is validated by "
            "test_locustfile_parses_without_locust; set "
            "ENHANCED_RUN_LOCUST_IMPORT=1 to run the full import check."
        ),
    )
    def test_locustfile_imports(self):
        # Locust is a heavy dependency to require for the unit-test
        # suite; only run this check if it happens to be installed.
        locust = pytest.importorskip("locust")

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_loadtest_locustfile",
            "tests/load/locustfile.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Expected User classes -- both the default-mix ones (existing)
        # and the Phase 5 extended scenarios (new).
        expected = [
            "ReadHeavyUser",
            "WriteHeavyUser",
            "MixedWorkloadUser",
            "HealthCheckUser",
            "SemanticSearchUser",
            "KnowledgeGraphUser",
            "GDPRWorkflowUser",
            "BackupVerifyUser",
        ]
        for cls_name in expected:
            assert hasattr(module, cls_name), (
                f"locustfile missing {cls_name}; tests/load/README.md "
                f"says it should be there"
            )
            cls = getattr(module, cls_name)
            assert issubclass(cls, locust.HttpUser), (
                f"{cls_name} must subclass locust.HttpUser"
            )

    def test_locustfile_parses_without_locust(self):
        """Without locust installed, py_compile still validates syntax."""
        import py_compile
        # Will raise SyntaxError or similar if the file is malformed.
        # Doesn't require locust to be importable.
        py_compile.compile("tests/load/locustfile.py", doraise=True)
