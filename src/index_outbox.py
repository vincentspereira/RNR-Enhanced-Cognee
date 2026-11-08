"""Restart-safe, leased delivery of current encrypted-memory projections.

At-least-once delivery is intentional: each sink replaces a record snapshot
idempotently. Acknowledgement follows every sink; canonical writes never depend
on a live index. No source memory, history or outbox event is deleted.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import uuid

from src.index_contracts import validated_links
from src.security.memory_admission import contains_credentials


class IndexWorker:
    def __init__(self, service, sinks, *, lease_seconds: int = 30):
        if not 15 <= lease_seconds <= 300 or service.embedder is None:
            raise ValueError("Workers require a prepared local embedder and a bounded lease")
        if service.embedder.model != sinks.model:
            raise ValueError("The worker and its sinks must use the same embedding model")
        self.service, self.pool, self.sinks = service, service.pool, sinks
        self.pipeline = sinks.identity.pipeline
        self.lease_seconds = lease_seconds

    async def heartbeat(self, state=None):
        async with self.pool.acquire() as conn:
            if state is None:
                failed = await conn.fetchval("""SELECT EXISTS(SELECT 1 FROM shared_memory.index_deliveries
                    WHERE pipeline=$1 AND completed_at IS NULL AND error_code IS NOT NULL)""", self.pipeline)
                state = "degraded" if failed else "running"
            value = await conn.fetchval("""INSERT INTO shared_memory.index_workers
                (pipeline,state,model,dimensions) VALUES($1,$2,$3,$4)
                ON CONFLICT(pipeline) DO UPDATE SET heartbeat=now(),state=excluded.state
                WHERE index_workers.model=excluded.model AND index_workers.dimensions=excluded.dimensions
                RETURNING pipeline""", self.pipeline, state, self.sinks.model, self.sinks.dimensions)
            if value is None:
                raise ValueError("Choose a new pipeline when changing the index model or dimensions")

    async def _claim(self):
        lease = uuid.uuid4().hex
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Expiry has immediate authoritative read exclusion even when
                # this delayed cleanup cannot reach a sink.
                await conn.execute("""INSERT INTO shared_memory.record_outbox
                    (tenant,project,record_id,version,event)
                    SELECT r.tenant,r.project,r.id,r.version,'expired' FROM shared_memory.records r
                    WHERE r.state='active' AND r.expires_at<=now() AND NOT EXISTS(
                      SELECT 1 FROM shared_memory.record_outbox o WHERE o.tenant=r.tenant
                      AND o.project=r.project AND o.record_id=r.id AND o.version=r.version AND o.event='expired')
                    ORDER BY r.expires_at LIMIT 64 ON CONFLICT DO NOTHING""")
                await conn.execute("""INSERT INTO shared_memory.index_deliveries(event_id,pipeline)
                    SELECT o.id,$1 FROM shared_memory.record_outbox o WHERE NOT EXISTS(
                      SELECT 1 FROM shared_memory.index_deliveries d WHERE d.event_id=o.id AND d.pipeline=$1)
                    ORDER BY o.id LIMIT 64 ON CONFLICT DO NOTHING""", self.pipeline)
                # A materialized candidate is selected exactly once. An inline
                # locking subquery may be rescanned by a nested-loop plan and
                # lease multiple events while fetchrow returns only one.
                return await conn.fetchrow("""WITH candidate AS MATERIALIZED (
                      SELECT event_id FROM shared_memory.index_deliveries
                      WHERE pipeline=$1 AND completed_at IS NULL AND retry_at<=now()
                      AND (lease_until IS NULL OR lease_until<=now())
                      ORDER BY event_id FOR UPDATE SKIP LOCKED LIMIT 1)
                    UPDATE shared_memory.index_deliveries d
                    SET lease_id=$2,lease_until=now()+$3::int*interval '1 second',attempts=d.attempts+1
                    FROM candidate
                    WHERE d.event_id=candidate.event_id AND d.pipeline=$1
                    RETURNING d.*""", self.pipeline, lease, self.lease_seconds)

    async def run_once(self) -> bool:
        await self.heartbeat()
        job = await self._claim()
        if job is None:
            return False
        try:
            async with asyncio.timeout(10):
                await self._deliver(job)
            await self.heartbeat()
        except asyncio.CancelledError:
            # The lease deliberately survives interruption; a new process can
            # reclaim it after expiry, including a crash after partial delivery.
            raise
        except Exception:
            async with self.pool.acquire() as conn:
                await conn.execute("""UPDATE shared_memory.index_deliveries SET
                    lease_id=NULL,lease_until=NULL,error_code='projection_unavailable',
                    retry_at=now()+$4::int*interval '1 second'
                    WHERE event_id=$1 AND pipeline=$2 AND lease_id=$3 AND completed_at IS NULL""",
                    job["event_id"], self.pipeline, job["lease_id"], min(60, 2 ** min(job["attempts"], 6)))
            await self.heartbeat("degraded")
        return True

    async def _deliver(self, job):
        async with self.pool.acquire() as conn:
            event = await conn.fetchrow("SELECT * FROM shared_memory.record_outbox WHERE id=$1", job["event_id"])
            if event is None:
                raise ValueError("The immutable change event is unavailable")
            async with conn.transaction():
                await conn.execute("SET LOCAL lock_timeout='3s'")
                await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                    "index:" + event["tenant"] + ":" + event["project"] + ":" + event["record_id"])
                owned = await conn.fetchval("""SELECT lease_id FROM shared_memory.index_deliveries
                    WHERE event_id=$1 AND pipeline=$2 AND lease_id=$3 AND completed_at IS NULL FOR UPDATE""",
                    job["event_id"], self.pipeline, job["lease_id"])
                if not owned:
                    return
                row = await conn.fetchrow("SELECT * FROM shared_memory.records WHERE tenant=$1 AND project=$2 AND id=$3",
                                         event["tenant"], event["project"], event["record_id"])
                if row is None:
                    raise ValueError("The canonical memory is unavailable")
                payload = self.service._payload(row)
                active = row["state"] == "active" and (row["expires_at"] is None or row["expires_at"] > datetime.now(timezone.utc))
                active = active and not contains_credentials(json.dumps(payload, ensure_ascii=True))
                vector = []
                if active:
                    payload["knowledge_links"] = validated_links(payload["content"], payload.get("knowledge_links", []))
                    if payload.get("embedding_model") == self.sinks.model and payload.get("embedding"):
                        vector = payload["embedding"]
                    else:
                        vector = await self.service.embedder.embed(payload["content"])
                await self.sinks.project(row, payload, vector, active=active)
                await conn.execute("""INSERT INTO shared_memory.index_receipts
                    (tenant,project,record_id,pipeline,version,active,model,dimensions)
                    VALUES($1,$2,$3,$4,$5,$6,$7,$8)
                    ON CONFLICT(tenant,project,record_id,pipeline) DO UPDATE SET
                    version=excluded.version,active=excluded.active,model=excluded.model,
                    dimensions=excluded.dimensions,indexed_at=now()""",
                    row["tenant"], row["project"], row["id"], self.pipeline, row["version"],
                    active, self.sinks.model, self.sinks.dimensions)
                await conn.execute("""UPDATE shared_memory.index_deliveries
                    SET completed_at=now(),lease_id=NULL,lease_until=NULL,error_code=NULL
                    WHERE event_id=$1 AND pipeline=$2 AND lease_id=$3""", job["event_id"], self.pipeline, job["lease_id"])
                await conn.execute("UPDATE shared_memory.record_outbox SET processed_at=coalesce(processed_at,now()) WHERE id=$1",
                                   job["event_id"])

    async def run(self, stop: asyncio.Event):
        try:
            while not stop.is_set():
                worked = await self.run_once()
                if not worked:
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=.5)
                    except asyncio.TimeoutError:
                        pass
        finally:
            await self.heartbeat("stopped")
