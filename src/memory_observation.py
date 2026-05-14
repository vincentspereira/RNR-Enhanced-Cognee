"""
Memory Observations - Phase 12.8
==================================
EAV (Entity-Attribute-Value) structured observations stored in a dedicated
table shared_memory.observations.  Observations attach structured facts to
existing memory entries without changing the raw content column.

Table schema (auto-created on first use):

    shared_memory.observations
    +--------------+-----------+------------------------------------------+
    | Column       | Type      | Notes                                    |
    +--------------+-----------+------------------------------------------+
    | id           | UUID PK   | auto-generated                           |
    | memory_id    | TEXT      | FK reference to documents.id (logical)   |
    | agent_id     | TEXT      | defaults to "system"                     |
    | entity       | TEXT      | e.g. "user", "server", "strategy"       |
    | attribute    | TEXT      | e.g. "name", "status", "risk_level"     |
    | value        | TEXT      | the observed value                       |
    | confidence   | FLOAT     | 0.0 - 1.0, defaults to 1.0              |
    | created_at   | TIMESTAMPTZ                                         |
    | updated_at   | TIMESTAMPTZ                                         |
    +--------------+-----------+------------------------------------------+

ASCII-only output. No Unicode symbols.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# DDL executed once per process via _ensure_schema()
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS shared_memory.observations (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id   TEXT        NOT NULL,
    agent_id    TEXT        NOT NULL DEFAULT 'system',
    entity      TEXT        NOT NULL,
    attribute   TEXT        NOT NULL,
    value       TEXT        NOT NULL,
    confidence  FLOAT       DEFAULT 1.0,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
"""

_CREATE_INDEX_MEMORY_ID = (
    "CREATE INDEX IF NOT EXISTS idx_observations_memory_id "
    "ON shared_memory.observations (memory_id);"
)

_CREATE_INDEX_ENTITY = (
    "CREATE INDEX IF NOT EXISTS idx_observations_entity "
    "ON shared_memory.observations (entity);"
)


class MemoryObservationManager:
    """
    CRUD interface for EAV-style observations attached to memory entries.

    All methods degrade gracefully when the database pool is unavailable.

    Usage::

        mgr = MemoryObservationManager(postgres_pool=pool)
        await mgr._ensure_schema()

        obs_id = (await mgr.add_observation(
            memory_id="uuid-...",
            entity="user",
            attribute="preference",
            value="dark mode",
        ))["observation_id"]

        rows = await mgr.get_observations("uuid-...")
        await mgr.update_observation(obs_id, value="light mode")
        await mgr.delete_observation(obs_id)
        results = await mgr.search_observations(entity="user")
    """

    def __init__(self, postgres_pool: Any = None) -> None:
        """
        Initialize MemoryObservationManager.

        Args:
            postgres_pool: An asyncpg connection pool.  May be None; all
                           methods return error dicts or empty lists in
                           that case.
        """
        self.pool = postgres_pool
        self._schema_ready: bool = False

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------

    async def _ensure_schema(self) -> None:
        """
        Create the observations table and indexes if they do not exist.

        Idempotent - safe to call on every startup.
        Skips silently when no pool is configured.
        """
        if self._schema_ready or not self.pool:
            return

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(_CREATE_TABLE_SQL)
                await conn.execute(_CREATE_INDEX_MEMORY_ID)
                await conn.execute(_CREATE_INDEX_ENTITY)
            self._schema_ready = True
            logger.debug("shared_memory.observations schema OK")
        except Exception as exc:
            logger.error("_ensure_schema failed: %s", exc)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def add_observation(
        self,
        memory_id: str,
        entity: str,
        attribute: str,
        value: str,
        agent_id: str = "system",
        confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Insert a new EAV observation row.

        Args:
            memory_id:  ID of the parent memory entry.
            entity:     Entity name (e.g. "user", "server").
            attribute:  Attribute name (e.g. "name", "status").
            value:      Observed value string.
            agent_id:   Agent that recorded the observation.
            confidence: Confidence score in [0.0, 1.0].

        Returns:
            Dict with observation_id, entity, attribute, value, created_at
            on success, or {"error": ...} when pool is unavailable.
        """
        if not self.pool:
            return {"error": "No database pool"}

        await self._ensure_schema()

        confidence = max(0.0, min(1.0, float(confidence)))

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO shared_memory.observations
                        (memory_id, agent_id, entity, attribute, value, confidence)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id, entity, attribute, value, confidence, created_at
                    """,
                    memory_id,
                    agent_id,
                    entity,
                    attribute,
                    value,
                    confidence,
                )

            result = {
                "observation_id": str(row["id"]),
                "memory_id": memory_id,
                "entity": row["entity"],
                "attribute": row["attribute"],
                "value": row["value"],
                "confidence": float(row["confidence"]),
                "created_at": row["created_at"].isoformat(),
            }
            logger.debug(
                "add_observation OK: %s.%s=%s (memory %s)",
                entity, attribute, value, memory_id,
            )
            return result
        except Exception as exc:
            logger.error("add_observation failed: %s", exc)
            return {"error": str(exc)}

    async def get_observations(self, memory_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all observations for a given memory entry.

        Args:
            memory_id: The memory ID to look up.

        Returns:
            List of observation dicts ordered by created_at ASC.
            Empty list when pool is unavailable or no rows found.
        """
        if not self.pool:
            return []

        await self._ensure_schema()

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, memory_id, agent_id, entity, attribute,
                           value, confidence, created_at, updated_at
                      FROM shared_memory.observations
                     WHERE memory_id = $1
                     ORDER BY created_at ASC
                    """,
                    memory_id,
                )

            return [
                {
                    "observation_id": str(r["id"]),
                    "memory_id": r["memory_id"],
                    "agent_id": r["agent_id"],
                    "entity": r["entity"],
                    "attribute": r["attribute"],
                    "value": r["value"],
                    "confidence": float(r["confidence"]),
                    "created_at": r["created_at"].isoformat(),
                    "updated_at": r["updated_at"].isoformat(),
                }
                for r in rows
            ]
        except Exception as exc:
            logger.error("get_observations failed for memory %s: %s", memory_id, exc)
            return []

    async def update_observation(
        self,
        observation_id: str,
        value: str,
        confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Update the value and confidence of an existing observation.

        Args:
            observation_id: UUID of the observation row.
            value:          New value string.
            confidence:     Updated confidence score in [0.0, 1.0].

        Returns:
            Dict with observation_id and ok=True on success, or error key.
        """
        if not self.pool:
            return {"observation_id": observation_id, "error": "No database pool"}

        await self._ensure_schema()

        confidence = max(0.0, min(1.0, float(confidence)))

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE shared_memory.observations
                       SET value = $1, confidence = $2, updated_at = NOW()
                     WHERE id = $3
                    """,
                    value,
                    confidence,
                    observation_id,
                )
            updated = int(result.split()[-1]) if result else 0
            if updated == 0:
                return {"observation_id": observation_id, "error": "observation not found"}

            logger.debug("update_observation OK: %s", observation_id)
            return {"observation_id": observation_id, "ok": True}
        except Exception as exc:
            logger.error("update_observation failed for %s: %s", observation_id, exc)
            return {"observation_id": observation_id, "error": str(exc)}

    async def delete_observation(self, observation_id: str) -> Dict[str, Any]:
        """
        Delete a single observation by its ID.

        Args:
            observation_id: UUID of the observation row.

        Returns:
            Dict with observation_id and deleted=True on success, or error key.
        """
        if not self.pool:
            return {"observation_id": observation_id, "error": "No database pool"}

        await self._ensure_schema()

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM shared_memory.observations WHERE id = $1",
                    observation_id,
                )
            deleted = int(result.split()[-1]) if result else 0
            if deleted == 0:
                return {"observation_id": observation_id, "error": "observation not found"}

            logger.debug("delete_observation OK: %s", observation_id)
            return {"observation_id": observation_id, "deleted": True}
        except Exception as exc:
            logger.error("delete_observation failed for %s: %s", observation_id, exc)
            return {"observation_id": observation_id, "error": str(exc)}

    async def search_observations(
        self,
        entity: str = "",
        attribute: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Search observations by entity and/or attribute substring (ILIKE).

        Both filters are optional.  Passing empty strings disables that filter.
        Results are ordered by created_at DESC.

        Args:
            entity:    Substring to match against the entity column.
            attribute: Substring to match against the attribute column.

        Returns:
            List of matching observation dicts.
            Empty list when pool is unavailable.
        """
        if not self.pool:
            return []

        await self._ensure_schema()

        # Build dynamic WHERE clause
        conditions: list[str] = ["1=1"]
        params: list[Any] = []
        param_idx = 1

        if entity:
            conditions.append(f"entity ILIKE ${param_idx}")
            params.append(f"%{entity}%")
            param_idx += 1

        if attribute:
            conditions.append(f"attribute ILIKE ${param_idx}")
            params.append(f"%{attribute}%")
            param_idx += 1

        where_clause = " AND ".join(conditions)

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT id, memory_id, agent_id, entity, attribute,
                           value, confidence, created_at, updated_at
                      FROM shared_memory.observations
                     WHERE {where_clause}
                     ORDER BY created_at DESC
                    """,
                    *params,
                )

            return [
                {
                    "observation_id": str(r["id"]),
                    "memory_id": r["memory_id"],
                    "agent_id": r["agent_id"],
                    "entity": r["entity"],
                    "attribute": r["attribute"],
                    "value": r["value"],
                    "confidence": float(r["confidence"]),
                    "created_at": r["created_at"].isoformat(),
                    "updated_at": r["updated_at"].isoformat(),
                }
                for r in rows
            ]
        except Exception as exc:
            logger.error(
                "search_observations failed (entity=%r, attribute=%r): %s",
                entity, attribute, exc,
            )
            return []


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_instance: Optional[MemoryObservationManager] = None


def init_observation_manager(
    postgres_pool: Any = None,
) -> MemoryObservationManager:
    """
    Create and register the global MemoryObservationManager singleton.

    Args:
        postgres_pool: asyncpg connection pool.

    Returns:
        The newly created MemoryObservationManager instance.
    """
    global _instance
    _instance = MemoryObservationManager(postgres_pool=postgres_pool)
    logger.info("OK MemoryObservationManager initialized")
    return _instance


def get_observation_manager() -> Optional[MemoryObservationManager]:
    """
    Return the global MemoryObservationManager singleton.

    Returns:
        The MemoryObservationManager instance, or None if
        init_observation_manager has not been called yet.
    """
    return _instance
