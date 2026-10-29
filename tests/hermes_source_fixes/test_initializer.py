"""Source/unit-only initializer regression; no full server import or services.

Compile the real initializer body, substituting dependency constructors and
factory imports. This proves Python global binding, not backend readiness.
"""
import ast
import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "bin/enhanced_cognee_mcp_server.py"
HOOKS = {
    "memory_deduplicator": "MemoryDeduplicator",
    "memory_summarizer": "MemorySummarizer",
    "performance_analytics": "PerformanceAnalytics",
    "cross_agent_sharing": "CrossAgentMemorySharing",
    "realtime_sync": "RealTimeMemorySync",
}


class Instance:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def initialize(self):
        pass

    async def ping(self):
        pass

    async def fetchval(self, query):
        return 1

    def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def session(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def run(self, query):
        return None

    def get_collections(self):
        return SimpleNamespace(collections=[])


def initializer_namespace():
    tree = ast.parse(SERVER.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                    and n.name == "init_enhanced_stack")
    namespace = {
        "logger": logging.getLogger("initializer-fixture"),
        "app_logger": logging.getLogger("initializer-fixture"),
        "os": SimpleNamespace(getenv=lambda key, default=None: default),
    }
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and n.value.value is None:
            for target in n.targets:
                if isinstance(target, ast.Name):
                    namespace[target.id] = None
    # Every external initializer is a harmless constructor double.
    for n in ast.walk(function):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            name = n.func.id
            if name[0].isupper() or name.startswith("init_"):
                namespace[name] = Instance
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(SERVER), "exec"), namespace)
    return namespace


class InitializerTests(unittest.TestCase):
    def test_five_existing_module_hooks_receive_initialized_instances(self):
        namespace = initializer_namespace()
        pool, vector, graph, cache = (Instance() for _ in range(4))

        async def relational(**kwargs):
            return pool

        factory = SimpleNamespace(
            get_relational_pool=relational,
            get_vector_client=lambda **kwargs: vector,
            get_graph_driver=lambda: graph,
            get_cache_client=lambda: cache,
            get_provider_summary=lambda: dict.fromkeys(
                ("vector", "graph", "relational", "cache"), "fixture"),
        )
        language = SimpleNamespace(LanguageDetector=Instance)
        search = SimpleNamespace(MultiLanguageSearch=Instance)
        with patch.dict("sys.modules", {
            "src.db_factory": factory,
            "src.language_detector": language,
            "src.multi_language_search": search,
        }):
            asyncio.run(namespace["init_enhanced_stack"]())

        expected_args = {
            "memory_deduplicator": (pool, vector),
            "memory_summarizer": (pool, {}),
            "performance_analytics": (pool, cache),
            "cross_agent_sharing": (pool,),
            "realtime_sync": (cache, pool),
        }
        for hook in HOOKS:
            with self.subTest(hook=hook):
                self.assertIsInstance(namespace[hook], Instance)
                self.assertEqual(namespace[hook].args, expected_args[hook])
        self.assertIs(namespace["memory_manager"].args[0], pool)


if __name__ == "__main__":
    unittest.main()
