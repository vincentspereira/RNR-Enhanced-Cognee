"""
Memory Provenance - Phase 10 (15.2)
=====================================
Tracks the origin, source chain, and verification status of each memory
entry.  Provenance data is stored as a JSONB column on documents and can
be queried or verified via dedicated MCP tools.

Provenance schema (stored inside documents.provenance JSONB):
{
    "source":        "user_input" | "ingest_url" | "ingest_db" | "cognify"
                     | "revert" | "consolidation" | "import" | ...,
    "source_url":    "<url>" (when source is ingest_url),
    "author":        "<agent_id or user label>",
    "ingested_at":   "<ISO timestamp>",
    "checksum":      "<sha256 hex of original content>",
    "transformations": [
        {"type": "redact_pii", "timestamp": "..."},
        {"type": "translate",  "from": "fr", "to": "en", "timestamp": "..."},
        ...
    ],
    "verified":      false,
    "verified_at":   null,
    "verified_by":   null
}
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional


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


class MemoryProvenanceTracker:
    f"""
    Read and write provenance JSONB on {_t_docs()}.
    All updates are non-destructive merges: existing keys are preserved
    unless explicitly overridden.
    """

    def __init__(self, postgres_pool: Any) -> None:
        self.pool = postgres_pool

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sha256(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def set_provenance(
        self,
        memory_id: str,
        source: str,
        agent_id: Optional[str] = None,
        source_url: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        content_for_checksum: Optional[str] = None,
    ) -> bool:
        """
        Create or replace the provenance record for a memory entry.
        Returns True on success.
        """
        if not self.pool:
            return False

        prov: Dict[str, Any] = {
            "source": source,
            "author": agent_id or "unknown",
            "ingested_at": datetime.now(UTC).isoformat(),
            "verified": False,
            "verified_at": None,
            "verified_by": None,
        }
        if source_url:
            prov["source_url"] = source_url
        if content_for_checksum:
            prov["checksum"] = self._sha256(content_for_checksum)
        if extra:
            prov.update(extra)

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    f"""
                    UPDATE {_t_docs()}
                       SET provenance = $1::jsonb, updated_at = NOW()
                     WHERE id = $2
                    """,
                    json.dumps(prov),
                    memory_id,
                )
            updated = int(result.split()[-1]) if result else 0
            return updated > 0
        except Exception as exc:
            logger.error("set_provenance failed for %s: %s", memory_id, exc)
            return False

    async def get_provenance(
        self, memory_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve the provenance JSONB for a single memory entry.
        Returns None if memory not found or pool unavailable.
        """
        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"SELECT provenance FROM {_t_docs()} WHERE id = $1",
                    memory_id,
                )
            if row is None:
                return None
            prov_raw = row["provenance"]
            if prov_raw is None:
                return {"source": "unknown", "verified": False}
            if isinstance(prov_raw, str):
                return json.loads(prov_raw)
            return dict(prov_raw)
        except Exception as exc:
            logger.error("get_provenance failed for %s: %s", memory_id, exc)
            return None

    async def add_transformation(
        self,
        memory_id: str,
        transformation_type: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Append a transformation entry to the provenance.transformations list.
        Example: redact_pii, translate, summarize, etc.
        """
        if not self.pool:
            return False

        entry: Dict[str, Any] = {
            "type": transformation_type,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if details:
            entry.update(details)

        try:
            async with self.pool.acquire() as conn:
                # Use jsonb_set to append to the transformations array atomically
                await conn.execute(
                    """
                    UPDATE shared_memory.documents
                       SET provenance = jsonb_set(
                               COALESCE(provenance, '{"transformations":[]}'::jsonb),
                               '{{transformations}}',
                               (COALESCE(provenance->'transformations', '[]'::jsonb)
                                || $1::jsonb)
                           ),
                           updated_at = NOW()
                     WHERE id = $2
                    """,
                    json.dumps([entry]),
                    memory_id,
                )
            return True
        except Exception as exc:
            logger.error(
                "add_transformation failed for %s: %s", memory_id, exc
            )
            return False

    async def mark_verified(
        self,
        memory_id: str,
        verified_by: Optional[str] = None,
    ) -> bool:
        """
        Mark the memory as provenance-verified.
        Returns True on success.
        """
        if not self.pool:
            return False

        now = datetime.now(UTC).isoformat()
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    f"""
                    UPDATE {_t_docs()}
                       SET provenance = provenance
                                      || jsonb_build_object(
                                             'verified',     true,
                                             'verified_at',  $1::text,
                                             'verified_by',  $2::text
                                         ),
                           updated_at = NOW()
                     WHERE id = $3
                    """,
                    now,
                    verified_by or "system",
                    memory_id,
                )
            return True
        except Exception as exc:
            logger.error("mark_verified failed for %s: %s", memory_id, exc)
            return False

    async def verify_checksum(self, memory_id: str) -> Dict[str, Any]:
        """
        Re-compute sha256 of documents.content and compare against
        provenance.checksum.  Returns a dict with "match" bool and details.
        """
        if not self.pool:
            return {"match": None, "error": "pool unavailable"}

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"SELECT content, provenance FROM {_t_docs()} WHERE id = $1",
                    memory_id,
                )
            if row is None:
                return {"match": None, "error": "memory not found"}

            prov_raw = row["provenance"]
            if not prov_raw:
                return {"match": None, "error": "no provenance recorded"}

            prov = json.loads(prov_raw) if isinstance(prov_raw, str) else dict(prov_raw)
            stored_checksum = prov.get("checksum")
            if not stored_checksum:
                return {"match": None, "error": "no checksum in provenance"}

            actual_checksum = self._sha256(row["content"])
            match = actual_checksum == stored_checksum
            return {
                "match": match,
                "stored_checksum": stored_checksum,
                "actual_checksum": actual_checksum,
                "memory_id": memory_id,
            }
        except Exception as exc:
            logger.error("verify_checksum failed for %s: %s", memory_id, exc)
            return {"match": None, "error": str(exc)}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_provenance_tracker: Optional[MemoryProvenanceTracker] = None


def init_provenance_tracker(postgres_pool: Any) -> MemoryProvenanceTracker:
    global _provenance_tracker
    _provenance_tracker = MemoryProvenanceTracker(postgres_pool)
    logger.info("OK MemoryProvenanceTracker initialized")
    return _provenance_tracker


def get_provenance_tracker() -> Optional[MemoryProvenanceTracker]:
    return _provenance_tracker
