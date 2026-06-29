# ADR-004: MCP Tool Trigger Type Classification (M / A / S)

**Status:** Accepted
**Date:** 2026-02-01
**Deciders:** RNR Enhanced Cognee maintainers

---

## Context

RNR Enhanced Cognee exposes approximately 58 MCP tools to Claude Code and other MCP
clients. The tools range from lightweight read operations (health, get_stats) to
irreversible destructive operations (gdpr_delete_user_data, rollback_restore,
forget_memory).

IDE integrations that use AI-assisted automation (such as Claude Code's background
agent mode) may call MCP tools proactively when they believe a tool is relevant to
the current task. Without classification, an automated agent could invoke
gdpr_delete_user_data or rollback_restore without explicit human instruction, which
would cause unrecoverable data loss.

A consistent, machine-readable classification embedded directly in each tool's
docstring allows any caller -- human or automated agent -- to inspect intent before
invoking.

---

## Decision

Every MCP tool function must include a TRIGGER TYPE declaration in its docstring,
immediately following the one-line summary:

    TRIGGER TYPE: (M) Manual     -- requires explicit human instruction
    TRIGGER TYPE: (A) Auto       -- safe for agent use without confirmation
    TRIGGER TYPE: (S) System     -- called by the scheduler or server internals

Guidelines for assignment:

- (A) Auto: read-only operations; operations that add data without deleting anything;
  operations whose effects are fully reversible by another tool.
- (M) Manual: any operation that deletes, purges, overwrites, or modifies data in a
  way that cannot be undone by a single subsequent call; any operation requiring
  user identity verification (GDPR tools); any backup restore.
- (S) System: tools designed for scheduled invocation (maintenance_scheduler,
  scheduled_deduplication, scheduled_summarization) or server-internal housekeeping.

Example:

    async def gdpr_delete_user_data(user_id: str, dry_run: bool = True):
        """
        Permanently erase all data for user_id from all four databases.

        TRIGGER TYPE: (M) Manual -- irreversible without a prior backup.
        ...
        """

---

## Consequences

**Positive**
- Automated agents can read TRIGGER TYPE before calling and skip or defer (M) tools.
- The classification is co-located with the implementation, so it stays current as
  the tool evolves.
- New contributors see the pattern on existing tools and follow it for new ones.
- No separate manifest file to keep synchronized with the code.

**Negative**
- Enforcement is by convention and code review, not by a runtime check. A tool
  with an incorrect trigger type will not be caught automatically.
- Adds one line to every docstring. For tools with brief docstrings this increases
  the docstring-to-code ratio noticeably.

---

## Alternatives Considered

**Separate tool manifest JSON**
A single JSON file listing every tool name and its trigger type. Rejected because
it is a second artifact to maintain and will drift from the implementation when
tools are renamed or added.

**No classification (status quo)**
Leave trigger type decisions to the calling agent's judgment. Rejected because
agents have no reliable way to distinguish safe reads from destructive writes based
on tool names alone.
