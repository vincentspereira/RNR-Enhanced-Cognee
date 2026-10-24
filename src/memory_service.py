"""Versioned, encrypted project memory with explicit, revocable sharing.

PostgreSQL is authoritative. Project and tenant come from credentials, not a
model-generated category or dataset name. Derived features never widen scope.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.encryption_manager import EncryptionManager
from src.memory_contracts import evidence_declaration
from src.memory_library import LibraryAccess, LIBRARY_SCHEMA, READ_PREDICATE
from src.multi_tenant import validate_tenant_id
from src.security.auth import Permission
from src.security.enterprise_auth import AuthError, Principal
from src.security.memory_admission import require_no_credentials, contains_credentials, contains_private_details, contains_private_memory_details
from src.index_contracts import INDEX_SCHEMA, validated_links
from src.memory_queries import MemoryQueries


class MemoryConflict(ValueError):
    """A retry key or expected version conflicts with canonical data."""


class MemoryClarificationRequired(ValueError):
    """A selected automatic capture needs a sanitized summary or human review."""


@dataclass(frozen=True)
class MemoryScope:
    tenant: str
    project: str
    subject: str
    agent: str
    admin: bool = False
    selected_capture: bool = False

    @classmethod
    def from_principal(cls, principal: Principal) -> "MemoryScope":
        tenant = validate_tenant_id(principal.tenant_id or "")
        project = validate_tenant_id(str(principal.claims.get("project_id") or ""))
        return cls(tenant, project, principal.subject,
                   str(principal.claims.get("agent_id") or principal.subject),
                   principal.has_permission(Permission.MEMORY_ADMIN), principal.claims.get("capture_policy") == "selected")


SCHEMA = """
CREATE SCHEMA IF NOT EXISTS shared_memory;
CREATE TABLE IF NOT EXISTS shared_memory.records (
 tenant TEXT NOT NULL, project TEXT NOT NULL, id TEXT NOT NULL,
 owner_subject TEXT NOT NULL, writer_agent TEXT NOT NULL,
 version INTEGER NOT NULL CHECK(version > 0), payload TEXT NOT NULL,
 request_hash TEXT NOT NULL, idempotency_key TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'active' CHECK(state IN ('active','retracted')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 expires_at TIMESTAMPTZ,
 PRIMARY KEY(tenant,project,id), UNIQUE(tenant,project,idempotency_key)
);
ALTER TABLE shared_memory.records ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
CREATE TABLE IF NOT EXISTS shared_memory.record_versions (
 tenant TEXT NOT NULL, project TEXT NOT NULL, record_id TEXT NOT NULL,
 version INTEGER NOT NULL, payload TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant,project,record_id,version),
 FOREIGN KEY(tenant,project,record_id) REFERENCES shared_memory.records(tenant,project,id)
);
CREATE TABLE IF NOT EXISTS shared_memory.record_shares (
 tenant TEXT NOT NULL, project TEXT NOT NULL, record_id TEXT NOT NULL,
 target_project TEXT NOT NULL, reviewed_by TEXT NOT NULL, version INTEGER NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant,project,record_id,target_project),
 FOREIGN KEY(tenant,project,record_id) REFERENCES shared_memory.records(tenant,project,id)
);
CREATE TABLE IF NOT EXISTS shared_memory.record_outbox (
 id BIGSERIAL PRIMARY KEY, tenant TEXT NOT NULL, project TEXT NOT NULL,
 record_id TEXT NOT NULL, version INTEGER NOT NULL,
 event TEXT NOT NULL, processed_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(tenant,project,record_id,version,event)
);
CREATE INDEX IF NOT EXISTS records_scope_updated
 ON shared_memory.records(tenant,project,updated_at DESC);
CREATE INDEX IF NOT EXISTS shares_target
 ON shared_memory.record_shares(tenant,target_project);
CREATE TABLE IF NOT EXISTS shared_memory.request_budgets (
 tenant TEXT NOT NULL, project TEXT NOT NULL, subject TEXT NOT NULL,
 window_start TIMESTAMPTZ NOT NULL, used INTEGER NOT NULL CHECK(used > 0),
 PRIMARY KEY(tenant,project,subject)
);
CREATE TABLE IF NOT EXISTS shared_memory.record_audit (
 id BIGSERIAL PRIMARY KEY, tenant TEXT NOT NULL, project TEXT NOT NULL,
 actor TEXT NOT NULL, agent TEXT NOT NULL, record_id TEXT NOT NULL,
 version INTEGER NOT NULL, action TEXT NOT NULL,
 occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS shared_memory.memory_service_schema (
 version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO shared_memory.memory_service_schema(version) VALUES(1) ON CONFLICT DO NOTHING;
"""


class MemoryService(LibraryAccess, MemoryQueries):
    SCHEMA_VERSION = 3
    def __init__(self, pool, cipher: EncryptionManager, embedder=None, *, candidate_limit: int = 2000,
                 candidate_budget_bytes: int = 16 * 1024 * 1024, derived=None):
        if not cipher._enabled:
            raise RuntimeError("The memory service requires authenticated encryption")
        self.pool, self.cipher, self.embedder = pool, cipher, embedder
        self.derived = derived
        self.candidate_limit = candidate_limit
        if candidate_limit < 1 or candidate_budget_bytes < 1:
            raise ValueError("Recall candidate limits must be positive")
        self.candidate_budget_bytes = candidate_budget_bytes
        self._recall_slots = asyncio.Semaphore(2)

    async def initialize(self) -> None:
        await self.provision(self.pool)

    @staticmethod
    async def provision(pool) -> None:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock(hashtext('enhanced_cognee:memory_schema'))")
                exists = await conn.fetchval("SELECT to_regclass('shared_memory.memory_service_schema')")
                if exists and (await conn.fetchval("SELECT max(version) FROM shared_memory.memory_service_schema") or 0) > MemoryService.SCHEMA_VERSION:
                    raise RuntimeError("A newer memory schema requires its matching service release")
                await conn.execute(SCHEMA)
                await conn.execute(LIBRARY_SCHEMA)
                await conn.execute(INDEX_SCHEMA)
                await conn.execute("ALTER TABLE shared_memory.records ADD COLUMN IF NOT EXISTS fact_key TEXT")
                await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS records_fact_key ON shared_memory.records(tenant,project,fact_key) WHERE fact_key IS NOT NULL")
                await conn.execute("INSERT INTO shared_memory.memory_service_schema(version) VALUES(3) ON CONFLICT DO NOTHING")

    async def check_schema(self) -> None:
        async with self.pool.acquire() as conn:
            if await conn.fetchval("SELECT max(version) FROM shared_memory.memory_service_schema") != self.SCHEMA_VERSION:
                raise RuntimeError("Provision the matching memory schema before service startup")

    async def status(self, scope: MemoryScope) -> dict:
        async with self.pool.acquire() as conn:
            count = await conn.fetchval("""SELECT count(*) FROM shared_memory.records
                WHERE tenant=$1 AND project=$2 AND state='active'
                AND (expires_at IS NULL OR expires_at > now())""", scope.tenant, scope.project)
            pending = await conn.fetchval("""SELECT count(*) FROM shared_memory.record_outbox
                WHERE tenant=$1 AND project=$2 AND processed_at IS NULL""", scope.tenant, scope.project)
        status = {"ready": True, "tenant_id": scope.tenant, "project_id": scope.project,
                "subject": scope.subject, "active_records": count,
                "pending_change_events": pending, "change_feed_worker": "unavailable",
                "retrieval": "semantic" if self.embedder else "text",
                "embedding_model": getattr(self.embedder, "model", None),
                "graph": "unavailable", "encryption": "AES-256-GCM",
                "encryption_key_id": getattr(self.cipher, "active", "legacy_unnamed"), "schema_version": self.SCHEMA_VERSION}
        if self.derived is not None:
            index = await self.derived.status(self, scope)
            status.update(index=index, graph=index["graph"], change_feed_worker=index["worker_state"],
                          pending_change_events=index["pending_change_events"])
        return status

    async def admit_request(self, principal: Principal, per_minute: int) -> None:
        """Atomic shared budget per verified identity, bounded to one row per actor."""
        scope = MemoryScope.from_principal(principal)
        async with self.pool.acquire() as conn:
            used = await conn.fetchval("""INSERT INTO shared_memory.request_budgets
                (tenant,project,subject,window_start,used)
                VALUES($1,$2,$3,date_trunc('minute',now()),1)
                ON CONFLICT(tenant,project,subject) DO UPDATE SET
                  window_start=date_trunc('minute',now()),
                  used=CASE WHEN request_budgets.window_start < date_trunc('minute',now())
                            THEN 1 ELSE request_budgets.used+1 END
                WHERE request_budgets.window_start < date_trunc('minute',now())
                   OR request_budgets.used < $4
                RETURNING used""", scope.tenant, scope.project, scope.subject, per_minute)
        if used is None:
            raise AuthError(429, "Memory request budget exceeded; retry next minute.")

    def _encode(self, payload: dict) -> str:
        encoded = self.cipher.encrypt(json.dumps(payload, ensure_ascii=True, sort_keys=True, allow_nan=False))
        if not encoded.startswith("enc2:"):
            raise RuntimeError("Encrypted storage is required")
        return encoded

    def _decode(self, row) -> dict:
        result = self._payload(row)
        require_no_credentials(json.dumps(result, ensure_ascii=True))
        result.update(id=row["id"], version=row["version"], project_id=row["project"], state=row["state"],
                      expires_at=row["expires_at"].isoformat() if row["expires_at"] else None,
                      created_at=row["created_at"].isoformat(), updated_at=row["updated_at"].isoformat())
        # Embeddings are internal projections, not model-visible memory content.
        result.pop("embedding", None)
        return result

    def _payload(self, row) -> dict:
        if not row["payload"].startswith("enc2:"):
            raise RuntimeError("Unencrypted canonical memory cannot be read")
        return json.loads(self.cipher.decrypt(row["payload"]))

    @staticmethod
    def admit(content: str) -> None:
        if not content.strip() or len(content.encode("utf-8")) > 65536:
            raise ValueError("Memory content must contain 1-65536 UTF-8 bytes")
        require_no_credentials(content)

    async def remember(self, scope: MemoryScope, content: str, *, idempotency_key: str,
                       category: str = "general", metadata: Optional[dict] = None,
                       expires_at: Optional[datetime] = None,
                       evidence: Optional[dict] = None, fact_key: Optional[str] = None,
                       knowledge_links: Optional[list] = None) -> dict:
        self.admit(content)
        if not 1 <= len(idempotency_key) <= 200 or not 1 <= len(category) <= 100:
            raise ValueError("Invalid retry key or category length")
        # Retry/topic identifiers are stored outside the encrypted payload too.
        # Screen every caller-controlled field before any database or model work.
        admission_fields = json.dumps([category, idempotency_key, fact_key], ensure_ascii=True)
        require_no_credentials(admission_fields)
        metadata = metadata or {}
        self.admit(json.dumps(metadata, ensure_ascii=True, allow_nan=False))
        if expires_at is not None:
            if expires_at.tzinfo is None:
                raise ValueError("Memory expiry must include a timezone")
            expires_at = expires_at.astimezone(timezone.utc)
        evidence = evidence_declaration(evidence)
        links = validated_links(content, knowledge_links)
        self.admit(json.dumps(evidence, ensure_ascii=True, allow_nan=False))
        if scope.selected_capture and contains_private_details(json.dumps(
                [content, category, idempotency_key, fact_key, metadata, evidence, links], ensure_ascii=True)):
            raise MemoryClarificationRequired("Please clarify a sanitized summary before automatic storage of private details")
        if fact_key is not None and (not isinstance(fact_key, str) or not re.fullmatch(r"[a-z][a-z0-9_.:-]{0,159}", fact_key)):
            raise ValueError("Fact keys must be bounded lowercase topic identifiers")
        request = {"content": content, "category": category, "metadata": metadata,
                   "expiry": expires_at.isoformat() if expires_at else None}
        # Preserve retry hashes for older callers that supplied no evidence.
        if evidence["declaration"] != {"kind": "unclassified"}:
            request["evidence"] = evidence
        if fact_key:
            request["fact_key"] = fact_key
        if links:
            request["knowledge_links"] = links
        digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        embedding = await self.embedder.embed(content) if self.embedder else None
        payload = dict(request, provenance={"subject": scope.subject, "agent_id": scope.agent,
                       "observed_at": datetime.now(timezone.utc).isoformat(),
                       "authority": "actor_submitted", "session_id": str(metadata.get("session_id") or "")[:200],
                       "content_sha256": hashlib.sha256(content.encode()).hexdigest()},
                       embedding=embedding, embedding_model=getattr(self.embedder, "model", None))
        payload["evidence"] = evidence
        ident = str(uuid.uuid4())
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if fact_key:
                    await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                                       scope.tenant + ":" + scope.project + ":fact:" + fact_key)
                    existing = await conn.fetchrow("SELECT * FROM shared_memory.records WHERE tenant=$1 AND project=$2 AND fact_key=$3",
                                                   scope.tenant, scope.project, fact_key)
                    if existing is not None and (existing["state"] != "active" or
                            (existing["expires_at"] and existing["expires_at"] <= datetime.now(timezone.utc))):
                        await conn.execute("UPDATE shared_memory.records SET fact_key=NULL WHERE tenant=$1 AND project=$2 AND id=$3",
                                           scope.tenant, scope.project, existing["id"])
                        await self._audit(conn, scope, existing["id"], existing["version"], "expired_fact_key_released")
                        existing = None
                    if existing is not None and existing["idempotency_key"] != idempotency_key:
                        raise MemoryConflict("This fact key already exists; recall its current version and clarify or correct it")
                row = await conn.fetchrow("""
                    INSERT INTO shared_memory.records
                    (tenant,project,id,owner_subject,writer_agent,version,payload,request_hash,idempotency_key,expires_at,fact_key)
                    VALUES($1,$2,$3,$4,$5,1,$6,$7,$8,$9,$10)
                    ON CONFLICT(tenant,project,idempotency_key) DO NOTHING RETURNING *
                    """, scope.tenant, scope.project, ident, scope.subject, scope.agent,
                    self._encode(payload), digest, idempotency_key, expires_at, fact_key)
                if row is None:
                    row = await conn.fetchrow("""SELECT * FROM shared_memory.records
                        WHERE tenant=$1 AND project=$2 AND idempotency_key=$3 FOR UPDATE""",
                        scope.tenant, scope.project, idempotency_key)
                    if row["request_hash"] != digest or row["owner_subject"] != scope.subject:
                        raise MemoryConflict("Retry key already belongs to another request")
                    return self._decode(row)
                await self._checkpoint(conn, row, "remembered", scope)
        return self._decode(row)

    async def _checkpoint(self, conn, row, event: str, scope: MemoryScope) -> None:
        await conn.execute("""INSERT INTO shared_memory.record_versions
            (tenant,project,record_id,version,payload) VALUES($1,$2,$3,$4,$5)""",
            row["tenant"], row["project"], row["id"], row["version"], row["payload"])
        await conn.execute("""INSERT INTO shared_memory.record_outbox
            (tenant,project,record_id,version,event) VALUES($1,$2,$3,$4,$5)""",
            row["tenant"], row["project"], row["id"], row["version"], event)
        await self._audit(conn, scope, row["id"], row["version"], event)

    async def _audit(self, conn, scope, record_id, version, action):
        await conn.execute("""INSERT INTO shared_memory.record_audit
            (tenant,project,actor,agent,record_id,version,action) VALUES($1,$2,$3,$4,$5,$6,$7)""",
            scope.tenant, scope.project, scope.subject, scope.agent, record_id, version, action)

    async def get(self, scope: MemoryScope, record_id: str) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT r.* FROM shared_memory.records r WHERE " + READ_PREDICATE + " AND r.id=$4",
                                      scope.tenant, scope.project, True, record_id)
        if row is None:
            raise KeyError("Memory not found in this project")
        result = self._decode(row)
        if scope.selected_capture and contains_private_memory_details(result):
            raise MemoryClarificationRequired("This record needs a sanitized current summary before selected recall")
        return self.shared_view(result) if row["project"] != scope.project else result

    async def correct(self, scope: MemoryScope, record_id: str, *, expected_version: int,
                      content: Optional[str] = None, retract: bool = False,
                      evidence: Optional[dict] = None, knowledge_links: Optional[list] = None,
                      metadata: Optional[dict] = None, category: Optional[str] = None) -> dict:
        if not retract:
            self.admit(content or "")
            if scope.selected_capture and contains_private_details(content or ""):
                raise MemoryClarificationRequired("Please clarify a sanitized correction before storing private details")
        replacement_evidence = evidence_declaration(evidence) if evidence is not None else None
        if replacement_evidence:
            self.admit(json.dumps(replacement_evidence, ensure_ascii=True, allow_nan=False))
        if metadata is not None:
            if not isinstance(metadata, dict):
                raise ValueError("Memory metadata must be an object")
            self.admit(json.dumps(metadata, ensure_ascii=True, allow_nan=False))
        if category is not None and not 1 <= len(category) <= 100:
            raise ValueError("Invalid category length")
        if category is not None:
            require_no_credentials(category)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Workers take the same record lock before publishing a snapshot.
                # A late delivery therefore cannot overwrite a newer correction.
                await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                                   "index:" + scope.tenant + ":" + scope.project + ":" + record_id)
                row = await conn.fetchrow("""SELECT * FROM shared_memory.records
                    WHERE tenant=$1 AND project=$2 AND id=$3 FOR UPDATE""",
                    scope.tenant, scope.project, record_id)
                if row is None or (row["owner_subject"] != scope.subject and not scope.admin):
                    raise KeyError("Memory not found for this owner")
                if row["version"] != expected_version:
                    raise MemoryConflict("Memory changed; read the current version before correcting")
                if row["state"] != "active":
                    raise MemoryConflict("Retracted memory cannot be reactivated by a correction")
                payload = self._payload(row)
                previous_hash = payload["provenance"]["content_sha256"]
                if not retract:
                    old_content = payload["content"]
                    payload["content"] = content
                    payload["knowledge_links"] = validated_links(content, knowledge_links if knowledge_links is not None
                        else payload.get("knowledge_links", []) if old_content == content else [])
                    if metadata is not None:
                        payload["metadata"] = metadata
                    if category is not None:
                        payload["category"] = category
                    payload["embedding"] = await self.embedder.embed(content) if self.embedder else None
                    payload["embedding_model"] = getattr(self.embedder, "model", None)
                    payload["provenance"]["content_sha256"] = hashlib.sha256(content.encode()).hexdigest()
                    payload["evidence"] = replacement_evidence or {
                        "declaration": {"kind": "unclassified"},
                        "authority": "actor_submitted_unverified",
                        "prior_evidence_version": row["version"],
                        "source_review_required": True,
                    }
                    if scope.selected_capture and contains_private_details(json.dumps(
                            [payload["content"], payload.get("metadata"), payload.get("category"),
                             payload.get("knowledge_links"), payload["evidence"]], ensure_ascii=True)):
                        raise MemoryClarificationRequired("Clarify a sanitized current record before storing private details")
                payload["provenance"]["corrected_by"] = scope.subject
                payload["provenance"]["corrected_at"] = datetime.now(timezone.utc).isoformat()
                payload["provenance"]["supersedes_version"] = row["version"]
                payload["provenance"]["previous_content_sha256"] = previous_hash
                changed = await conn.fetchrow("""UPDATE shared_memory.records SET
                    payload=$4,version=version+1,state=$5,updated_at=now(),
                    fact_key=CASE WHEN $5='retracted' THEN NULL ELSE fact_key END
                    WHERE tenant=$1 AND project=$2 AND id=$3 RETURNING *""",
                    scope.tenant, scope.project, record_id, self._encode(payload),
                    "retracted" if retract else "active")
                # A correction is private until its new version is reviewed.
                await conn.execute("DELETE FROM shared_memory.record_shares WHERE tenant=$1 AND project=$2 AND record_id=$3",
                                   scope.tenant, scope.project, record_id)
                await conn.execute("DELETE FROM shared_memory.library_publications WHERE tenant=$1 AND project=$2 AND record_id=$3",
                                   scope.tenant, scope.project, record_id)
                await self._checkpoint(conn, changed, "retracted" if retract else "corrected", scope)
        return {"id": record_id, "version": changed["version"], "state": changed["state"]}

    async def share(self, scope: MemoryScope, record_id: str, *, target_project: str,
                    expected_version: int, revoke: bool = False) -> dict:
        if not scope.admin:
            raise AuthError(403, "Sharing requires a reviewer credential")
        validate_tenant_id(target_project)
        if target_project == scope.project:
            raise ValueError("Share targets must be a different project")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("""SELECT * FROM shared_memory.records
                    WHERE tenant=$1 AND project=$2 AND id=$3 AND state='active'
                    AND (expires_at IS NULL OR expires_at > now()) FOR UPDATE""",
                    scope.tenant, scope.project, record_id)
                if row is None:
                    raise KeyError("Memory not found")
                if row["version"] != expected_version:
                    raise MemoryConflict("Review must name the current memory version")
                if revoke:
                    await conn.execute("""DELETE FROM shared_memory.record_shares
                        WHERE tenant=$1 AND project=$2 AND record_id=$3 AND target_project=$4""",
                        scope.tenant, scope.project, record_id, target_project)
                else:
                    await conn.execute("""INSERT INTO shared_memory.record_shares
                        (tenant,project,record_id,target_project,reviewed_by,version)
                        VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(tenant,project,record_id,target_project)
                        DO UPDATE SET reviewed_by=excluded.reviewed_by,version=excluded.version""",
                        scope.tenant, scope.project, record_id, target_project, scope.subject, expected_version)
                await self._audit(conn, scope, record_id, expected_version,
                                  ("sharing_revoked:" if revoke else "shared:") + target_project)
        return {"id": record_id, "target_project": target_project, "shared": not revoke}

    async def recall(self, scope: MemoryScope, query: str, *, limit: int = 5,
                     include_shared: bool = True) -> dict:
        async with self._recall_slots:
            return await self._recall(scope, query, limit=limit, include_shared=include_shared)

    async def _recall(self, scope: MemoryScope, query: str, *, limit: int,
                      include_shared: bool) -> dict:
        if not query.strip() or len(query) > 2000 or not 1 <= limit <= 20:
            raise ValueError("Invalid recall query or limit")
        vector = await self.embedder.embed(query) if self.embedder else None
        sql = "SELECT r.* FROM shared_memory.records r WHERE " + READ_PREDICATE + " ORDER BY r.updated_at DESC,r.id LIMIT $4"
        rows, candidate_bytes, truncated = [], 0, False
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                async for row in conn.cursor(sql, scope.tenant, scope.project, include_shared,
                                             self.candidate_limit + 1, prefetch=10):
                    size = len(row["payload"].encode("utf-8"))
                    if len(rows) == self.candidate_limit or candidate_bytes + size > self.candidate_budget_bytes:
                        truncated = True
                        break
                    candidate_bytes += size
                    rows.append(row)
        words = set(re.findall(r"\w+", query.lower()))
        ranked = []
        modes = set()
        index_scores, index_state = {}, "unconfigured"
        if vector and self.derived is not None:
            index_scores, index_state = await self.derived.vector_scores(scope, vector, rows, limit)
        for row in rows:
            raw = self._payload(row)
            if contains_credentials(json.dumps(raw, ensure_ascii=True)):
                continue
            if scope.selected_capture and contains_private_memory_details(raw):
                continue
            stored = raw.get("embedding")
            if vector and stored and raw.get("embedding_model") == self.embedder.model:
                if len(vector) != len(stored):
                    raise RuntimeError("Embedding dimensions differ; reindex before semantic recall")
                denom = math.sqrt(sum(x*x for x in vector) * sum(x*x for x in stored))
                score = sum(a*b for a,b in zip(vector, stored))/denom if denom else 0
                # Fresh authorized hits use the configured vector index. Missing
                # or delayed projections retain their current canonical score.
                score = index_scores.get(row["id"], score)
                mode = "semantic"
            else:
                tokens = set(re.findall(r"\w+", raw["content"].lower()))
                score = len(words & tokens)/max(1, len(words))
                mode = "text"
            modes.add(mode)
            if score > (0.2 if mode == "semantic" else 0):
                result = self._decode(row)
                if row["project"] != scope.project:
                    result = self.shared_view(result)
                result.update(score=score, shared=row["project"] != scope.project, retrieval=mode)
                ranked.append(result)
        ranked.sort(key=lambda item: item["score"], reverse=True)
        retrieval = "mixed" if len(modes) > 1 else next(iter(modes), "semantic" if vector else "text")
        selected, response_bytes, response_limited = [], 0, False
        for result in ranked[:limit]:
            # Recall supplies bounded evidence; get() retains the full record.
            if len(result["content"]) > 4096:
                result["content"] = result["content"][:4096]
                result["content_truncated"] = True
            if len(json.dumps(result.get("metadata", {}), ensure_ascii=True)) > 4096:
                result["metadata"] = {"omitted_from_recall": True}
            size = len(json.dumps(result, ensure_ascii=True).encode())
            if response_bytes + size > 128 * 1024:
                response_limited = True
                break
            response_bytes += size
            selected.append(result)
        return {"results": selected, "retrieval": retrieval,
                "vector_index": index_state,
                "response_limit_reached": response_limited,
                "candidate_limit_reached": truncated, "instructions_are_data": True}

    async def connections(self, scope, entity, *, depth=2, limit=10, include_shared=True):
        if self.derived is None:
            raise AuthError(503, "A source-linked graph index is not configured")
        async with asyncio.timeout(10):
            return await self.derived.connections(self, scope, entity, depth=depth, limit=limit,
                                                  include_shared=include_shared)
