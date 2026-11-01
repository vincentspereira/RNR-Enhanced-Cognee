"""Source-grounded graph traversal with authoritative authorization at each hop."""
from __future__ import annotations

import math
import json

from src.index_contracts import normalized, validated_links
from src.memory_library import READ_PREDICATE
from src.security.enterprise_auth import AuthError
from src.security.memory_admission import contains_private_memory_details


class DerivedRecall:
    def __init__(self, sinks):
        self.sinks = sinks
        self.pipeline = sinks.identity.pipeline

    async def status(self, service, scope):
        async with service.pool.acquire() as conn:
            worker = await conn.fetchrow("""SELECT state,heartbeat,model,dimensions,
                heartbeat > now()-interval '30 seconds' AS fresh FROM shared_memory.index_workers WHERE pipeline=$1""",
                self.pipeline)
            lag = await conn.fetchrow("""SELECT count(*) AS pending,
                coalesce(max(extract(epoch FROM now()-o.created_at)),0) AS seconds
                FROM shared_memory.record_outbox o LEFT JOIN shared_memory.index_deliveries d
                  ON d.event_id=o.id AND d.pipeline=$3
                WHERE o.tenant=$1 AND o.project=$2 AND d.completed_at IS NULL""",
                scope.tenant, scope.project, self.pipeline)
        fresh = bool(worker and worker["fresh"] and worker["state"] == "running"
                     and worker["model"] == self.sinks.model and worker["dimensions"] == self.sinks.dimensions)
        return {"pipeline": self.pipeline, "worker_available": fresh,
                "worker_state": worker["state"] if worker and worker["fresh"] else "unavailable",
                "pending_change_events": lag["pending"], "oldest_pending_seconds": float(lag["seconds"]),
                "graph": "source_linked_graph" if fresh else "unavailable",
                "vector_index": "available" if fresh else "degraded",
                "cache_contents": "encrypted_records_only"}

    async def vector_scores(self, scope, vector, rows, limit):
        """Index candidates must already be authorized by canonical SQL.

        The caller retains current local scores for missing, delayed or rejected
        index results. Index downtime must not hide an acknowledged new memory.
        """
        allowed = {row["id"]: row for row in rows}
        try:
            hits = await self.sinks.search(scope.tenant, vector, list(allowed), limit)
        except Exception:
            return {}, "degraded"
        scores = {}
        for hit in hits:
            ident = str(hit.get("id", ""))
            row = allowed.get(ident)
            data = hit.get("payload", {})
            score = hit.get("score")
            if (row and data.get("tenant") == scope.tenant and data.get("project") == row["project"]
                    and data.get("record_id") == ident and data.get("version") == row["version"]
                    and data.get("model") == self.sinks.model and isinstance(score, (int, float))
                    and math.isfinite(score) and -1 <= score <= 1):
                scores[ident] = score
        return scores, "queried"

    async def connections(self, service, scope, entity: str, *, depth=2, limit=10, include_shared=True):
        if not entity.strip() or len(entity) > 160 or not 1 <= depth <= 3 or not 1 <= limit <= 20:
            raise ValueError("Use a bounded starting entity, depth 1-3 and at most twenty paths")
        status = await self.status(service, scope)
        if not status["worker_available"]:
            raise AuthError(503, "Graph index is not ready; current text/semantic recall remains available")
        candidate_limit = min(service.candidate_limit, 2000)
        async with service.pool.acquire() as conn:
            authorized = await conn.fetch("SELECT r.id FROM shared_memory.records r WHERE " + READ_PREDICATE +
                " ORDER BY r.updated_at DESC,r.id LIMIT $4", scope.tenant, scope.project, include_shared, candidate_limit+1)
        identifiers = [row["id"] for row in authorized[:candidate_limit]]
        frontier, paths, inspected, limited = [(entity, [], frozenset({normalized(entity)}))], [], 0, len(authorized)>candidate_limit
        response_bytes = 0
        for _ in range(depth):
            following = []
            for current, chain, seen in frontier:
                neighbors = await self.sinks.neighbors(scope.tenant, current, identifiers=identifiers, limit=64)
                limited = limited or len(neighbors) == 64
                for edge in neighbors:
                    inspected += 1
                    if inspected > 128 or len(paths) >= limit:
                        limited = True
                        break
                    # An index is never an authorization authority, even when its
                    # document claims to belong to the requesting project.
                    async with service.pool.acquire() as conn:
                        row = await conn.fetchrow("SELECT r.* FROM shared_memory.records r WHERE " + READ_PREDICATE +
                            " AND r.project=$4 AND r.id=$5", scope.tenant, scope.project, include_shared,
                            str(edge.get("project", "")), str(edge.get("record_id", "")))
                    if row is None or row["version"] != edge.get("version"):
                        continue
                    try:
                        record = service._decode(row)
                        if scope.selected_capture and contains_private_memory_details(record):
                            continue
                        links = validated_links(record["content"], record.get("knowledge_links", []))
                        number = edge.get("link_index")
                        if not isinstance(number, int) or not 0 <= number < len(links):
                            continue
                        link = links[number]
                        if (normalized(link["subject"]) != normalized(current)
                                or edge.get("source_key") != self.sinks.entity(scope.tenant, link["subject"])
                                or edge.get("target_key") != self.sinks.entity(scope.tenant, link["object"])):
                            continue
                    except (ValueError, TypeError, KeyError):
                        continue
                    target = normalized(link["object"])
                    if target in seen:
                        continue
                    next_chain = chain + [{"subject": link["subject"], "predicate": link["predicate"],
                        "object": link["object"], "record_id": row["id"], "version": row["version"],
                        "source_project": row["project"], "source_excerpt": record["content"][link["span_start"]:link["span_end"]][:2048],
                        "source_excerpt_truncated": link["span_end"] - link["span_start"] > 2048,
                        "evidence": record.get("evidence"), "authority": "actor_submitted_unverified"}]
                    size = len(json.dumps(next_chain, ensure_ascii=True).encode())
                    if response_bytes+size > 128*1024:
                        limited = True
                        break
                    response_bytes += size
                    paths.append(next_chain)
                    following.append((link["object"], next_chain, seen | {target}))
                if limited and (inspected > 128 or len(paths) >= limit):
                    break
            frontier = following
            if not frontier or inspected > 128 or len(paths) >= limit:
                break
        return {"paths": paths, "retrieval": "source_linked_graph", "instructions_are_data": True,
                "claims_are_verified": False, "budget_limit_reached": limited,
                "index_pending_changes": status["pending_change_events"], "pipeline": self.pipeline}
