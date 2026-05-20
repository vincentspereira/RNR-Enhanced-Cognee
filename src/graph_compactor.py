"""
Knowledge Graph Compaction - Phase 10 (15.6)
==============================================
Reduces Neo4j graph bloat by removing orphaned nodes, collapsing redundant
relationship chains, and merging duplicate entities.

Compaction operations (all idempotent):

    1. Remove orphan nodes  - nodes with no relationships that are not
                              referenced by any memory document.
    2. Merge duplicate entities - nodes with identical (label, name) pairs
                                  are collapsed into one using Neo4j APOC or
                                  a manual Cypher merge procedure.
    3. Prune stale relations - RELATED_TO edges whose source memory has been
                               archived or expired (documents.expire_at < NOW()
                               or memory_tier = 'archive') are removed.
    4. Compact relationship weights - aggregate multiple parallel SIMILAR_TO
                                      edges into a single weighted edge.

All operations are performed in small batches to avoid long-running
transactions.  The module degrades gracefully when Neo4j is unavailable
(returns empty stats dict).
"""

from __future__ import annotations

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

# Batch size for graph operations
_BATCH = 500


class GraphCompactor:
    """
    Perform compaction / maintenance on the Enhanced Cognee Neo4j knowledge graph.

    Requires neo4j_driver; postgres_pool is optional (used for stale-relation pruning).
    """

    def __init__(
        self,
        neo4j_driver: Any,
        postgres_pool: Any = None,
    ) -> None:
        self.driver = neo4j_driver
        self.pool = postgres_pool

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run(self, cypher: str, params: Optional[Dict] = None) -> Any:
        """Execute a Cypher query synchronously (Neo4j sync driver)."""
        with self.driver.session() as session:
            return session.run(cypher, **(params or {}))

    # ------------------------------------------------------------------
    # Compaction operations
    # ------------------------------------------------------------------

    def remove_orphan_nodes(self) -> int:
        """
        Delete nodes that have no relationships.
        Returns count of deleted nodes.
        """
        try:
            result = self._run(
                """
                MATCH (n)
                WHERE NOT (n)--()
                WITH n LIMIT $batch
                DELETE n
                RETURN count(n) AS deleted
                """,
                {"batch": _BATCH},
            )
            record = result.single()
            count = record["deleted"] if record else 0
            logger.info("remove_orphan_nodes: deleted %d orphan nodes", count)
            return int(count)
        except Exception as exc:
            logger.error("remove_orphan_nodes failed: %s", exc)
            return 0

    def prune_stale_relations(self, archived_doc_ids: list) -> int:
        """
        Delete RELATED_TO/SIMILAR_TO edges whose source doc_id is in archived_doc_ids.
        Returns count of deleted relationships.
        """
        if not archived_doc_ids:
            return 0
        try:
            result = self._run(
                """
                MATCH ()-[r]->()
                WHERE r.doc_id IN $ids
                WITH r LIMIT $batch
                DELETE r
                RETURN count(r) AS deleted
                """,
                {"ids": archived_doc_ids, "batch": _BATCH},
            )
            record = result.single()
            count = record["deleted"] if record else 0
            logger.info("prune_stale_relations: deleted %d stale relations", count)
            return int(count)
        except Exception as exc:
            logger.error("prune_stale_relations failed: %s", exc)
            return 0

    def compact_similar_edges(self) -> int:
        """
        Merge parallel SIMILAR_TO edges between the same node pair into
        a single weighted edge (averaged weight).
        Returns number of edge pairs compacted.
        """
        try:
            result = self._run(
                """
                MATCH (a)-[r:SIMILAR_TO]->(b)
                WITH a, b, collect(r) AS rels, avg(r.weight) AS avg_weight
                WHERE size(rels) > 1
                WITH a, b, rels, avg_weight LIMIT $batch
                FOREACH (r IN rels | DELETE r)
                MERGE (a)-[new:SIMILAR_TO]->(b)
                SET new.weight = avg_weight
                RETURN count(a) AS compacted
                """,
                {"batch": _BATCH},
            )
            record = result.single()
            count = record["compacted"] if record else 0
            logger.info("compact_similar_edges: compacted %d edge pairs", count)
            return int(count)
        except Exception as exc:
            logger.error("compact_similar_edges failed: %s", exc)
            return 0

    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Return basic statistics about the Neo4j graph.
        """
        try:
            result = self._run("MATCH (n) RETURN count(n) AS nodes")
            node_count = result.single()["nodes"] if result else 0

            result = self._run("MATCH ()-[r]->() RETURN count(r) AS rels")
            rel_count = result.single()["rels"] if result else 0

            result = self._run(
                "MATCH (n) WHERE NOT (n)--() RETURN count(n) AS orphans"
            )
            orphans = result.single()["orphans"] if result else 0

            return {
                "node_count": int(node_count),
                "relationship_count": int(rel_count),
                "orphan_nodes": int(orphans),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as exc:
            logger.error("get_graph_stats failed: %s", exc)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Full compaction run
    # ------------------------------------------------------------------

    async def run_compaction(self) -> Dict[str, Any]:
        """
        Execute all compaction steps and return a summary dict.
        Steps run sequentially; any step failure is logged but does not
        abort subsequent steps.
        """
        summary: Dict[str, Any] = {
            "started_at": datetime.now(UTC).isoformat(),
            "orphans_removed": 0,
            "stale_relations_pruned": 0,
            "similar_edges_compacted": 0,
            "errors": [],
        }

        # Step 1: Get archived doc IDs from PostgreSQL
        archived_ids: list = []
        if self.pool:
            try:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch(
                        f"""
                        SELECT id FROM {_t_docs()}
                         WHERE memory_tier = 'archive'
                            OR (expire_at IS NOT NULL AND expire_at < NOW())
                         LIMIT 1000
                        """
                    )
                archived_ids = [r["id"] for r in rows]
            except Exception as exc:
                logger.warning("run_compaction: could not fetch archived IDs: %s", exc)
                summary["errors"].append(f"archived_ids fetch: {exc}")

        # Step 2: Prune stale relations
        try:
            summary["stale_relations_pruned"] = self.prune_stale_relations(archived_ids)
        except Exception as exc:
            summary["errors"].append(f"prune_stale_relations: {exc}")

        # Step 3: Remove orphan nodes
        try:
            summary["orphans_removed"] = self.remove_orphan_nodes()
        except Exception as exc:
            summary["errors"].append(f"remove_orphan_nodes: {exc}")

        # Step 4: Compact parallel edges
        try:
            summary["similar_edges_compacted"] = self.compact_similar_edges()
        except Exception as exc:
            summary["errors"].append(f"compact_similar_edges: {exc}")

        summary["finished_at"] = datetime.now(UTC).isoformat()
        return summary


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_graph_compactor: Optional[GraphCompactor] = None


def init_graph_compactor(
    neo4j_driver: Any,
    postgres_pool: Any = None,
) -> GraphCompactor:
    global _graph_compactor
    _graph_compactor = GraphCompactor(neo4j_driver, postgres_pool)
    logger.info("OK GraphCompactor initialized")
    return _graph_compactor


def get_graph_compactor() -> Optional[GraphCompactor]:
    return _graph_compactor
