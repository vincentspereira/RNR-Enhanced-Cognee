"""Tests for MCP server tool-group selection."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[2] / 'bin'


def load(name):
    spec = importlib.util.spec_from_file_location(name, BIN / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


groups = load('mcp_tool_groups')

# The pinned server inventory (122 tools). A server change that adds or
# renames tools must update the group mapping in the same change.
INVENTORY = frozenset({
    "add_memory", "add_observation", "advanced_search", "archive_category",
    "auto_deduplicate", "auto_summarize_old_memories", "cancel_task",
    "check_duplicate", "check_memory_access", "cluster_memories", "cognify",
    "cognify_status", "compact_knowledge_graph",
    "configure_discord_notifications", "configure_slack_notifications",
    "consolidate_memories", "create_backup", "create_shared_space",
    "cross_language_search", "deduplicate", "deduplication_report",
    "delete_memory", "delete_observation", "detect_language",
    "disable_webhook", "encrypt_memory", "end_session", "expand_search_query",
    "expire_memories", "extract_graph_v2", "find_consolidation_candidates",
    "forget_memory", "gdpr_check_consent", "gdpr_delete_user_data",
    "gdpr_export_user_data", "gdpr_list_consents", "gdpr_record_consent",
    "gdpr_verify_tenant_isolation", "get_confidence_report",
    "get_consolidation_report", "get_deduplication_stats",
    "get_encryption_stats", "get_graph_stats", "get_language_distribution",
    "get_llm_cost_report", "get_memories", "get_memory", "get_memory_age_stats",
    "get_memory_detail", "get_memory_history", "get_memory_importance",
    "get_memory_provenance", "get_observations", "get_performance_metrics",
    "get_prometheus_metrics", "get_related", "get_search_analytics",
    "get_search_facets", "get_session_context", "get_session_history",
    "get_shared_memories", "get_slow_queries", "get_stats",
    "get_summarization_stats", "get_summary_stats", "get_supported_languages",
    "get_sync_status", "get_tier_stats", "get_top_important_memories",
    "get_undo_history", "health", "improve", "ingest_db", "ingest_url",
    "intelligent_summarize", "list_agents", "list_backups", "list_data",
    "list_loader_plugins", "list_loaders", "list_tasks", "list_webhooks",
    "load_document_with_plugin", "promote_memory_tier", "publish_memory_event",
    "query_audit_log", "recall", "redo_last", "regex_extract_entities",
    "register_webhook", "remember", "rerank_search_results", "restore_backup",
    "revert_memory", "rollback_restore", "rotate_encryption_key",
    "save_interaction", "schedule_deduplication", "schedule_summarization",
    "schedule_task", "search", "search_by_language", "search_memories",
    "search_quick", "set_cost_budget", "set_memory_confidence",
    "set_memory_sharing", "set_memory_ttl", "start_session",
    "summarize_category", "summarize_old_memories", "summary_stats",
    "sync_agent_state", "test_notification_channel", "test_webhook",
    "translate_text", "undo_last", "update_importance_scores",
    "update_memory", "update_observation", "verify_backup", "verify_memory",
})


def test_inventory_is_fully_partitioned():
    mapped = set()
    for name, tools in groups.TOOL_GROUPS.items():
        assert tools, f"group {name} empty"
        mapped |= tools
    mapped |= groups.ADMIN_ONLY_TOOLS
    assert mapped == INVENTORY
    # no tool in two buckets
    overlaps = set()
    seen = set()
    for tools in list(groups.TOOL_GROUPS.values()) + [groups.ADMIN_ONLY_TOOLS]:
        overlaps |= (seen & tools)
        seen |= tools
    assert not overlaps


def test_admin_families_never_advertised_in_groups():
    advertised = set()
    for tools in groups.TOOL_GROUPS.values():
        advertised |= tools
    for tool in ("rotate_encryption_key", "restore_backup", "gdpr_delete_user_data",
                 "set_cost_budget", "register_webhook", "undo_last",
                 "schedule_summarization", "query_audit_log"):
        assert tool not in advertised or tool in groups.TOOL_GROUPS.get("ops_readonly", frozenset())
        if tool == "query_audit_log":
            assert tool in groups.TOOL_GROUPS["ops_readonly"]


def test_parse_selection_supports_unions_and_refuses_unknown():
    single = groups.parse_selection("graph")
    assert "cognify" in single and "add_memory" not in single
    combined = groups.parse_selection("memory_read, graph")
    assert "recall" in combined and "cognify" in combined
    assert "restore_backup" not in combined
    with pytest.raises(ValueError):
        groups.parse_selection("")
    with pytest.raises(ValueError):
        groups.parse_selection("graph, nonexistent")


def test_apply_to_registry_prunes_and_guards():
    registry = {name: object() for name in INVENTORY}
    summary = groups.apply_to_registry(registry, "memory_read")
    assert summary["selected"] == len(groups.TOOL_GROUPS["memory_read"])
    assert summary["removed"] == len(INVENTORY) - summary["selected"]
    assert set(registry) == set(groups.TOOL_GROUPS["memory_read"])
    partial = {"recall": object()}
    with pytest.raises(ValueError):
        groups.apply_to_registry(partial, "memory_read")  # missing tools refused
    with pytest.raises(ValueError):
        groups.apply_to_registry({"recall": object()}, "bogus")
