"""Complete permission/effect manifest without assuming legacy purity.

Canonical adapters expose a reviewed small contract. Historical tool code has
broader dependencies; its read permission alone is not proof of no side effects.
Keep that distinction in the machine-readable policy and release inventory.
"""
from dataclasses import dataclass

from src.security import enterprise_auth as auth


@dataclass(frozen=True)
class ToolPolicy:
    permission: str
    implementation: str
    possible_effects: tuple[str, ...]
    canonical_admitted: bool
    inputs_are_untrusted: bool = True
    grants_authority_from_content: bool = False


_READS = frozenset({"search_memories", "search", "recall", "get_memories", "list_data", "get_memory",
                   "get_memory_detail", "get_memory_history", "list_agents", "get_stats", "health"})
_WRITES = frozenset({"add_memory", "remember", "update_memory"})
_RETRACTIONS = frozenset({"delete_memory", "forget_memory"})


def policy_for(tool: str, *, canonical: bool = False) -> ToolPolicy:
    if tool not in auth.TOOL_PERMISSIONS:
        raise auth.AuthError(403, "Tool has no declared permission/effect policy")
    permission = auth.TOOL_PERMISSIONS[tool].value
    admitted = tool in _READS | _WRITES | _RETRACTIONS
    if canonical:
        if not admitted:
            raise auth.AuthError(403, "This tool is outside canonical project memory")
        effects = ("authorized_record_read", "bounded_index_read") if tool in _READS else (
            "versioned_retraction", "audit_append", "derived_cleanup_event") if tool in _RETRACTIONS else (
            "canonical_record_write", "history_append", "audit_append", "index_event_append")
        return ToolPolicy(permission, "canonical_service", effects, True)
    # Conservative upper bound, not a claim that every legacy tool sends data.
    # This forces clients/release reports to distinguish a permission label
    # from a reviewed filesystem/network/model capability contract.
    return ToolPolicy(permission, "legacy_separate_qualification_required",
        ("legacy_storage", "possible_mutation", "possible_filesystem", "possible_network", "possible_model"), admitted)


def manifest() -> dict:
    from dataclasses import asdict
    return {name: {"legacy": asdict(policy_for(name)),
                   "canonical": asdict(policy_for(name, canonical=True)) if name in _READS | _WRITES | _RETRACTIONS else None}
            for name in sorted(auth.TOOL_PERMISSIONS)}
