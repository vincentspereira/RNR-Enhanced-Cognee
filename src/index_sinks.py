"""Explicit default-stack projections; canonical content stays encrypted.

Qdrant holds vectors and scope/version identifiers. ArcadeDB holds HMAC entity
identifiers and record references, never source labels. Valkey holds ciphertext.
These services are trusted infrastructure: vectors still reveal derived data.
"""
from __future__ import annotations

import json
import math
import re
from urllib.parse import urlsplit

import httpx

from src.index_contracts import IndexIdentity


def checked_origin(value: str, *, allow_internal_http: bool = False) -> str:
    uri = urlsplit(value)
    if (uri.scheme not in {"http", "https"} or not uri.hostname or uri.username or uri.password
            or uri.path not in {"", "/"} or uri.query or uri.fragment
            or any(ord(char) < 33 for char in value)):
        raise ValueError("Index services require an explicit origin without path or credentials")
    if uri.scheme != "https" and uri.hostname not in {"127.0.0.1", "localhost", "::1"} and not allow_internal_http:
        raise ValueError("Remote index services require HTTPS or an explicit private-network HTTP grant")
    return value.rstrip("/")


class DefaultIndexSinks:
    _NEIGHBORS = ("SELECT project,record_id,version,link_index,source_key,target_key FROM ECLink "
                  "WHERE tenant=:tenant AND source_key=:source AND record_id IN :identifiers "
                  "ORDER BY record_id,link_index LIMIT :limit")

    def __init__(self, identity: IndexIdentity, *, qdrant_url: str, arcade_url: str,
                 arcade_database: str, arcade_user: str, arcade_password: str,
                 cache_url: str | None = None, dimensions: int, model: str, qdrant_key: str = "",
                 allow_internal_http: bool = False, http_transport=None, readonly: bool = False):
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", arcade_database):
            raise ValueError("Use a bounded explicit graph database identifier")
        if not 1 <= dimensions <= 8192 or not model or not arcade_user or not arcade_password:
            raise ValueError("Explicit index model, dimensions and graph credentials are required")
        cache = urlsplit(cache_url or "")
        if not readonly and (cache.scheme not in {"redis", "rediss"} or not cache.hostname or cache.query or cache.fragment
                or (cache.scheme == "redis" and cache.hostname not in {"127.0.0.1", "localhost", "::1"}
                    and not allow_internal_http)):
            raise ValueError("Use a protected explicit Valkey connection")
        self.identity, self.model, self.dimensions = identity, model, dimensions
        self.readonly = readonly
        self.collection = "ec_" + identity.pipeline
        self.qdrant_url = checked_origin(qdrant_url, allow_internal_http=allow_internal_http)
        self.arcade_url = checked_origin(arcade_url, allow_internal_http=allow_internal_http)
        self.database = arcade_database
        self._arcade_auth = (arcade_user, arcade_password)
        self._qdrant_headers = {"api-key": qdrant_key} if qdrant_key else {}
        self.http = httpx.AsyncClient(timeout=3, trust_env=False, follow_redirects=False,
                                     transport=http_transport)
        self.cache = None
        if not readonly:
            from redis.asyncio import Redis
            self.cache = Redis.from_url(cache_url, socket_connect_timeout=3, socket_timeout=3,
                                        decode_responses=True, max_connections=8)

    async def _request(self, method, url, **kwargs):
        # Do not buffer an unbounded error/response from a compromised index.
        async with self.http.stream(method, url, **kwargs) as response:
            response.raise_for_status()
            raw = bytearray()
            async for block in response.aiter_bytes():
                raw.extend(block)
                if len(raw) > 2 * 1024 * 1024:
                    raise ValueError("Index response exceeded the response budget")
        value = json.loads(raw) if raw else {}
        if not isinstance(value, dict):
            raise ValueError("Invalid index response")
        return value

    async def sql(self, command: str, params=None, *, script: bool = False, session: str | None = None):
        if self.readonly and (command != self._NEIGHBORS or script or session is not None):
            raise PermissionError("API graph clients admit only the fixed bounded neighbor query")
        value = await self._request("POST", self.arcade_url + "/api/v1/command/" + self.database,
            auth=self._arcade_auth, headers={"arcadedb-session-id": session} if session else {},
            json={"language": "sqlscript" if script else "sql",
                                         "command": command, "params": params or {}})
        rows = value.get("result", [])
        if not isinstance(rows, list) or len(rows) > 256:
            raise ValueError("Invalid or oversized graph result")
        return rows

    async def _transaction(self, action: str, session: str | None = None):
        async with self.http.stream("POST", self.arcade_url + "/api/v1/" + action + "/" + self.database,
                auth=self._arcade_auth, headers={"arcadedb-session-id": session} if session else {}) as response:
            response.raise_for_status()
            if response.headers.get("arcadedb-session-expired"):
                raise ValueError("Graph transaction expired")
            if action == "begin":
                value = response.headers.get("arcadedb-session-id", "")
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
                    raise ValueError("Graph did not return a valid transaction identity")
                return value

    async def _vertex(self, key: str, session: str):
        rows = await self.sql("UPDATE ECEntity SET key=:key UPSERT RETURN AFTER WHERE key=:key",
                              {"key": key}, session=session)
        rid = rows[0].get("@rid", "") if len(rows) == 1 else ""
        if not re.fullmatch(r"#[0-9]+:[0-9]+", rid):
            raise ValueError("Graph did not return a valid vertex identity")
        return rid

    async def provision(self, *, create_graph_database: bool = False):
        """Operator action only. Runtime never creates schemas or chooses a DB."""
        if self.readonly:
            raise PermissionError("The API cannot provision derived storage")
        if create_graph_database:
            await self._request("POST", self.arcade_url + "/api/v1/server", auth=self._arcade_auth,
                                json={"command": "create database " + self.database})
        try:
            existing = await self._request("GET", self.qdrant_url + "/collections/" + self.collection,
                                           headers=self._qdrant_headers)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
            existing = None
        if existing is None:
            await self._request("PUT", self.qdrant_url + "/collections/" + self.collection,
                headers=self._qdrant_headers, json={"vectors": {"size": self.dimensions, "distance": "Cosine"}})
        else:
            config = existing["result"]["config"]["params"]["vectors"]
            if config.get("size") != self.dimensions or config.get("distance") != "Cosine":
                raise ValueError("Existing vector collection has a different model/dimension contract")
        for statement in (
            "CREATE VERTEX TYPE ECEntity IF NOT EXISTS",
            "CREATE PROPERTY ECEntity.key IF NOT EXISTS STRING",
            "CREATE INDEX IF NOT EXISTS ON ECEntity (key) UNIQUE",
            "CREATE EDGE TYPE ECLink IF NOT EXISTS",
            "CREATE PROPERTY ECLink.record_key IF NOT EXISTS STRING",
            "CREATE PROPERTY ECLink.source_key IF NOT EXISTS STRING",
            "CREATE INDEX IF NOT EXISTS ON ECLink (record_key) NOTUNIQUE",
            "CREATE INDEX IF NOT EXISTS ON ECLink (source_key) NOTUNIQUE",
        ):
            await self.sql(statement)
        await self.cache.ping()

    def entity(self, tenant, value):
        return self.identity.entity(tenant, value)

    async def project(self, row, payload: dict, vector: list[float], *, active: bool):
        if self.readonly:
            raise PermissionError("The API cannot mutate derived storage")
        tenant, project, ident = row["tenant"], row["project"], row["id"]
        if (len(vector) != self.dimensions or any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in vector)) and active:
            raise ValueError("Index vector violates the configured model/dimension contract")
        record_key = self.identity.record(tenant, project, ident)
        base = self.qdrant_url + "/collections/" + self.collection + "/points"
        if active:
            await self._request("PUT", base + "?wait=true", headers=self._qdrant_headers, json={"points": [{
                "id": ident, "vector": vector, "payload": {"tenant": tenant, "project": project,
                "record_id": ident, "version": row["version"], "model": self.model}}]})
        else:
            await self._request("POST", base + "/delete?wait=true", headers=self._qdrant_headers,
                                json={"points": [ident]})
        # Snapshot replacement is one graph transaction. Replays produce the
        # same edge set. Orphan hashed vertices are retained, never traversed
        # without an authorized current source edge.
        params = {"record_key": record_key, "tenant": tenant, "project": project,
                  "record_id": ident, "version": row["version"]}
        session = await self._transaction("begin")
        try:
            await self.sql("DELETE FROM ECLink WHERE record_key=:record_key", params, session=session)
            if active:
                for number, link in enumerate(payload.get("knowledge_links", [])):
                    source, target = self.entity(tenant, link["subject"]), self.entity(tenant, link["object"])
                    source_rid = await self._vertex(source, session)
                    target_rid = await self._vertex(target, session)
                    await self.sql(f"CREATE EDGE ECLink FROM {source_rid} TO {target_rid} "
                        "SET record_key=:record_key,tenant=:tenant,project=:project,record_id=:record_id,"
                        "version=:version,link_index=:link_index,source_key=:source,target_key=:target",
                        {**params, "link_index": number, "source": source, "target": target}, session=session)
            await self._transaction("commit", session)
        except BaseException:
            # A failed/ambiguous commit is retried from the canonical snapshot.
            # Never acknowledge an incomplete graph replacement.
            try:
                await self._transaction("rollback", session)
            except Exception:
                pass
            raise
        cache_key = "ec:" + self.identity.pipeline + ":" + record_key
        if active:
            await self.cache.set(cache_key, json.dumps({"version": row["version"], "payload": row["payload"]}), ex=3600)
        else:
            await self.cache.delete(cache_key)

    async def neighbors(self, tenant: str, entity: str, *, identifiers: list[str], limit: int = 64):
        if not 1 <= limit <= 64:
            raise ValueError("Graph neighbor limit exceeds the query budget")
        if len(identifiers) > 2000 or any(not isinstance(value, str) or len(value) > 200 for value in identifiers):
            raise ValueError("Graph query exceeds the authorized candidate budget")
        if not identifiers:
            return []
        return await self.sql(self._NEIGHBORS,
                              {"tenant": tenant, "source": self.entity(tenant, entity), "identifiers": identifiers, "limit": limit})

    async def search(self, tenant: str, vector: list[float], identifiers: list[str], limit: int):
        if not identifiers:
            return []
        if len(identifiers) > 2000 or len(vector) != self.dimensions or not 1 <= limit <= 20:
            raise ValueError("Vector query exceeds the authorized candidate budget")
        value = await self._request("POST", self.qdrant_url + "/collections/" + self.collection + "/points/search",
            headers=self._qdrant_headers, json={"vector": vector, "limit": limit, "with_payload": True,
                "filter": {"must": [{"key": "tenant", "match": {"value": tenant}}, {"has_id": identifiers}]}})
        result = value.get("result", [])
        if not isinstance(result, list) or len(result) > limit:
            raise ValueError("Invalid bounded vector result")
        return result

    async def close(self):
        await self.http.aclose()
        if self.cache is not None:
            await self.cache.aclose()
