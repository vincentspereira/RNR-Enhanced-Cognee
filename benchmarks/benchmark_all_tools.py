#!/usr/bin/env python3
"""
Performance Benchmark - Enhanced Cognee MCP Server (119 tools)

Measures pure-Python overhead of all tool functions using mocked DB pools.
No live services or Docker required.

Usage:
    python benchmarks/benchmark_all_tools.py

Output:
    - ASCII table to stdout grouped by category
    - JSON results to benchmarks/results/benchmark_results.json

Exit code: always 0 (benchmark, not a test)
"""

import sys
import os
import asyncio
import time
import json
import statistics
from typing import Callable, Awaitable, Any
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup - must come before any project imports
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "bin"))

# ---------------------------------------------------------------------------
# Suppress noisy startup output during import
# ---------------------------------------------------------------------------
import io
import contextlib

# ---------------------------------------------------------------------------
# Pre-patch all external dependencies before importing the server module
# ---------------------------------------------------------------------------

# Minimal fake pool/connection that returns None-ish responses
class _FakeConn:
    async def execute(self, *a, **kw):
        return None
    async def fetch(self, *a, **kw):
        return []
    async def fetchval(self, *a, **kw):
        return None
    async def fetchrow(self, *a, **kw):
        return None
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        pass

class _FakePool:
    def acquire(self):
        return _FakeConn()
    async def close(self):
        pass

class _FakeQdrant:
    def get_collections(self):
        r = MagicMock()
        r.collections = []
        return r
    def search(self, *a, **kw):
        return []
    def upsert(self, *a, **kw):
        pass
    def delete(self, *a, **kw):
        pass

class _FakeRedis:
    async def ping(self):
        return True
    async def get(self, *a, **kw):
        return None
    async def set(self, *a, **kw):
        return True
    async def delete(self, *a, **kw):
        return 0
    async def keys(self, *a, **kw):
        return []
    async def close(self):
        pass

class _FakeNeo4j:
    def session(self):
        return self
    def __enter__(self):
        return self
    def __exit__(self, *a):
        pass
    def run(self, *a, **kw):
        return []
    def close(self):
        pass

# Patch module-level imports that would fail without installed packages
_fake_modules = {}

def _make_fake_module(name: str):
    m = MagicMock()
    m.__name__ = name
    m.__spec__ = MagicMock()
    return m

_optional_deps = [
    "asyncpg",
    "qdrant_client",
    "qdrant_client.models",
    "neo4j",
    "redis",
    "redis.asyncio",
    "dotenv",
    "cognee",
    "cognee.api",
    "cognee.api.v1",
    "cognee.api.v1.remember",
    "cognee.api.v1.remember.remember",
    "cognee.api.v1.forget",
    "cognee.api.v1.forget.forget",
    "cognee.tasks",
    "cognee.tasks.web_scraper",
    "cognee.tasks.web_scraper.web_scraper_task",
    "aiohttp",
    "cryptography",
    "cryptography.fernet",
    "hypothesis",
    "apscheduler",
    "apscheduler.schedulers",
    "apscheduler.schedulers.asyncio",
    "apscheduler.triggers",
    "apscheduler.triggers.cron",
    "mcp",
    "mcp.server",
    "mcp.types",
]

for _dep in _optional_deps:
    _fake_modules[_dep] = _make_fake_module(_dep)

# Make FastMCP a usable class
class _FakeFastMCP:
    def __init__(self, *a, **kw):
        pass
    def tool(self, *a, **kw):
        def decorator(fn):
            return fn
        return decorator
    async def run_stdio_async(self):
        pass

_fake_modules["mcp.server"].FastMCP = _FakeFastMCP
_fake_modules["mcp"].server = _fake_modules["mcp.server"]

# Make dotenv loadable
_fake_modules["dotenv"].load_dotenv = lambda *a, **kw: None

# Patch sys.modules before importing server
for _mod_name, _mod in _fake_modules.items():
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _mod

# ---------------------------------------------------------------------------
# Now patch the src.* modules that are imported at module level in the server
# ---------------------------------------------------------------------------

_src_stubs = [
    "src.memory_management",
    "src.memory_deduplication",
    "src.memory_summarization",
    "src.performance_analytics",
    "src.cross_agent_sharing",
    "src.realtime_sync",
    "src.language_detector",
    "src.multi_language_search",
    "src.intelligent_summarization",
    "src.advanced_search_reranking",
    "src.security_mcp",
    "src.logging_config",
    "src.mcp_response_formatter",
    "src.transaction_manager",
    "src.llm_cost_tracker",
    "src.session_manager",
    "src.audit_logger",
    "src.rate_limiter",
    "src.pii_detector",
    "src.circuit_breaker",
    "src.tracing",
    "src.memory_versioner",
    "src.memory_provenance",
    "src.memory_confidence",
    "src.memory_consolidator",
    "src.memory_tier_manager",
    "src.graph_compactor",
    "src.gdpr_manager",
    "src.plugin_loader",
    "src.webhook_manager",
    "src.encryption_manager",
    "src.memory_observation",
    "src.notification_manager",
    "src.memory_importance_scorer",
    "src.memory_reranker",
]

# Validation functions that the server calls inline on parameters
class _FakeValidationError(Exception):
    pass

class _FakeAuthorizationError(Exception):
    pass

class _FakeConfirmationRequiredError(Exception):
    pass

def _passthrough(val, *a, **kw):
    if isinstance(val, str):
        return val
    return val

def _validate_days(val, *a, **kw):
    return int(val) if val is not None else 90

def _validate_limit(val, *a, **kw):
    return int(val) if val is not None else 10

async def _require_agent_authorization(*a, **kw):
    pass

def _validate_dry_run_safe(*a, **kw):
    pass

def _handle_database_exception(exc, *a, **kw):
    return f"ERR {exc}"

def _handle_backup_exception(exc, *a, **kw):
    return f"ERR {exc}"

_fake_authorizer = MagicMock()
_fake_authorizer.check_backup_permission = AsyncMock(return_value=None)

_fake_confirmation_manager = MagicMock()
_fake_confirmation_manager.require_confirmation = MagicMock(return_value=None)

def _mock_get_logger(name=None):
    return MagicMock()

# Build stubs for all src modules
for _stub_name in _src_stubs:
    _m = _make_fake_module(_stub_name)
    # Security module - must export specific callables
    if _stub_name == "src.security_mcp":
        _m.ValidationError = _FakeValidationError
        _m.AuthorizationError = _FakeAuthorizationError
        _m.ConfirmationRequiredError = _FakeConfirmationRequiredError
        _m.validate_uuid = _passthrough
        _m.validate_days = _validate_days
        _m.validate_limit = _validate_limit
        _m.validate_agent_id = _passthrough
        _m.validate_category = _passthrough
        _m.validate_memory_content = _passthrough
        _m.sanitize_string = _passthrough
        _m.authorizer = _fake_authorizer
        _m.confirmation_manager = _fake_confirmation_manager
        _m.require_agent_authorization = _require_agent_authorization
        _m.validate_dry_run_safe = _validate_dry_run_safe
        _m.handle_database_exception = _handle_database_exception
        _m.handle_backup_exception = _handle_backup_exception
    elif _stub_name == "src.logging_config":
        _m.get_logger = _mock_get_logger
    elif _stub_name == "src.mcp_response_formatter":
        _m.success_response = lambda *a, **kw: "OK"
        _m.error_response = lambda *a, **kw: "ERR"
        _m.format_response = lambda *a, **kw: "OK"
    elif _stub_name == "src.transaction_manager":
        _m.TransactionManager = MagicMock()
        _m.execute_in_transaction = AsyncMock(return_value="OK")
        _m.execute_operation_with_transaction = AsyncMock(return_value="OK")
    elif _stub_name == "src.llm_cost_tracker":
        _m.LLMCostTracker = MagicMock()
        _m.init_cost_tracker = AsyncMock(return_value=None)
        _m.get_cost_tracker = MagicMock(return_value=None)
        _m.set_llm_context = MagicMock(return_value=None)
    elif _stub_name == "src.audit_logger":
        _m.AuditLogger = MagicMock()
        _m.AuditOperationType = MagicMock()
        _m.init_audit_logger = AsyncMock(return_value=None)
        _m.get_audit_logger = MagicMock(return_value=None)
    elif _stub_name == "src.rate_limiter":
        _m.RateLimiter = MagicMock()
        _m.init_rate_limiter = AsyncMock(return_value=None)
        _m.get_rate_limiter = MagicMock(return_value=None)
    elif _stub_name == "src.pii_detector":
        _m.PIIDetector = MagicMock()
        _m.init_pii_detector = AsyncMock(return_value=None)
        _m.get_pii_detector = MagicMock(return_value=None)
    elif _stub_name == "src.circuit_breaker":
        _m.CircuitBreaker = MagicMock()
        _m.get_circuit_breaker = MagicMock(return_value=None)
        _m.get_all_circuit_stats = MagicMock(return_value={})
    elif _stub_name == "src.tracing":
        _m.init_tracing = MagicMock(return_value=None)
        _m.trace_tool = lambda fn: fn
        _m.is_tracing_enabled = MagicMock(return_value=False)
    elif _stub_name == "src.memory_management":
        _m.MemoryManager = MagicMock()
        _m.RetentionPolicy = MagicMock()
        _m.RetentionPolicy.DELETE_OLD = "DELETE_OLD"
    elif _stub_name == "src.cross_agent_sharing":
        _m.CrossAgentMemorySharing = MagicMock()
        _m.SharePolicy = MagicMock()
    elif _stub_name == "src.intelligent_summarization":
        _m.IntelligentMemorySummarizer = MagicMock()
        _m.SummaryStrategy = MagicMock()
    elif _stub_name == "src.advanced_search_reranking":
        _m.AdvancedSearchEngine = MagicMock()
        _m.ReRankingStrategy = MagicMock()
    elif _stub_name in (
        "src.memory_versioner", "src.memory_provenance", "src.memory_confidence",
        "src.memory_consolidator", "src.memory_tier_manager", "src.graph_compactor",
        "src.gdpr_manager", "src.plugin_loader", "src.webhook_manager",
        "src.encryption_manager", "src.memory_observation", "src.notification_manager",
        "src.memory_importance_scorer", "src.memory_reranker",
    ):
        # All phase managers: init_X returns None, get_X returns None
        for _prefix in ("init_", "get_"):
            _short = _stub_name.replace("src.", "")
            _m.__dict__[f"{_prefix}{_short}"] = MagicMock(return_value=None)
        # Also add specific manager classes
        _m.EncryptionManager = MagicMock()
        _m.MemoryObservationManager = MagicMock()
        _m.NotificationManager = MagicMock()
        _m.MemoryImportanceScorer = MagicMock()
        _m.MemoryReranker = MagicMock()
        _m.GDPRManager = MagicMock()
        _m.PluginRegistry = MagicMock()
        _m.EnhancedCogneeLoader = MagicMock()
        _m.WebhookManager = MagicMock()
        _m.MemoryVersioner = MagicMock()
        _m.MemoryProvenanceTracker = MagicMock()
        _m.MemoryConfidenceManager = MagicMock()
        _m.MemoryConsolidator = MagicMock()
        _m.MemoryTierManager = MagicMock()
        _m.GraphCompactor = MagicMock()
    sys.modules[_stub_name] = _m

# Also stub out specific get_X functions that the server calls at the module level
for _mgr_func in [
    "get_encryption_manager", "get_observation_manager", "get_notification_manager",
    "get_importance_scorer", "get_reranker", "get_gdpr_manager",
    "get_plugin_registry", "get_webhook_manager", "get_memory_versioner",
    "get_provenance_tracker", "get_confidence_manager", "get_consolidator",
    "get_tier_manager", "get_graph_compactor",
]:
    # Patch in the relevant stub modules
    pass  # handled per-module above

# ---------------------------------------------------------------------------
# Import the server module with output suppressed
# ---------------------------------------------------------------------------
_null_io = io.StringIO()
_import_error = None
try:
    with contextlib.redirect_stdout(_null_io), contextlib.redirect_stderr(_null_io):
        import enhanced_cognee_mcp_server as _server
except Exception as _exc:
    _import_error = _exc

# ---------------------------------------------------------------------------
# Patch the global singletons in the server to None (they already are, but
# be explicit) so tools fail fast with "ERR X not available"
# ---------------------------------------------------------------------------
if _server is not None:
    _server.postgres_pool = None
    _server.qdrant_client = None
    _server.neo4j_driver = None
    _server.redis_client = None
    _server.memory_manager = None
    _server.memory_deduplicator = None
    _server.memory_summarizer = None
    _server.performance_analytics = None
    _server.cross_agent_sharing = None
    _server.realtime_sync = None
    _server.language_detector_instance = None
    _server.multi_language_search_instance = None
    _server.intelligent_summarizer = None
    _server.advanced_search_engine = None
    _server.llm_cost_tracker = None
    _server.session_manager = None
    _server.audit_logger_instance = None
    _server.rate_limiter_instance = None
    _server.pii_detector_instance = None
    _server.memory_versioner_instance = None
    _server.provenance_tracker_instance = None
    _server.confidence_manager_instance = None
    _server.consolidator_instance = None
    _server.tier_manager_instance = None
    _server.graph_compactor_instance = None
    _server.gdpr_manager_instance = None
    _server.plugin_registry_instance = None
    _server.webhook_manager_instance = None
    _server.encryption_manager_instance = None
    _server.observation_manager_instance = None
    _server.notification_manager_instance = None
    _server.importance_scorer_instance = None
    _server.reranker_instance = None
    # Patch maintenance_scheduler and backup_manager too
    if hasattr(_server, "maintenance_scheduler"):
        _server.maintenance_scheduler = None
    if hasattr(_server, "backup_manager"):
        _server.backup_manager = None
    if hasattr(_server, "scheduled_deduplication"):
        _server.scheduled_deduplication = None
    if hasattr(_server, "scheduled_summarization"):
        _server.scheduled_summarization = None

# ---------------------------------------------------------------------------
# Benchmark configuration
# ---------------------------------------------------------------------------
N_ITERATIONS = 50

# Sensible default arguments for each function
_BENCH_DEFAULTS = {
    # memory_id, agent_id, content, query, user_id, category, etc.
    "memory_id": "bench-mem-001",
    "agent_id": "bench-agent",
    "content": "benchmark test content",
    "query": "benchmark search query",
    "user_id": "bench-user",
    "category": "benchmark",
    "data": "benchmark data content",
    "text": "benchmark text content",
    "session_id": "bench-session-001",
    "backup_id": "bench-backup-001",
    "task_id": "bench-task-001",
    "space_name": "bench-space",
    "member_agents": "bench-agent-1,bench-agent-2",
    "event_type": "memory_added",
    "source_agent": "bench-agent-src",
    "target_agent": "bench-agent-tgt",
    "task_name": "cleanup",
    "schedule": "weekly",
    "policy": "shared",
    "allowed_agents": "bench-agent-2",
    "days": 30,
    "limit": 10,
    "dry_run": True,
    "backup_type": "manual",
    "dataset_name": "bench_dataset",
    "url": "https://example.com",
    "connection_string": "postgresql://localhost/bench",
    "search_type": "GRAPH_COMPLETION",
    "dataset": "bench_dataset",
    "everything": False,
    "data_id": None,
    "run_in_background": False,
    "ttl_days": 30,
    "description": "benchmark description",
    "monthly_usd": 10.0,
    "results_json": "[]",
    "tenant_id": "bench-tenant",
    "granted": True,
    "deduplication_id": None,
    "entity": "bench-entity",
    "attribute": "bench-attr",
    "value": "bench-value",
    "confidence": 0.9,
    "observation_id": "bench-obs-001",
    "channel_id": "bench-channel",
    "webhook_url": "https://hooks.example.com/test",
    "events": None,
    "new_key": None,
    "top_n": 5,
    "agent_id_opt": None,
    "include_memories": True,
    "active_only": False,
    "include_versions": True,
    "sample_size": 10,
    "max_expansions": 3,
    "threshold_ms": 1000.0,
    "group_by": "agent",
    "days_back": 30,
    "max_clusters": 5,
    "algorithm": "kmeans",
    "reranking_strategy": "hybrid",
    "strategy": "extractive",
    "language": "en",
    "target_language": "en",
    "source_languages": None,
    "table_name": "bench_table",
    "pattern": "\\b[A-Z]{2,}\\b",
    "depth": 2,
    "plugin_name": "PlainTextLoader",
    "file_path_str": "/tmp/bench.txt",
    "webhook_id": "bench-webhook-001",
    "endpoint_url": "https://hooks.example.com/bench",
    "secret": "bench-secret",
    "confirm_token": "CONFIRM-bench",
    "output_format": "json",
    "compress": True,
    "auto_verify": False,
    "requester": "bench-requester",
    "cron": "0 2 * * *",
    "enabled": True,
    "tier": "hot",
    "promote_reason": "frequent_access",
    "lookback_days": 30,
    "min_candidates": 2,
    "min_similarity": 0.85,
    "consolidation_id": "bench-consol-001",
    "version_id": "bench-ver-001",
    "reason": "benchmark test",
    "source": "benchmark",
    "operation_type": "read",
    "start_date": None,
    "end_date": None,
    "agent_id_filter": None,
    "page": 1,
    "page_size": 10,
    "score": 0.9,
    "search_query": "benchmark",
    "include_facets": False,
    "include_highlights": False,
    "rerank": False,
}


def _get_call_kwargs(fn_name: str, fn) -> dict:
    """
    Build a kwargs dict for a tool function using _BENCH_DEFAULTS.
    Inspects the function signature to pick the right args.
    """
    import inspect
    sig = inspect.signature(fn)
    kwargs = {}
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue

        val = None
        # Try exact match first
        if param_name in _BENCH_DEFAULTS:
            val = _BENCH_DEFAULTS[param_name]
        elif param.default is not inspect.Parameter.empty:
            val = param.default
        else:
            # Guess from type annotation
            ann = param.annotation
            if ann is str or (hasattr(ann, "__origin__") and ann.__origin__ is type(None)):
                val = "bench-value"
            elif ann is int:
                val = 10
            elif ann is float:
                val = 0.9
            elif ann is bool:
                val = False
            else:
                val = None

        kwargs[param_name] = val
    return kwargs


# ---------------------------------------------------------------------------
# Category definitions (19 groups, 119 tools)
# ---------------------------------------------------------------------------
CATEGORIES = {
    "core_memory": [
        "remember", "recall", "forget_memory", "improve", "save_interaction",
        "cognify_status", "add_memory", "search_memories", "get_memories",
        "get_memory", "update_memory", "delete_memory", "list_agents",
    ],
    "knowledge_graph": [
        "cognify", "search", "get_stats", "health", "list_data",
    ],
    "ttl_archive": [
        "expire_memories", "get_memory_age_stats", "set_memory_ttl",
        "archive_category",
    ],
    "deduplication": [
        "check_duplicate", "auto_deduplicate", "get_deduplication_stats",
        "deduplicate", "schedule_deduplication", "deduplication_report",
    ],
    "summarization": [
        "summarize_category", "get_summary_stats", "summarize_old_memories",
        "schedule_summarization", "summary_stats", "auto_summarize_old_memories",
        "get_summarization_stats", "intelligent_summarize",
    ],
    "performance_mon": [
        "get_performance_metrics", "get_slow_queries", "get_prometheus_metrics",
    ],
    "sharing_sync": [
        "set_memory_sharing", "check_memory_access", "get_shared_memories",
        "create_shared_space", "publish_memory_event", "get_sync_status",
        "sync_agent_state",
    ],
    "backup": [
        "create_backup", "restore_backup", "list_backups", "verify_backup",
        "rollback_restore",
    ],
    "scheduling": [
        "schedule_task", "list_tasks", "cancel_task",
    ],
    "language": [
        "detect_language", "get_supported_languages", "search_by_language",
        "get_language_distribution", "cross_language_search", "get_search_facets",
    ],
    "search_advanced": [
        "advanced_search", "expand_search_query", "get_search_analytics",
        "search_quick",
    ],
    "ingestion": [
        "ingest_url", "ingest_db", "translate_text", "regex_extract_entities",
        "extract_graph_v2", "list_loaders",
    ],
    "cost": [
        "get_llm_cost_report", "set_cost_budget",
    ],
    "session": [
        "start_session", "end_session", "get_session_context",
        "get_session_history",
    ],
    "audit_prov": [
        "query_audit_log", "get_memory_history", "revert_memory",
        "get_memory_provenance", "verify_memory", "set_memory_confidence",
        "get_confidence_report",
    ],
    "consolidation": [
        "find_consolidation_candidates", "consolidate_memories",
        "get_consolidation_report", "promote_memory_tier", "get_tier_stats",
        "compact_knowledge_graph", "get_graph_stats",
    ],
    "gdpr": [
        "gdpr_delete_user_data", "gdpr_export_user_data", "gdpr_record_consent",
        "gdpr_check_consent", "gdpr_list_consents", "gdpr_verify_tenant_isolation",
    ],
    "plugins_webhooks": [
        "list_loader_plugins", "load_document_with_plugin", "register_webhook",
        "list_webhooks", "test_webhook", "disable_webhook",
    ],
    "phase14": [
        "encrypt_memory", "get_encryption_stats", "rotate_encryption_key",
        "add_observation", "get_observations", "update_observation",
        "delete_observation", "configure_slack_notifications",
        "configure_discord_notifications", "test_notification_channel",
        "get_memory_importance", "update_importance_scores",
        "get_top_important_memories", "rerank_search_results",
        "cluster_memories", "get_memory_detail", "get_related",
    ],
}


# ---------------------------------------------------------------------------
# Timing helper
# ---------------------------------------------------------------------------
async def _time_fn(fn, kwargs: dict, n: int) -> list:
    """Run fn(**kwargs) n times and return list of elapsed_ms values."""
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            result = fn(**kwargs)
            if asyncio.isfuture(result) or asyncio.iscoroutine(result):
                await result
        except Exception:
            pass  # ERR return is expected - count as completed
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)
    return times


def _percentile(data: list, pct: float) -> float:
    """Compute percentile from a sorted or unsorted list."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (pct / 100.0) * (len(sorted_data) - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= len(sorted_data):
        return sorted_data[lo]
    frac = idx - lo
    return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac


def _stats(times: list) -> dict:
    return {
        "mean_ms": round(statistics.mean(times), 3),
        "p50_ms": round(_percentile(times, 50), 3),
        "p95_ms": round(_percentile(times, 95), 3),
        "min_ms": round(min(times), 3),
        "max_ms": round(max(times), 3),
    }


# ---------------------------------------------------------------------------
# Table formatting
# ---------------------------------------------------------------------------
COL_FN   = 28
COL_STAT =  9

def _header_line() -> str:
    return (
        f"  {'Function':<{COL_FN}} | "
        f"{'mean_ms':>{COL_STAT}} | "
        f"{'p50_ms':>{COL_STAT}} | "
        f"{'p95_ms':>{COL_STAT}} | "
        f"{'min_ms':>{COL_STAT}} | "
        f"{'max_ms':>{COL_STAT}}"
    )

def _sep_line() -> str:
    return (
        f"  {'-'*COL_FN} | "
        f"{'-'*COL_STAT} | "
        f"{'-'*COL_STAT} | "
        f"{'-'*COL_STAT} | "
        f"{'-'*COL_STAT} | "
        f"{'-'*COL_STAT}"
    )

def _data_line(fn_name: str, s: dict) -> str:
    name_trunc = fn_name[:COL_FN]
    return (
        f"  {name_trunc:<{COL_FN}} | "
        f"{s['mean_ms']:>{COL_STAT}.2f} | "
        f"{s['p50_ms']:>{COL_STAT}.2f} | "
        f"{s['p95_ms']:>{COL_STAT}.2f} | "
        f"{s['min_ms']:>{COL_STAT}.2f} | "
        f"{s['max_ms']:>{COL_STAT}.2f}"
    )


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------
async def run_benchmarks():
    if _import_error is not None:
        print(f"ERR Failed to import server module: {_import_error}")
        print("Some tools may still be benchmarked from direct lookups.")

    banner = "Performance Benchmark - Enhanced Cognee MCP Server (119 tools)"
    sep = "=" * len(banner)
    print(f"\n{banner}")
    print(sep)

    all_results = {}  # category -> {fn_name -> stats}
    all_times_flat = []  # for overall p50/p95

    slowest_fn = None
    slowest_mean = -1.0
    fastest_fn = None
    fastest_mean = float("inf")

    total_benchmarked = 0

    for category, fn_names in CATEGORIES.items():
        cat_results = {}
        print(f"\nCategory: {category} ({len(fn_names)} tools)")
        print(_header_line())
        print(_sep_line())

        for fn_name in fn_names:
            # Resolve function from server module
            fn = getattr(_server, fn_name, None)
            if fn is None:
                # Try to find it in the module's globals
                fn = globals().get(fn_name)
            if fn is None or not callable(fn):
                s = {"mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0,
                     "min_ms": 0.0, "max_ms": 0.0, "error": "not_found"}
                print(_data_line(fn_name + " [N/F]", s))
                cat_results[fn_name] = s
                continue

            kwargs = _get_call_kwargs(fn_name, fn)
            try:
                times = await _time_fn(fn, kwargs, N_ITERATIONS)
                s = _stats(times)
                all_times_flat.extend(times)
                total_benchmarked += 1

                if s["mean_ms"] > slowest_mean:
                    slowest_mean = s["mean_ms"]
                    slowest_fn = fn_name
                if s["mean_ms"] < fastest_mean:
                    fastest_mean = s["mean_ms"]
                    fastest_fn = fn_name

                print(_data_line(fn_name, s))
                cat_results[fn_name] = s
            except Exception as exc:
                s = {"mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0,
                     "min_ms": 0.0, "max_ms": 0.0, "error": str(exc)[:80]}
                print(_data_line(fn_name + " [ERR]", s))
                cat_results[fn_name] = s

        all_results[category] = cat_results

    # Summary
    print(f"\n{sep}")
    print("SUMMARY")
    overall_p50 = round(_percentile(all_times_flat, 50), 3) if all_times_flat else 0.0
    overall_p95 = round(_percentile(all_times_flat, 95), 3) if all_times_flat else 0.0
    print(f"  Total functions benchmarked : {total_benchmarked}")
    print(f"  Total categories            : {len(CATEGORIES)}")
    print(f"  Overall p50_ms              : {overall_p50:.2f}")
    print(f"  Overall p95_ms              : {overall_p95:.2f}")
    if slowest_fn:
        print(f"  Slowest function            : {slowest_fn} ({slowest_mean:.2f}ms mean)")
    if fastest_fn:
        print(f"  Fastest function            : {fastest_fn} ({fastest_mean:.2f}ms mean)")

    # Write JSON results
    results_dir = PROJECT_ROOT / "benchmarks" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / "benchmark_results.json"

    output_data = {
        "benchmark_info": {
            "n_iterations": N_ITERATIONS,
            "total_functions_benchmarked": total_benchmarked,
            "total_categories": len(CATEGORIES),
            "overall_p50_ms": overall_p50,
            "overall_p95_ms": overall_p95,
            "slowest_function": {"name": slowest_fn, "mean_ms": round(slowest_mean, 3)},
            "fastest_function": {"name": fastest_fn, "mean_ms": round(fastest_mean, 3)},
        },
        "results_by_category": all_results,
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(output_data, fh, indent=2)

    print(f"\nResults saved to: benchmarks/results/benchmark_results.json")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(run_benchmarks())
    sys.exit(0)
