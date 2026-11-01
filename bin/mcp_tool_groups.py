"""Tool-group selection for the Enhanced Cognee MCP server.

Groups are explicit allow-lists over the server's tool inventory. A tool
not listed in any group is never advertised when a group selection is
active (fail-safe default: administrative families stay operator-only).
Selections may combine groups with commas; the union is advertised.
"""
from __future__ import annotations

TOOL_GROUPS: dict[str, frozenset[str]] = {
    "memory_read": frozenset({
        "get_memories", "get_memory", "get_memory_detail", "get_memory_history",
        "get_memory_importance", "get_memory_provenance", "get_observations",
        "get_related", "get_shared_memories", "get_top_important_memories",
        "recall", "search", "search_memories", "search_quick", "advanced_search",
        "cross_language_search", "search_by_language", "expand_search_query",
        "get_search_facets", "get_search_analytics", "verify_memory",
        "check_memory_access", "get_session_context", "get_session_history",
        "list_agents", "get_language_distribution", "get_supported_languages",
        "detect_language", "get_confidence_report", "regex_extract_entities",
        "list_data",
    }),
    "graph": frozenset({
        "cognify", "cognify_status", "extract_graph_v2", "compact_knowledge_graph",
        "get_graph_stats", "cluster_memories",
    }),
    "ingest": frozenset({
        "ingest_url", "ingest_db", "load_document_with_plugin",
        "list_loaders", "list_loader_plugins",
    }),
    "analysis": frozenset({
        "intelligent_summarize", "summarize_category", "summarize_old_memories",
        "auto_summarize_old_memories", "auto_deduplicate", "deduplicate",
        "deduplication_report", "find_consolidation_candidates",
        "consolidate_memories", "get_consolidation_report",
        "get_deduplication_stats", "get_summarization_stats",
        "get_summary_stats", "summary_stats", "rerank_search_results",
        "translate_text", "check_duplicate", "promote_memory_tier",
        "get_memory_age_stats", "get_tier_stats",
    }),
    "memory_write": frozenset({
        "add_memory", "remember", "save_interaction", "update_memory",
        "delete_memory", "forget_memory", "add_observation", "update_observation",
        "delete_observation", "set_memory_confidence", "set_memory_ttl",
        "set_memory_sharing", "update_importance_scores", "revert_memory",
        "improve", "encrypt_memory", "publish_memory_event", "sync_agent_state",
        "expire_memories", "archive_category", "start_session", "end_session",
        "create_shared_space",
    }),
    "ops_readonly": frozenset({
        "health", "get_stats", "get_performance_metrics", "get_prometheus_metrics",
        "get_slow_queries", "get_sync_status", "get_llm_cost_report",
        "list_tasks", "get_undo_history", "get_encryption_stats",
        "query_audit_log",
    }),
    # Deliberately NOT in any group (operator-only via direct CLI):
    # backups/restore, key rotation, schedulers, webhooks/notifications,
    # cost budget, undo/redo, and the GDPR suite.
}

ADMIN_ONLY_TOOLS: frozenset[str] = frozenset({
    "create_backup", "list_backups", "restore_backup", "verify_backup",
    "rollback_restore", "rotate_encryption_key", "schedule_deduplication",
    "schedule_summarization", "schedule_task", "cancel_task",
    "register_webhook", "disable_webhook", "list_webhooks", "test_webhook",
    "configure_discord_notifications", "configure_slack_notifications",
    "test_notification_channel", "set_cost_budget", "undo_last", "redo_last",
    "gdpr_check_consent", "gdpr_delete_user_data", "gdpr_export_user_data",
    "gdpr_list_consents", "gdpr_record_consent", "gdpr_verify_tenant_isolation",
})


def parse_selection(spec: str) -> frozenset[str]:
    """Comma-separated group names -> union of their tools."""
    names = [name.strip() for name in spec.split(",") if name.strip()]
    if not names:
        raise ValueError("tool_groups_empty_selection")
    unknown = [name for name in names if name not in TOOL_GROUPS]
    if unknown:
        raise ValueError("tool_groups_unknown:" + ",".join(unknown))
    union: set[str] = set()
    for name in names:
        union |= TOOL_GROUPS[name]
    return frozenset(union)


def apply_to_registry(registry: dict, spec: str) -> dict:
    """Prune `registry` (name -> tool) to the selection; returns a summary.

    Requires every selected tool to exist (typo guard) and at least one
    survivor. Mutates the passed dict."""
    allowed = parse_selection(spec)
    missing = sorted(allowed - registry.keys())
    if missing:
        raise ValueError("tool_groups_missing_tools:" + ",".join(missing[:8]))
    removed = [name for name in registry if name not in allowed]
    for name in removed:
        del registry[name]
    if not registry:
        raise ValueError("tool_groups_empty_registry")
    return {"selected": len(registry), "removed": len(removed),
            "groups": spec}
