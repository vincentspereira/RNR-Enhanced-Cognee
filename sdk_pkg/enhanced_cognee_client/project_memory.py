"""Scoped canonical project-memory client, separate from legacy tool dispatch."""
from __future__ import annotations

import json
import math
from urllib.parse import quote, urlencode, urlsplit

import httpx


class MemoryRequestError(RuntimeError):
    def __init__(self, status: int | None, *, clarification_required=False):
        self.status_code = status
        self.clarification_required = clarification_required
        self.retry_same_identity = status is None or status in {408, 429, 500, 502, 503, 504}
        super().__init__("Memory request was refused or unavailable; no success was acknowledged")


class ProjectMemoryClient:
    def __init__(self, base_url: str, access_token: str, *, timeout=10, transport=None):
        uri = urlsplit(base_url)
        if (uri.scheme not in {"http", "https"} or not uri.hostname or uri.username or uri.password
                or uri.path not in {"", "/"} or uri.query or uri.fragment
                or any(ord(char) < 33 for char in base_url)
                or uri.scheme == "http" and uri.hostname not in {"localhost", "127.0.0.1", "::1"}):
            raise ValueError("Use an HTTPS service origin, or local loopback HTTP")
        if not access_token or any(char.isspace() for char in access_token) or len(access_token) > 16384:
            raise ValueError("A bounded project-scoped access token is required")
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 60:
            raise ValueError("Use a timeout between zero and sixty seconds")
        self._http = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout,
            headers={"Authorization": "Bearer " + access_token}, trust_env=False,
            follow_redirects=False, transport=transport)

    async def request(self, method, path, body=None):
        # Never let a caller-controlled route forward this project's bearer
        # credential to another origin, including network-path references.
        target = urlsplit(path)
        if (target.scheme or target.netloc or target.fragment or not target.path.startswith("/v1/memories")
                or target.path not in {"/v1/memories"} and not target.path.startswith("/v1/memories/")
                or "\\" in path or any(ord(char) < 33 for char in path)
                or any(part in {".", ".."} for part in target.path.split("/"))):
            raise ValueError("Only canonical memory routes on the configured origin are allowed")
        try:
            async with self._http.stream(method, path, json=body) as response:
                raw = bytearray()
                async for block in response.aiter_bytes():
                    raw.extend(block)
                    if len(raw) > 1024 * 1024:
                        raise MemoryRequestError(response.status_code)
                if not 200 <= response.status_code < 300:
                    try:
                        clarification = json.loads(raw).get("clarification_required") is True
                    except (ValueError, AttributeError):
                        clarification = False
                    raise MemoryRequestError(response.status_code, clarification_required=clarification)
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise MemoryRequestError(response.status_code)
                return value
        except (httpx.HTTPError, ValueError):
            raise MemoryRequestError(None) from None

    async def remember(self, content: str, idempotency_key: str, **declarations):
        return await self.request("POST", "/v1/memories", dict(declarations, content=content, idempotency_key=idempotency_key))

    async def recall(self, query: str, *, limit=5, include_shared=True):
        return await self.request("POST", "/v1/memories/recall", dict(query=query, limit=limit, include_shared=include_shared))

    async def get(self, record_id: str):
        return await self.request("GET", "/v1/memories/" + quote(record_id, safe=""))

    async def correct(self, record_id: str, content: str, expected_version: int, **declarations):
        return await self.request("PATCH", "/v1/memories/" + quote(record_id, safe=""),
                                  dict(declarations, content=content, expected_version=expected_version))

    async def retract(self, record_id: str, expected_version: int):
        return await self.request("POST", "/v1/memories/" + quote(record_id, safe="") + "/retract",
                                  {"expected_version": expected_version})

    async def list_records(self, *, limit=50, offset=0, include_shared=True):
        return await self.request("GET", "/v1/memories?" + urlencode(dict(limit=limit, offset=offset, include_shared=str(include_shared).lower())))

    async def history(self, record_id: str, *, limit=50, before_version=None):
        params = {"limit": limit}
        if before_version is not None:
            params["before_version"] = before_version
        return await self.request("GET", "/v1/memories/" + quote(record_id, safe="") + "/history?" + urlencode(params))

    async def connections(self, entity: str, *, depth=2, limit=10, include_shared=True):
        return await self.request("POST", "/v1/memories/connections", dict(entity=entity, depth=depth, limit=limit, include_shared=include_shared))

    async def status(self):
        return await self.request("GET", "/v1/memories/status")

    async def close(self):
        await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
