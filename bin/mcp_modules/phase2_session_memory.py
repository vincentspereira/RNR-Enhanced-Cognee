"""
bin/mcp_modules/phase2_session_memory.py
=========================================
Phase 2 MCP Tools: Session-Aware Memory + Knowledge Graph Search

Tools in this module (6):
  - remember         : Store data with session context
  - recall           : Search KG with 15 search strategies
  - forget_memory    : Delete graph data
  - improve          : Run 4-stage feedback improvement pipeline
  - save_interaction : Save coding interaction for rule learning
  - cognify_status   : Check background task status

Source in monolith: bin/enhanced_cognee_mcp_server.py lines 4031-4378

NOTE: This module is the CANONICAL reference for Phase 2 tools.
      The monolith still defines these tools inline (to avoid double-registration).
      Future migration: remove inline definitions from monolith and call register(mcp) here.

ASCII-ONLY output constraint: no Unicode symbols per CLAUDE.md.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Valid search types from cognee v1.0.9 SearchType enum
VALID_SEARCH_TYPES = {
    "SUMMARIES", "CHUNKS", "RAG_COMPLETION", "TRIPLET_COMPLETION",
    "GRAPH_COMPLETION", "GRAPH_COMPLETION_DECOMPOSITION", "GRAPH_SUMMARY_COMPLETION",
    "CYPHER", "NATURAL_LANGUAGE", "GRAPH_COMPLETION_COT",
    "GRAPH_COMPLETION_CONTEXT_EXTENSION", "FEELING_LUCKY",
    "TEMPORAL", "CODING_RULES", "CHUNKS_LEXICAL",
}

# Background task registry (module-level; shared when using register() pattern)
_cognify_tasks: dict = {}


def register(mcp: "FastMCP") -> None:
    """Register all Phase 2 tools with the given FastMCP instance."""

    @mcp.tool()
    async def remember(
        data: str,
        dataset_name: str = "main_dataset",
        session_id: Optional[str] = None,
        run_in_background: bool = False,
    ) -> str:
        """
        Store data into the cognee knowledge graph (session-aware ingestion).

        This is the v1.0.9 remember() API - richer than cognify() because it
        supports session context, self-improvement feedback, and typed memory
        entries (QA, Trace, Feedback). Use cognify() for simple document storage.

        TRIGGER TYPE: (A) Auto - AI IDE triggers this based on conversation context.
        WHEN TO CALL: Call automatically when the user says "remember this", "save this",
        "note that", "keep this in mind", or when the user shares knowledge they will
        likely need later (project decisions, preferences, facts, meeting notes, code
        patterns). Do NOT call for transient conversational messages.

        Parameters:
        -----------
        - data: Text, URL, or structured content to store
        - dataset_name: Target dataset name (default: 'main_dataset')
        - session_id: Optional session ID to associate this memory with a conversation
        - run_in_background: If True, returns immediately with a task ID

        Returns:
        --------
        - Status string with task ID if background mode, else completion status
        """
        try:
            from cognee.api.v1.remember.remember import remember as cognee_remember

            if run_in_background:
                task_id = f"remember_{len(_cognify_tasks) + 1}"
                _cognify_tasks[task_id] = "running"

                async def _run() -> None:
                    try:
                        await cognee_remember(
                            data=data,
                            dataset_name=dataset_name,
                            session_id=session_id,
                            run_in_background=False,
                        )
                        _cognify_tasks[task_id] = "completed"
                    except Exception as exc:
                        _cognify_tasks[task_id] = f"failed: {exc}"

                asyncio.create_task(_run())
                return f"OK remember task started in background (task_id: {task_id})"

            await cognee_remember(
                data=data,
                dataset_name=dataset_name,
                session_id=session_id,
            )
            return f"OK Data stored in dataset '{dataset_name}'" + (
                f" (session: {session_id})" if session_id else ""
            )

        except Exception as exc:
            logger.error(f"remember failed: {exc}")
            return f"ERR remember failed: {exc}"

    @mcp.tool()
    async def recall(
        query: str,
        search_type: str = "GRAPH_COMPLETION",
        dataset_name: Optional[str] = None,
        session_id: Optional[str] = None,
        top_k: int = 10,
    ) -> str:
        """
        Search the cognee knowledge graph with 15 available search strategies.

        Available search_type values:
        - GRAPH_COMPLETION         : LLM-augmented graph traversal (recommended default)
        - GRAPH_COMPLETION_COT     : Chain-of-thought graph reasoning
        - GRAPH_COMPLETION_DECOMPOSITION : Decompose query into sub-questions
        - GRAPH_COMPLETION_CONTEXT_EXTENSION : Extend context along graph edges
        - GRAPH_SUMMARY_COMPLETION : Search graph-level summaries
        - SUMMARIES                : Document and chunk summaries
        - CHUNKS                   : Raw text chunk retrieval
        - CHUNKS_LEXICAL           : BM25-style lexical chunk search
        - RAG_COMPLETION           : Retrieval-augmented generation
        - TRIPLET_COMPLETION       : Knowledge triplet retrieval
        - NATURAL_LANGUAGE         : Natural language query parser
        - TEMPORAL                 : Time-aware knowledge retrieval
        - CODING_RULES             : Retrieve coding rules and patterns
        - CYPHER                   : Direct Cypher query against graph
        - FEELING_LUCKY            : Auto-select best strategy for query

        TRIGGER TYPE: (A) Auto - AI IDE triggers this based on conversation context.
        WHEN TO CALL: Call automatically when the user asks "what did we decide about X?",
        "what do you know about Y?", or any question that may be answered from stored
        knowledge. Prefer recall over search_memories for structured knowledge graph queries.

        Parameters:
        -----------
        - query: Search query text
        - search_type: Strategy name (see above, default: GRAPH_COMPLETION)
        - dataset_name: Optional dataset to scope the search
        - session_id: Optional session ID for session-scoped recall
        - top_k: Maximum results to return (default: 10)

        Returns:
        --------
        - Formatted search results with content and source references
        """
        search_type_upper = search_type.upper()
        if search_type_upper not in VALID_SEARCH_TYPES:
            valid = ", ".join(sorted(VALID_SEARCH_TYPES))
            return f"ERR Invalid search_type '{search_type}'. Valid: {valid}"

        try:
            from cognee.api.v1.search.search import search as cognee_search
            from cognee.modules.search.methods.get_search_type_retriever_instance import SearchType

            s_type = SearchType[search_type_upper]
            datasets = [dataset_name] if dataset_name else None
            results = await cognee_search(
                query_text=query,
                query_type=s_type,
                datasets=datasets,
                top_k=top_k,
            )

            if not results:
                return f"OK No results found for query: '{query}' (strategy: {search_type_upper})"

            lines = [f"OK {len(results)} result(s) (strategy: {search_type_upper}):\n"]
            for i, item in enumerate(results[:top_k], 1):
                if isinstance(item, dict):
                    content = item.get("text") or item.get("content") or str(item)
                    score = item.get("score") or item.get("relevance_score", "")
                    score_str = f" | score: {score:.3f}" if isinstance(score, float) else ""
                    lines.append(f"{i}. {content[:200].strip()}{score_str}")
                else:
                    lines.append(f"{i}. {str(item)[:200]}")
            return "\n".join(lines)

        except Exception as exc:
            logger.error(f"recall failed: {exc}")
            return f"ERR recall failed: {exc}"

    @mcp.tool()
    async def forget_memory(
        data_id: Optional[str] = None,
        dataset: Optional[str] = None,
        everything: bool = False,
    ) -> str:
        """
        Remove data from the cognee knowledge graph.

        Note: This operates on the cognee graph (not Enhanced PostgreSQL memories).
        To delete an Enhanced memory entry, use delete_memory() instead.

        TRIGGER TYPE: (M) Manual - triggered by explicit user deletion request

        Parameters:
        -----------
        - data_id: UUID of a specific data item to forget
        - dataset: Dataset name or UUID to forget entirely
        - everything: If True, wipe all graph data (requires dataset=None and data_id=None)

        Returns:
        --------
        - Status message confirming deletion
        """
        if everything and (data_id or dataset):
            return "ERR Cannot combine everything=True with data_id or dataset"
        if not everything and not data_id and not dataset:
            return "ERR Provide data_id, dataset, or set everything=True"

        try:
            from cognee.api.v1.forget.forget import forget as cognee_forget
            from uuid import UUID as _UUID

            parsed_id = None
            if data_id:
                try:
                    parsed_id = _UUID(data_id)
                except ValueError:
                    return f"ERR data_id must be a valid UUID, got: {data_id}"

            await cognee_forget(data_id=parsed_id, dataset=dataset, everything=everything)

            if everything:
                return "OK All graph data deleted"
            if data_id:
                return f"OK Data item {data_id} deleted from knowledge graph"
            return f"OK Dataset '{dataset}' deleted from knowledge graph"

        except Exception as exc:
            logger.error(f"forget_memory failed: {exc}")
            return f"ERR forget_memory failed: {exc}"

    @mcp.tool()
    async def improve(
        dataset: str = "main_dataset",
        session_ids: Optional[str] = None,
        run_in_background: bool = False,
    ) -> str:
        """
        Run the 4-stage feedback improvement pipeline on a dataset.

        This is cognee v1.0.9's improve() API. It applies:
          Stage 1: Extract feedback QAs from sessions
          Stage 2: Apply feedback weights to graph edges
          Stage 3: Persist session data to permanent graph
          Stage 4: Sync enriched graph back to session cache

        TRIGGER TYPE: (S) System - Automatically scheduled via Phase 8b auto_scheduler config.
        Enable with: {"auto_scheduler": {"improve": {"enabled": true}}}
        in .enhanced-cognee-config.json. Also callable manually.

        Parameters:
        -----------
        - dataset: Dataset name to improve (default: 'main_dataset')
        - session_ids: Comma-separated session IDs to use as feedback source
        - run_in_background: If True, returns immediately with a task ID

        Returns:
        --------
        - Completion status or background task ID
        """
        try:
            from cognee.api.v1.improve.improve import improve as cognee_improve

            parsed_sessions = None
            if session_ids:
                parsed_sessions = [s.strip() for s in session_ids.split(",") if s.strip()]

            if run_in_background:
                task_id = f"improve_{len(_cognify_tasks) + 1}"
                _cognify_tasks[task_id] = "running"

                async def _run() -> None:
                    try:
                        await cognee_improve(
                            dataset=dataset,
                            session_ids=parsed_sessions,
                            run_in_background=False,
                        )
                        _cognify_tasks[task_id] = "completed"
                    except Exception as exc:
                        _cognify_tasks[task_id] = f"failed: {exc}"

                asyncio.create_task(_run())
                return f"OK improve task started in background (task_id: {task_id})"

            await cognee_improve(dataset=dataset, session_ids=parsed_sessions)
            sessions_str = f" using sessions [{session_ids}]" if session_ids else ""
            return (
                f"OK Knowledge improvement pipeline complete for dataset '{dataset}'{sessions_str}"
            )

        except Exception as exc:
            logger.error(f"improve failed: {exc}")
            return f"ERR improve failed: {exc}"

    @mcp.tool()
    async def save_interaction(
        data: str,
        dataset_name: str = "main_dataset",
    ) -> str:
        """
        Save a coding interaction (user/assistant exchange) to the knowledge graph.

        This enables Claude Code / Cursor / Windsurf to record interaction patterns
        so they can be surfaced as rules and best practices via recall(search_type=CODING_RULES).

        TRIGGER TYPE: (A) Auto - trigger after significant user/assistant exchanges

        Format for data (recommended):
          'user: <user message>\\nassistant: <assistant response>'

        Parameters:
        -----------
        - data: The interaction text (user + assistant turn)
        - dataset_name: Target dataset (default: 'main_dataset')

        Returns:
        --------
        - Status confirming the interaction was saved
        """
        try:
            from cognee.api.v1.add.add import add as cognee_add
            from cognee.api.v1.cognify.cognify import cognify as cognee_cognify

            await cognee_add(data=data, dataset_name=dataset_name)
            await cognee_cognify(datasets=[dataset_name])
            return f"OK Interaction saved to dataset '{dataset_name}'"

        except Exception as exc:
            logger.error(f"save_interaction failed: {exc}")
            return f"ERR save_interaction failed: {exc}"

    @mcp.tool()
    async def cognify_status(dataset_name: Optional[str] = None) -> str:
        """
        Check the status of background cognify / remember / improve tasks.

        Parameters:
        -----------
        - dataset_name: Optional dataset name filter (reserved for future use)

        Returns:
        --------
        - Status of all tracked background tasks
        """
        if not _cognify_tasks:
            return "OK No background tasks recorded"

        lines = [f"OK Background task status ({len(_cognify_tasks)} task(s)):\n"]
        for task_id, status in list(_cognify_tasks.items())[-20:]:
            lines.append(f"  {task_id}: {status}")
        return "\n".join(lines)
