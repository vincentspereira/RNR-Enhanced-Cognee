"""
Enhanced Cognee - Session Manager

Manages Claude Code sessions for multi-prompt context continuity.
Provides session lifecycle management and context injection.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manager for Claude Code sessions.

    Handles session lifecycle, context injection, and summaries.
    """

    def __init__(self, db_pool, llm_client=None):
        """
        Initialize session manager.

        Args:
            db_pool: PostgreSQL connection pool
            llm_client: Optional LLM client for summaries
        """
        self.db_pool = db_pool
        self.llm_client = llm_client
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    async def start_session(
        self,
        user_id: str = "default",
        agent_id: str = "claude-code",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new session.

        Args:
            user_id: User identifier
            agent_id: Agent identifier
            metadata: Optional session metadata

        Returns:
            Session ID (UUID)
        """
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        metadata_json = json.dumps(metadata or {})

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO shared_memory.sessions (id, user_id, agent_id, start_time, metadata)
                VALUES ($1, $2, $3, $4, $5)
            """, session_id, user_id, agent_id, now, metadata_json)

        # Cache in memory
        self.active_sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "agent_id": agent_id,
            "start_time": now.isoformat(),
            "metadata": metadata or {}
        }

        logger.info(f"Started session: {session_id} for user={user_id}, agent={agent_id}")

        return session_id

    async def end_session(
        self,
        session_id: str,
        summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        End a session and optionally generate summary.

        Args:
            session_id: Session ID to end
            summary: Optional pre-generated summary

        Returns:
            Session information dict
        """
        # Check if session exists
        session = await self.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return {"error": "Session not found"}

        if session.get("end_time"):
            logger.warning(f"Session already ended: {session_id}")
            return session

        # Generate summary if not provided
        if not summary and self.llm_client:
            summary = await self.generate_session_summary(session_id)

        # End the session
        now = datetime.now(timezone.utc)
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE shared_memory.sessions
                SET end_time = $1, summary = $2
                WHERE id = $3
            """, now, summary, session_id)

        # Remove from active cache
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

        logger.info(f"Ended session: {session_id}")

        # Return updated session info
        return await self.get_session(session_id)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information.

        Args:
            session_id: Session ID

        Returns:
            Session dict or None if not found
        """
        # Check cache first
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, user_id, agent_id, start_time, end_time,
                       summary, metadata, created_at, updated_at
                FROM shared_memory.sessions
                WHERE id = $1
            """, session_id)

        if not row:
            return None

        return {
            "session_id": str(row["id"]),
            "user_id": row["user_id"],
            "agent_id": row["agent_id"],
            "start_time": row["start_time"].isoformat(),
            "end_time": row["end_time"].isoformat() if row["end_time"] else None,
            "summary": row["summary"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat()
        }

    async def get_session_context(
        self,
        session_id: str,
        include_memories: bool = True,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get full context from a session.

        Args:
            session_id: Session ID
            include_memories: Whether to include associated memories
            limit: Optional limit on number of memories

        Returns:
            Session context dict
        """
        session = await self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        context = {
            "session": session,
            "memories": []
        }

        if include_memories:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT id, data_text, data_type, created_at, metadata
                    FROM shared_memory.documents
                    WHERE session_id = $1
                    ORDER BY created_at ASC
                """
                if limit:
                    query += f" LIMIT {limit}"

                rows = await conn.fetch(query, session_id)

            context["memories"] = [
                {
                    "memory_id": str(row["id"]),
                    "content": row["data_text"],
                    "data_type": row["data_type"],
                    "created_at": row["created_at"].isoformat(),
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                }
                for row in rows
            ]

        return context

    async def get_recent_sessions(
        self,
        user_id: str = "default",
        agent_id: str = "claude-code",
        limit: int = 5,
        active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get recent sessions for a user/agent.

        Args:
            user_id: User identifier
            agent_id: Agent identifier
            limit: Maximum number of sessions
            active_only: Only return active sessions

        Returns:
            List of session dicts
        """
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT id, user_id, agent_id, start_time, end_time,
                       summary, created_at, updated_at
                FROM shared_memory.sessions
                WHERE user_id = $1 AND agent_id = $2
            """
            params = [user_id, agent_id]

            if active_only:
                query += " AND end_time IS NULL"

            query += " ORDER BY start_time DESC LIMIT $" + str(len(params) + 1)
            params.append(limit)

            rows = await conn.fetch(query, *params)

        return [
            {
                "session_id": str(row["id"]),
                "user_id": row["user_id"],
                "agent_id": row["agent_id"],
                "start_time": row["start_time"].isoformat(),
                "end_time": row["end_time"].isoformat() if row["end_time"] else None,
                "summary": row["summary"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat()
            }
            for row in rows
        ]

    async def get_active_session(
        self,
        user_id: str = "default",
        agent_id: str = "claude-code"
    ) -> Optional[str]:
        """
        Get the most recent active session for a user/agent.

        Args:
            user_id: User identifier
            agent_id: Agent identifier

        Returns:
            Session ID or None if no active session
        """
        sessions = await self.get_recent_sessions(
            user_id=user_id,
            agent_id=agent_id,
            limit=1,
            active_only=True
        )

        if sessions:
            return sessions[0]["session_id"]
        return None

    async def add_memory_to_session(
        self,
        session_id: str,
        memory_id: str
    ) -> bool:
        """
        Associate a memory with a session.

        Args:
            session_id: Session ID
            memory_id: Memory/document ID

        Returns:
            True if successful
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE shared_memory.documents
                    SET session_id = $1
                    WHERE id = $2
                """, session_id, memory_id)

            logger.debug(f"Associated memory {memory_id} with session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to associate memory with session: {e}")
            return False

    async def generate_session_summary(self, session_id: str) -> Optional[str]:
        """
        Generate LLM-based summary of session.

        Args:
            session_id: Session ID

        Returns:
            Generated summary or None
        """
        if not self.llm_client:
            logger.warning("No LLM client available for summary generation")
            return None

        # Get session context
        context = await self.get_session_context(session_id, include_memories=True)

        if not context.get("memories"):
            return "Empty session - no memories to summarize"

        # Build summary prompt
        memories_text = "\n\n".join([
            f"- {m['content'][:200]}..."  # Truncate for token efficiency
            for m in context["memories"][:20]  # Limit to 20 memories
        ])

        prompt = f"""Summarize the following Claude Code session in 2-3 sentences.

Session Memories:
{memories_text}

Provide a concise summary of what was discussed and accomplished."""

        try:
            # Call LLM for summary
            summary = await self.llm_client.summarize(
                prompt,
                max_tokens=150,
                temperature=0.3
            )

            return summary

        except Exception as e:
            logger.error(f"Failed to generate session summary: {e}")
            return None

    async def cleanup_stale_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up stale sessions (automatically end old active sessions).

        Args:
            max_age_hours: Maximum age in hours before auto-ending

        Returns:
            Number of sessions cleaned up
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE shared_memory.sessions
                SET end_time = NOW(), updated_at = NOW()
                WHERE end_time IS NULL
                  AND start_time < $1
            """, cutoff_time)

            count = result.split(" ")[-1] if " " in result else 0
            try:
                count = int(count)
            except ValueError:
                count = 0

        if count > 0:
            logger.info(f"Cleaned up {count} stale sessions")

        return count

    async def get_session_stats(
        self,
        user_id: str = "default",
        agent_id: str = "claude-code"
    ) -> Dict[str, Any]:
        """
        Get session statistics for a user/agent.

        Args:
            user_id: User identifier
            agent_id: Agent identifier

        Returns:
            Statistics dict
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    COUNT(*) AS total_sessions,
                    COUNT(*) FILTER (WHERE end_time IS NULL) AS active_sessions,
                    COUNT(*) FILTER (WHERE end_time IS NOT NULL) AS completed_sessions,
                    AVG(EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time)) / 60) AS avg_duration_minutes,
                    MAX(start_time) AS last_session_start
                FROM shared_memory.sessions
                WHERE user_id = $1 AND agent_id = $2
            """, user_id, agent_id)

        return {
            "total_sessions": row["total_sessions"] or 0,
            "active_sessions": row["active_sessions"] or 0,
            "completed_sessions": row["completed_sessions"] or 0,
            "avg_duration_minutes": round(float(row["avg_duration_minutes"] or 0), 2),
            "last_session_start": row["last_session_start"].isoformat() if row["last_session_start"] else None
        }


class ContextInjector:
    """
    Context injection system for Claude Code.

    Automatically injects relevant session context into prompts.
    """

    def __init__(self, session_manager: SessionManager):
        """
        Initialize context injector.

        Args:
            session_manager: Session manager instance
        """
        self.session_manager = session_manager

    async def inject_context(
        self,
        session_id: str,
        max_tokens: int = 2000,
        recent_only: bool = False
    ) -> str:
        """
        Inject session context for Claude Code.

        Args:
            session_id: Session ID
            max_tokens: Maximum tokens for context
            recent_only: Only include recent memories

        Returns:
            Formatted context string
        """
        context = await self.session_manager.get_session_context(
            session_id,
            include_memories=True
        )

        if not context or "error" in context:
            return ""

        memories = context.get("memories", [])

        if not memories:
            return ""

        # Build context string
        context_parts = [
            f"<context>",
            f"<session_id>{session_id}</session_id>",
            f"<session_start>{context['session']['start_time']}</session_start>"
        ]

        # Add memories (token-limited)
        current_tokens = 0
        estimated_chars_per_token = 4
        max_chars = max_tokens * estimated_chars_per_token

        context_parts.append("<memories>")
        for memory in memories:
            memory_text = memory["content"][:500]  # Truncate long memories
            memory_entry = f"<memory id='{memory['memory_id']}' type='{memory['data_type']}'>{memory_text}</memory>"

            if current_tokens + len(memory_entry) > max_chars:
                break

            context_parts.append(memory_entry)
            current_tokens += len(memory_entry)

        context_parts.append("</memories>")
        context_parts.append("</context>")

        return "\n".join(context_parts)

    async def inject_recent_context(
        self,
        user_id: str = "default",
        agent_id: str = "claude-code",
        num_sessions: int = 3
    ) -> str:
        """
        Inject context from recent sessions.

        Args:
            user_id: User identifier
            agent_id: Agent identifier
            num_sessions: Number of recent sessions to include

        Returns:
            Formatted context string
        """
        sessions = await self.session_manager.get_recent_sessions(
            user_id=user_id,
            agent_id=agent_id,
            limit=num_sessions,
            active_only=False
        )

        if not sessions:
            return ""

        context_parts = ["<recent_sessions>"]

        for session in sessions:
            session_id = session["session_id"]
            session_context = await self.session_manager.get_session_context(
                session_id,
                include_memories=True,
                limit=5  # Only 5 memories per session
            )

            if session_context.get("memories"):
                context_parts.append(f"<session id='{session_id}'>")
                for memory in session_context["memories"][:5]:
                    context_parts.append(f"<memory>{memory['content'][:200]}...</memory>")
                context_parts.append(f"</session>")

        context_parts.append("</recent_sessions>")

        return "\n".join(context_parts)


async def main():
    """Test session manager."""
    import asyncpg

    # Mock database pool (for testing)
    # In real usage, this would be a real connection pool
    print("Session manager test requires database connection")
    print("Use with real PostgreSQL connection pool")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
