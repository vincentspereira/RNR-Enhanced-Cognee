"""Shared ASGI authentication, tenant binding, and bounded request admission."""
from __future__ import annotations

import json
import os
import asyncio
import time

from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from src.multi_tenant import TenantContext, tenant_required, validate_tenant_id
from src.security.auth import Role
from src.security.enterprise_auth import AuthError, authenticate_request, authorize, route_required_permission
from src.security.request_context import principal_context, validate_identity_fields


class SecurityBoundary:
    """Read at most the configured byte budget, then replay the bounded body.

    No reliance on Content-Length or client-supplied tenant/agent identity. A
    native ASGI middleware also keeps identity context active for streaming.
    """

    def __init__(self, app, *, dashboard: bool = False):
        self.app = app
        self.dashboard = dashboard
        self._active = 0
        try:
            self._capacity = int(os.getenv("ENHANCED_MAX_CONCURRENT_REQUESTS", "32"))
            if not 1 <= self._capacity <= 256:
                raise ValueError
        except ValueError as exc:
            raise ValueError("Concurrent request capacity must be between 1 and 256") from exc

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") == "/health/live":
            await self.app(scope, receive, send)
            return
        # No await between admission check/increment: requests on this ASGI
        # loop cannot create an unbounded queue of waiting embedding jobs.
        if self._active >= self._capacity:
            await JSONResponse({"detail": "Service busy; retry the same request identity"}, status_code=503)(scope, receive, send)
            return
        self._active += 1
        try:
            await self._handle(scope, receive, send)
        finally:
            self._active -= 1

    async def _handle(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        headers = Headers(scope=scope)
        public = path in {"/health", "/health/live", "/health/ready"}
        if path == "/metrics" and os.getenv("ENHANCED_METRICS_PUBLIC", "0") == "1":
            public = True
        if public:
            await self.app(scope, receive, send)
            return
        try:
            principal = authenticate_request(headers)
            canonical = bool(getattr(getattr(scope.get("app"), "state", None), "canonical_memory", False))
            compatible = canonical and (path.startswith(("/api/", "/tools/", "/mcp/"))
                                         or path in {"/stats", "/memory/add", "/memory/search"})
            if principal.claims.get("project_id") and not (path == "/v1/memories" or path.startswith("/v1/memories/") or compatible):
                raise AuthError(403, "Project credentials are restricted to the project-memory API.")
            permission = route_required_permission(scope["method"], path)
            authorize(principal, permission)
            selected = headers.get("x-tenant-id") or principal.tenant_id
            if principal.claims.get("project_id") and selected != principal.tenant_id:
                raise AuthError(403, "Tenant header conflicts with project credential scope.")
            if principal.role != Role.ADMIN:
                if not principal.tenant_id:
                    raise AuthError(403, "Restricted credentials require an assigned tenant.")
                if selected and selected != principal.tenant_id:
                    raise AuthError(403, "Tenant header conflicts with credential scope.")
                selected = principal.tenant_id
            if selected:
                try:
                    selected = validate_tenant_id(selected)
                except ValueError as exc:
                    raise AuthError(400, str(exc)) from exc
            elif tenant_required():
                raise AuthError(400, "An assigned tenant or X-Tenant-ID is required.")
            service = getattr(getattr(scope.get("app"), "state", None), "memory_service", None)
            if service is not None and hasattr(service, "admit_request"):
                try:
                    budget = int(os.getenv("ENHANCED_RATE_LIMIT_PER_MINUTE", "120"))
                    if budget <= 0:
                        raise ValueError
                except ValueError as exc:
                    raise AuthError(503, "Invalid request budget configuration.") from exc
                try:
                    await service.admit_request(principal, budget)
                except ValueError as exc:
                    raise AuthError(403, "A credential assigned to a tenant and project is required.") from exc
            raw_cap = os.getenv("ENHANCED_MAX_PAYLOAD_BYTES", "1048576")
            try:
                cap = int(raw_cap)
                if cap <= 0:
                    raise ValueError
            except ValueError as exc:
                raise AuthError(503, "Invalid request-size limit configuration.") from exc
            chunks = []
            size = 0
            try:
                body_timeout = float(os.getenv("ENHANCED_BODY_TIMEOUT_SECONDS", "10"))
                if not 0 < body_timeout <= 30:
                    raise ValueError
            except ValueError as exc:
                raise AuthError(503, "Invalid request-body time limit configuration.") from exc
            deadline = time.monotonic() + body_timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AuthError(408, "Request body exceeded its time limit.")
                try:
                    message = await asyncio.wait_for(receive(), timeout=remaining)
                except asyncio.TimeoutError as exc:
                    raise AuthError(408, "Request body exceeded its time limit.") from exc
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > cap:
                    raise AuthError(413, "Request exceeds the configured byte limit.")
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break
            body = b"".join(chunks)
            if body and "application/json" in headers.get("content-type", ""):
                try:
                    payload = json.loads(body)
                except (ValueError, UnicodeError) as exc:
                    raise AuthError(422, "Request must contain valid JSON.") from exc
                if isinstance(payload, dict):
                    validate_identity_fields(payload.get("arguments", payload), principal)
            scope.setdefault("state", {})["principal"] = principal
            scope["state"]["tenant_id"] = selected
            sent_body = False

            async def replay():
                nonlocal sent_body
                if not sent_body:
                    sent_body = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            with principal_context(principal):
                if selected:
                    with TenantContext(selected):
                        await self.app(scope, replay, send)
                else:
                    await self.app(scope, replay, send)
        except AuthError as exc:
            await JSONResponse({"detail": exc.detail}, status_code=exc.status_code)(scope, receive, send)
