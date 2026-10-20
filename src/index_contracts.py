"""Bounded, source-linked graph declarations and private derived identifiers."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field

from src.security.memory_admission import require_no_credentials


class KnowledgeLink(BaseModel):
    """An actor's claim, never a verified fact or an execution instruction."""
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(min_length=1, max_length=160)
    predicate: str = Field(min_length=1, max_length=80)
    object: str = Field(min_length=1, max_length=160)
    span_start: int = Field(ge=0)
    span_end: int = Field(ge=1)


def validated_links(content: str, values=None) -> list[dict]:
    if values is None:
        return []
    if not isinstance(values, list) or len(values) > 16:
        raise ValueError("A memory can declare at most sixteen source-linked relationships")
    result = []
    for value in values:
        link = KnowledgeLink.model_validate(value).model_dump()
        if not 0 <= link["span_start"] < link["span_end"] <= len(content):
            raise ValueError("Relationship spans must refer to the submitted content")
        for field in ("subject", "predicate", "object"):
            link[field] = " ".join(link[field].split())
            if not link[field] or any(unicodedata.category(char).startswith("C") for char in link[field]):
                raise ValueError("Relationship labels require printable bounded text")
        # Requiring the named endpoints in the cited span prevents an unrelated
        # record from being presented as the source for a fabricated graph edge.
        # This checks source correspondence, not the truth/semantics of a claim.
        span = normalized(content[link["span_start"]:link["span_end"]])
        if any(normalized(link[field]) not in span for field in ("subject", "object")):
            raise ValueError("Relationship endpoints must occur in the cited content span")
        require_no_credentials(json.dumps(link, ensure_ascii=True))
        if link not in result:
            result.append(link)
    return result


def normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


class IndexIdentity:
    def __init__(self, key: str, pipeline: str):
        if len(key.encode()) < 32 or not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", pipeline):
            raise ValueError("Use a persistent index key and a bounded pipeline identifier")
        self._key = key.encode()
        self.pipeline = pipeline

    def entity(self, tenant: str, value: str) -> str:
        return self._digest("entity", tenant, normalized(value))

    def record(self, tenant: str, project: str, ident: str) -> str:
        return self._digest("record", tenant, project, ident)

    def _digest(self, *values: str) -> str:
        data = json.dumps([self.pipeline, *values], ensure_ascii=True, separators=(",", ":")).encode()
        return hmac.new(self._key, data, hashlib.sha256).hexdigest()


INDEX_SCHEMA = """
CREATE TABLE IF NOT EXISTS shared_memory.index_deliveries (
 event_id BIGINT NOT NULL REFERENCES shared_memory.record_outbox(id),
 pipeline TEXT NOT NULL, lease_id TEXT, lease_until TIMESTAMPTZ,
 attempts INTEGER NOT NULL DEFAULT 0, retry_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 completed_at TIMESTAMPTZ, error_code TEXT,
 PRIMARY KEY(event_id,pipeline)
);
CREATE INDEX IF NOT EXISTS index_delivery_pending
 ON shared_memory.index_deliveries(pipeline,retry_at,event_id) WHERE completed_at IS NULL;
CREATE INDEX IF NOT EXISTS index_delivery_failed
 ON shared_memory.index_deliveries(pipeline) WHERE completed_at IS NULL AND error_code IS NOT NULL;
CREATE TABLE IF NOT EXISTS shared_memory.index_receipts (
 tenant TEXT NOT NULL, project TEXT NOT NULL, record_id TEXT NOT NULL,
 pipeline TEXT NOT NULL, version INTEGER NOT NULL, active BOOLEAN NOT NULL,
 model TEXT, dimensions INTEGER, indexed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant,project,record_id,pipeline),
 FOREIGN KEY(tenant,project,record_id) REFERENCES shared_memory.records(tenant,project,id)
);
CREATE TABLE IF NOT EXISTS shared_memory.index_workers (
 pipeline TEXT PRIMARY KEY, heartbeat TIMESTAMPTZ NOT NULL DEFAULT now(),
 state TEXT NOT NULL, model TEXT, dimensions INTEGER
);
"""
