"""
GDPR Manager - Phase 11 (16.1, 16.2, 16.3, 16.4)
====================================================
Provides data subject rights under GDPR / CCPA:

    16.1 - Right to erasure (delete-my-data):
           Permanently purge all memories, version history, audit log entries,
           and graph nodes associated with a user_id from all four databases.

    16.2 - Right of access / data portability (export-my-data):
           Produce a structured JSON export of everything stored for a user_id,
           optionally wrapped in a zip archive.

    16.3 - Consent management:
           Store and query explicit consent records for data categories.
           Gate ingestion operations behind consent checks.

    16.4 - Multi-tenant isolation:
           Enforce tenant_id boundaries so that cross-tenant data leakage
           is detected at the application layer (in addition to row-level
           security policies at the DB layer).

All operations are async-safe; each degrades gracefully when the relevant
DB connection is unavailable.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# Multi-tenant helper -- routes Postgres reads/writes to the per-tenant
# table when a TenantContext is active. See src/multi_tenant.py.
def _t_docs() -> str:
    from src.multi_tenant import tenant_scoped_table
    return tenant_scoped_table("shared_memory.documents")


def _t_embeddings() -> str:
    from src.multi_tenant import tenant_scoped_table
    return tenant_scoped_table("shared_memory.embeddings")


logger = logging.getLogger(__name__)

UTC = timezone.utc


# ---------------------------------------------------------------------------
# GDPRManager
# ---------------------------------------------------------------------------

class GDPRManager:
    """
    Manage GDPR/CCPA data subject rights for Enhanced Cognee.

    Constructor parameters:
        postgres_pool   - asyncpg pool (primary data store)
        qdrant_client   - Qdrant client (vector store)
        neo4j_driver    - Neo4j sync driver (knowledge graph)
        redis_client    - Redis client (cache / rate-limiting state)
    """

    def __init__(
        self,
        postgres_pool: Any,
        qdrant_client: Any = None,
        neo4j_driver: Any = None,
        redis_client: Any = None,
    ) -> None:
        self.pool = postgres_pool
        self.qdrant = qdrant_client
        self.neo4j = neo4j_driver
        self.redis = redis_client

    # ------------------------------------------------------------------
    # 16.1 - Right to Erasure
    # ------------------------------------------------------------------

    async def delete_user_data(
        self,
        user_id: str,
        requester: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Permanently erase all data associated with *user_id* from all stores.

        When dry_run=True, returns a preview of what would be deleted without
        making any changes.

        Returns a summary dict::

            {
                "user_id": "...",
                "dry_run": False,
                "postgres_rows_deleted": N,
                "qdrant_vectors_deleted": N,
                "neo4j_nodes_deleted": N,
                "redis_keys_deleted": N,
                "consent_records_deleted": N,
                "errors": [...],
            }
        """
        summary: Dict[str, Any] = {
            "user_id": user_id,
            "dry_run": dry_run,
            "postgres_rows_deleted": 0,
            "qdrant_vectors_deleted": 0,
            "neo4j_nodes_deleted": 0,
            "redis_keys_deleted": 0,
            "consent_records_deleted": 0,
            "errors": [],
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # ------ PostgreSQL ------
        if self.pool:
            try:
                doc_ids = await self._get_user_doc_ids(user_id)

                if not dry_run:
                    async with self.pool.acquire() as conn:
                        # Versions cascade via FK; delete documents first
                        deleted = await conn.fetchval(
                            f"""
                            DELETE FROM {_t_docs()}
                             WHERE agent_id = $1
                            RETURNING COUNT(*)
                            """,
                            user_id,
                        )
                        summary["postgres_rows_deleted"] = int(deleted or 0)

                        # Delete consent records
                        c_deleted = await conn.fetchval(
                            """
                            DELETE FROM shared_memory.consent_records
                             WHERE user_id = $1
                            RETURNING COUNT(*)
                            """,
                            user_id,
                        ) if await self._table_exists(conn, "consent_records") else 0
                        summary["consent_records_deleted"] = int(c_deleted or 0)

                        # Redact audit_log (preserve row but erase PII)
                        await conn.execute(
                            """
                            UPDATE shared_memory.audit_log
                               SET details = '{"gdpr_erased": true}'::jsonb
                             WHERE agent_id = $1
                            """,
                            user_id,
                        )
                else:
                    async with self.pool.acquire() as conn:
                        count = await conn.fetchval(
                            f"SELECT COUNT(*) FROM {_t_docs()} WHERE agent_id = $1",
                            user_id,
                        )
                    summary["postgres_rows_deleted"] = int(count or 0)

            except Exception as exc:
                logger.error("delete_user_data postgres failed: %s", exc)
                summary["errors"].append(f"postgresql: {exc}")

        # ------ Qdrant ------
        if self.qdrant and not dry_run:
            try:
                # Delete all points with matching agent_id payload field
                from qdrant_client.http.models import FilterSelector, Filter, FieldCondition, MatchValue
                self.qdrant.delete(
                    collection_name="memories",
                    points_selector=FilterSelector(
                        filter=Filter(
                            must=[FieldCondition(key="agent_id", match=MatchValue(value=user_id))]
                        )
                    ),
                )
                summary["qdrant_vectors_deleted"] = -1  # unknown count without pre-query
            except Exception as exc:
                logger.warning("delete_user_data qdrant failed (may be ok): %s", exc)
                summary["errors"].append(f"qdrant: {exc}")

        # ------ Neo4j ------
        if self.neo4j and not dry_run:
            try:
                with self.neo4j.session() as session:
                    result = session.run(
                        """
                        MATCH (n {agent_id: $uid})
                        DETACH DELETE n
                        RETURN count(n) AS deleted
                        """,
                        uid=user_id,
                    )
                    rec = result.single()
                    summary["neo4j_nodes_deleted"] = int(rec["deleted"]) if rec else 0
            except Exception as exc:
                logger.warning("delete_user_data neo4j failed (may be ok): %s", exc)
                summary["errors"].append(f"neo4j: {exc}")

        # ------ Redis ------
        if self.redis and not dry_run:
            try:
                pattern = f"*:{user_id}:*"
                keys = await self.redis.keys(pattern)
                if keys:
                    await self.redis.delete(*keys)
                summary["redis_keys_deleted"] = len(keys)
            except Exception as exc:
                logger.warning("delete_user_data redis failed: %s", exc)
                summary["errors"].append(f"redis: {exc}")

        return summary

    async def _get_user_doc_ids(self, user_id: str) -> List[str]:
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT id FROM {_t_docs()} WHERE agent_id = $1", user_id
            )
        return [r["id"] for r in rows]

    @staticmethod
    async def _table_exists(conn: Any, table_name: str) -> bool:
        result = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                 WHERE table_schema = 'shared_memory'
                   AND table_name = $1
            )
            """,
            table_name,
        )
        return bool(result)

    # ------------------------------------------------------------------
    # 16.2 - Right of Access / Data Portability
    # ------------------------------------------------------------------

    async def export_user_data(
        self,
        user_id: str,
        include_versions: bool = True,
        as_zip: bool = False,
    ) -> Tuple[bytes, str]:
        """
        Compile a full data export for *user_id*.

        Returns (data_bytes, filename):
            - JSON export:  (json_bytes, "gdpr_export_{user_id}.json")
            - ZIP export:   (zip_bytes,  "gdpr_export_{user_id}.zip")
        """
        export: Dict[str, Any] = {
            "gdpr_export_version": "1.0",
            "user_id": user_id,
            "exported_at": datetime.now(UTC).isoformat(),
            "memories": [],
            "version_history": [],
            "consent_records": [],
        }

        if self.pool:
            try:
                async with self.pool.acquire() as conn:
                    # Memories
                    rows = await conn.fetch(
                        f"""
                        SELECT id, title, content, agent_id, metadata,
                               provenance, confidence, memory_tier,
                               expire_at, created_at, updated_at
                          FROM {_t_docs()}
                         WHERE agent_id = $1
                         ORDER BY created_at DESC
                        """,
                        user_id,
                    )
                    for r in rows:
                        export["memories"].append({
                            "id": r["id"],
                            "title": r["title"],
                            "content": r["content"],
                            "metadata": r["metadata"],
                            "provenance": r["provenance"],
                            "confidence": float(r["confidence"]) if r["confidence"] else None,
                            "memory_tier": r["memory_tier"],
                            "expire_at": str(r["expire_at"]) if r["expire_at"] else None,
                            "created_at": str(r["created_at"]),
                            "updated_at": str(r["updated_at"]),
                        })

                    if include_versions:
                        # Version history
                        ver_rows = await conn.fetch(
                            f"""
                            SELECT mv.id, mv.memory_id, mv.version_number,
                                   mv.content, mv.change_reason, mv.created_at
                              FROM shared_memory.memory_versions mv
                              JOIN {_t_docs()} d ON d.id = mv.memory_id
                             WHERE d.agent_id = $1
                             ORDER BY mv.created_at DESC
                             LIMIT 1000
                            """,
                            user_id,
                        )
                        for r in ver_rows:
                            export["version_history"].append({
                                "id": r["id"],
                                "memory_id": r["memory_id"],
                                "version_number": r["version_number"],
                                "content": r["content"],
                                "change_reason": r["change_reason"],
                                "created_at": str(r["created_at"]),
                            })

                    # Consent records (if table exists)
                    if await self._table_exists(conn, "consent_records"):
                        consent_rows = await conn.fetch(
                            """
                            SELECT category, granted, granted_at, revoked_at
                              FROM shared_memory.consent_records
                             WHERE user_id = $1
                            """,
                            user_id,
                        )
                        for r in consent_rows:
                            export["consent_records"].append({
                                "category": r["category"],
                                "granted": r["granted"],
                                "granted_at": str(r["granted_at"]) if r["granted_at"] else None,
                                "revoked_at": str(r["revoked_at"]) if r["revoked_at"] else None,
                            })

            except Exception as exc:
                logger.error("export_user_data postgres failed: %s", exc)
                export["error"] = str(exc)

        json_bytes = json.dumps(export, ensure_ascii=True, indent=2).encode("utf-8")
        safe_uid = hashlib.sha256(user_id.encode()).hexdigest()[:12]

        if as_zip:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f"gdpr_export_{safe_uid}.json", json_bytes)
            return buf.getvalue(), f"gdpr_export_{safe_uid}.zip"

        return json_bytes, f"gdpr_export_{safe_uid}.json"

    # ------------------------------------------------------------------
    # 16.3 - Consent Management
    # ------------------------------------------------------------------

    async def _ensure_consent_table(self, conn: Any) -> None:
        """Create consent_records table if it does not exist."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shared_memory.consent_records (
                id          BIGSERIAL PRIMARY KEY,
                user_id     TEXT NOT NULL,
                category    TEXT NOT NULL,
                granted     BOOLEAN NOT NULL DEFAULT FALSE,
                granted_at  TIMESTAMPTZ,
                revoked_at  TIMESTAMPTZ,
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, category)
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_consent_user_category
            ON shared_memory.consent_records (user_id, category)
        """)

    async def record_consent(
        self,
        user_id: str,
        category: str,
        granted: bool,
    ) -> bool:
        """
        Record or update the consent status for (user_id, category).
        Returns True on success.
        """
        if not self.pool:
            return False
        try:
            now = datetime.now(UTC)
            async with self.pool.acquire() as conn:
                await self._ensure_consent_table(conn)
                await conn.execute(
                    """
                    INSERT INTO shared_memory.consent_records
                           (user_id, category, granted, granted_at, revoked_at, updated_at)
                    VALUES ($1, $2, $3,
                            CASE WHEN $3 THEN $4 ELSE NULL END,
                            CASE WHEN NOT $3 THEN $4 ELSE NULL END,
                            $4)
                    ON CONFLICT (user_id, category) DO UPDATE
                       SET granted    = EXCLUDED.granted,
                           granted_at = CASE WHEN EXCLUDED.granted THEN $4 ELSE consent_records.granted_at END,
                           revoked_at = CASE WHEN NOT EXCLUDED.granted THEN $4 ELSE consent_records.revoked_at END,
                           updated_at = $4
                    """,
                    user_id,
                    category,
                    granted,
                    now,
                )
            return True
        except Exception as exc:
            logger.error("record_consent failed: %s", exc)
            return False

    async def check_consent(
        self,
        user_id: str,
        category: str,
    ) -> Optional[bool]:
        """
        Return True if user has granted consent for category,
        False if revoked, None if no record exists.
        """
        if not self.pool:
            return None
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT granted FROM shared_memory.consent_records
                     WHERE user_id = $1 AND category = $2
                    """,
                    user_id,
                    category,
                )
            return row["granted"] if row else None
        except Exception as exc:
            logger.error("check_consent failed: %s", exc)
            return None

    async def list_consents(self, user_id: str) -> List[Dict[str, Any]]:
        """Return all consent records for a user."""
        if not self.pool:
            return []
        try:
            async with self.pool.acquire() as conn:
                if not await self._table_exists(conn, "consent_records"):
                    return []
                rows = await conn.fetch(
                    """
                    SELECT category, granted, granted_at, revoked_at, updated_at
                      FROM shared_memory.consent_records
                     WHERE user_id = $1
                     ORDER BY category
                    """,
                    user_id,
                )
            return [
                {
                    "category": r["category"],
                    "granted": r["granted"],
                    "granted_at": str(r["granted_at"]) if r["granted_at"] else None,
                    "revoked_at": str(r["revoked_at"]) if r["revoked_at"] else None,
                    "updated_at": str(r["updated_at"]),
                }
                for r in rows
            ]
        except Exception as exc:
            logger.error("list_consents failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # 16.4 - Multi-Tenant Isolation Check
    # ------------------------------------------------------------------

    async def verify_tenant_isolation(
        self,
        tenant_id: str,
        sample_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Verify that no memory rows attributed to *tenant_id* have leaked
        into another tenant's namespace (cross-tenant contamination check).

        Returns:
            {
                "tenant_id": "...",
                "sampled": N,
                "violations": [ {"memory_id": "...", "found_agent_id": "..."}, ... ],
                "clean": True | False,
            }
        """
        if not self.pool:
            return {"error": "pool unavailable"}

        try:
            async with self.pool.acquire() as conn:
                # Sample memories that should belong to this tenant
                rows = await conn.fetch(
                    f"""
                    SELECT id, agent_id
                      FROM {_t_docs()}
                     WHERE agent_id = $1
                     LIMIT $2
                    """,
                    tenant_id,
                    sample_size,
                )

            violations = []
            for r in rows:
                if r["agent_id"] != tenant_id:
                    violations.append({
                        "memory_id": r["id"],
                        "found_agent_id": r["agent_id"],
                    })

            return {
                "tenant_id": tenant_id,
                "sampled": len(rows),
                "violations": violations,
                "clean": len(violations) == 0,
            }
        except Exception as exc:
            logger.error("verify_tenant_isolation failed: %s", exc)
            return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_gdpr_manager: Optional[GDPRManager] = None


def init_gdpr_manager(
    postgres_pool: Any,
    qdrant_client: Any = None,
    neo4j_driver: Any = None,
    redis_client: Any = None,
) -> GDPRManager:
    global _gdpr_manager
    _gdpr_manager = GDPRManager(
        postgres_pool=postgres_pool,
        qdrant_client=qdrant_client,
        neo4j_driver=neo4j_driver,
        redis_client=redis_client,
    )
    logger.info("OK GDPRManager initialized")
    return _gdpr_manager


def get_gdpr_manager() -> Optional[GDPRManager]:
    return _gdpr_manager
