"""Reviewed legacy HTTP/tool aliases, all delegated to one canonical service.

No SQL, filesystem, importer, LLM or derived-store mutation lives in this layer.
Historical data needs the explicit copy-only migration before it appears here.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from src.memory_service import MemoryScope
from src.security.enterprise_auth import AuthError, authorize, tool_required_permission
from src.security.request_context import validate_identity_fields


SUPPORTED_TOOLS = frozenset({"add_memory", "remember", "search_memories", "search", "recall", "get_memories",
    "list_data", "get_memory", "get_memory_detail", "update_memory", "delete_memory", "forget_memory",
    "get_memory_history", "list_agents", "get_stats", "health"})


def canonical_mode() -> bool:
    import os
    selected = os.getenv("ENHANCED_MEMORY_MODE")
    if selected is not None and selected not in {"canonical", "legacy"}:
        raise ValueError("Choose canonical or legacy memory mode explicitly")
    return selected == "canonical" or selected is None and bool(os.getenv("ENHANCED_MEMORY_DATABASE_URL"))


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    arguments: dict[str, Any] = Field(default_factory=dict)


async def dispatch(service, principal, tool, arguments):
    from src.security.tool_policy import policy_for
    policy_for(tool, canonical=True)
    if tool not in SUPPORTED_TOOLS:
        raise AuthError(403, "This legacy tool is not admitted to canonical project memory")
    authorize(principal, tool_required_permission(tool))
    validate_identity_fields(arguments, principal)
    args = dict(arguments)
    for name in ("tenant_id", "project_id", "agent_id", "user_id"):
        # Even administrator tool callers use the project's signed mapping.
        expected = {"tenant_id": principal.tenant_id, "project_id": principal.claims.get("project_id"),
                    "agent_id": principal.claims.get("agent_id") or principal.subject,
                    "user_id": principal.subject}[name]
        if name in args and args.pop(name) not in (None, expected):
            raise AuthError(403, "Compatibility arguments cannot override signed identity")
    scope = MemoryScope.from_principal(principal)

    def require(allowed, required=()):
        if set(args) - set(allowed) or not set(required) <= set(args):
            raise ValueError("Unsupported compatibility arguments; use the canonical API contract")

    if tool in {"add_memory", "remember"}:
        require({"content", "data", "idempotency_key", "category", "memory_category", "metadata", "evidence",
                 "fact_key", "expires_at", "knowledge_links"}, {"idempotency_key"})
        content = args.pop("content", args.pop("data", None))
        if not isinstance(content, str):
            raise ValueError("Memory content is required")
        metadata = args.pop("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        category = args.pop("category", args.pop("memory_category", "general"))
        from src.memory_api import RememberRequest
        body = RememberRequest(content=content, category=category, metadata=metadata, **args)
        return await service.remember(scope, **body.model_dump())
    if tool in {"search_memories", "search", "recall"}:
        require({"query", "limit", "top_k", "include_shared"}, {"query"})
        from src.memory_api import RecallRequest
        body = RecallRequest(query=args["query"], limit=args.get("limit", args.get("top_k", 5)),
                             include_shared=args.get("include_shared", True))
        return await service.recall(scope, **body.model_dump())
    if tool in {"get_memories", "list_data"}:
        require({"limit", "offset", "category", "include_shared"})
        return await service.list_records(scope, **args)
    if tool in {"get_memory", "get_memory_detail", "get_memory_history"}:
        require({"memory_id", "limit", "before_version"} if tool == "get_memory_history" else {"memory_id"}, {"memory_id"})
        ident = args.pop("memory_id")
        return await service.history(scope, ident, **args) if tool == "get_memory_history" else await service.get(scope, ident)
    if tool in {"update_memory", "delete_memory", "forget_memory"}:
        deleting = tool != "update_memory"
        require({"memory_id", "expected_version", "content", "evidence", "knowledge_links", "metadata", "category"}
                if not deleting else {"memory_id", "expected_version"}, {"memory_id", "expected_version"})
        ident = args.pop("memory_id")
        from src.memory_api import CorrectionRequest, VersionRequest
        body = VersionRequest(**args) if deleting else CorrectionRequest(**args)
        return await service.correct(scope, ident, retract=deleting, **body.model_dump())
    require(set())
    return await service.agents(scope) if tool == "list_agents" else await service.status(scope)


def dashboard_record(record):
    metadata = record.get("metadata", {})
    return dict(memory_id=record["id"], content=record["content"], data_type="text",
        memory_type=record.get("category"), memory_concept=metadata.get("memory_concept"),
        summary=None, created_at=record["created_at"], updated_at=record["updated_at"],
        char_count=len(record["content"]), estimated_tokens=(len(record["content"])+3)//4,
        agent_id=record.get("provenance", {}).get("agent_id"), tags=metadata.get("tags", []),
        version=record["version"], project_id=record["project_id"], state=record["state"],
        before_state=metadata.get("before_state"), after_state=metadata.get("after_state"),
        files=metadata.get("files", []), facts=metadata.get("facts", []), metadata=metadata)


class DashboardWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=65536)
    idempotency_key: str = Field(min_length=1, max_length=200)
    agent_id: str | None = None
    memory_type: str = Field(default="general", min_length=1, max_length=100)
    memory_concept: str | None = Field(default=None, max_length=100)
    before_state: str | None = None
    after_state: str | None = None
    files: list[str] = Field(default_factory=list, max_length=32)
    facts: list[str] = Field(default_factory=list, max_length=32)
    tags: list[str] = Field(default_factory=list, max_length=32)


class DashboardCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    content: str | None = Field(default=None, min_length=1, max_length=65536)
    memory_type: str | None = Field(default=None, min_length=1, max_length=100)
    memory_concept: str | None = None
    before_state: str | None = None
    after_state: str | None = None
    files: list[str] | None = Field(default=None, max_length=32)
    facts: list[str] | None = Field(default=None, max_length=32)


def adapter_router():
    router = APIRouter()

    def service(request):
        return request.app.state.memory_service

    def scope(request):
        return MemoryScope.from_principal(request.state.principal)

    @router.post("/tools/{tool_name}")
    async def tools(tool_name: str, body: ToolRequest, request: Request):
        return {"result": await dispatch(service(request), request.state.principal, tool_name, body.arguments)}

    @router.post("/mcp/{tool_name}")
    async def named_tool(tool_name: str, request: Request, body: dict[str, Any] = Body(...)):
        # These are legacy JSON aliases, not an MCP protocol transport.
        return await dispatch(service(request), request.state.principal, tool_name, body)

    @router.get("/mcp/list_agents")
    async def named_agents(request: Request):
        return await dispatch(service(request), request.state.principal, "list_agents", {})

    @router.post("/memory/add")
    async def old_add(request: Request, body: dict[str, Any] = Body(...)):
        return await dispatch(service(request), request.state.principal, "add_memory", body)

    @router.post("/memory/search")
    async def old_search(request: Request, body: dict[str, Any] = Body(...)):
        return await dispatch(service(request), request.state.principal, "search_memories", body)

    @router.get("/api/memories")
    async def listing(request: Request, limit: int = Query(50, ge=1, le=200),
                      offset: int = Query(0, ge=0, le=100000), agent_id: str | None = None,
                      memory_type: str | None = None, memory_concept: str | None = None):
        if memory_concept:
            raise ValueError("Use canonical category or semantic recall for concept filtering")
        page = await service(request).list_records(scope(request), limit=limit, offset=offset,
                                                   category=memory_type, agent=agent_id)
        return JSONResponse([dashboard_record(record) for record in page["results"]],
                            headers={"X-Next-Offset": str(page["next_offset"]) if page["next_offset"] is not None else ""})

    @router.get("/api/memories/{memory_id}")
    async def get(memory_id: str, request: Request):
        return dashboard_record(await service(request).get(scope(request), memory_id))

    @router.post("/api/memories", status_code=201)
    async def remember(body: DashboardWrite, request: Request):
        validate_identity_fields({"agent_id": body.agent_id}, request.state.principal)
        declarations = body.model_dump(exclude={"content", "idempotency_key", "agent_id", "memory_type"})
        record = await service(request).remember(scope(request), body.content, idempotency_key=body.idempotency_key,
            category=body.memory_type, metadata=declarations)
        return dashboard_record(record)

    @router.patch("/api/memories/{memory_id}")
    async def correct(memory_id: str, body: DashboardCorrection, request: Request):
        current = await service(request).get(scope(request), memory_id)
        values = body.model_dump(exclude_unset=True)
        metadata = dict(current.get("metadata", {}))
        for name in ("memory_concept", "before_state", "after_state", "files", "facts"):
            if name in values:
                metadata[name] = values[name]
        await service(request).correct(scope(request), memory_id, expected_version=body.expected_version,
            content=body.content or current["content"], metadata=metadata, category=body.memory_type)
        return dashboard_record(await service(request).get(scope(request), memory_id))

    @router.delete("/api/memories/{memory_id}")
    @router.post("/api/memories/{memory_id}/retract")
    async def retract(memory_id: str, request: Request, expected_version: int = Query(..., ge=1)):
        result = await service(request).correct(scope(request), memory_id, expected_version=expected_version, retract=True)
        return dict(result, history_preserved=True)

    @router.get("/api/search")
    async def search(request: Request, query: str = Query(..., min_length=1, max_length=2000),
                     limit: int = Query(20, ge=1, le=20), agent_id: str | None = None):
        if agent_id is not None:
            validate_identity_fields({"agent_id": agent_id}, request.state.principal)
        found = await service(request).recall(scope(request), query, limit=limit)
        return {"query": query, "result_count": len(found["results"]),
                "results": [dashboard_record(record) for record in found["results"]],
                "retrieval": found["retrieval"], "token_savings": {"measured": False}}

    @router.get("/api/agents")
    async def agents(request: Request):
        return (await service(request).agents(scope(request)))["agents"]

    @router.get("/stats")
    @router.get("/api/stats")
    async def stats(request: Request):
        value = await service(request).status(scope(request))
        return dict(value, total_memories=value["active_records"], total_sessions=0, active_sessions=0,
                    avg_tokens_per_memory=0, token_efficiency_percent=0, sessions_available=False,
                    token_statistics_available=False, database_status={"postgresql": True}, server_uptime="unmeasured")

    @router.get("/api/timeline/{memory_id}")
    async def timeline(memory_id: str, request: Request):
        return await service(request).history(scope(request), memory_id)

    @router.get("/api/security/user")
    async def user(request: Request):
        principal = request.state.principal
        return {"user_id": principal.subject, "role": principal.role.value,
                "permissions": [p.value for p in principal.permissions]}

    @router.get("/api/sessions")
    async def sessions():
        # Transcript persistence was expressly excluded. Report capability
        # absence instead of fabricating session summaries from arbitrary data.
        raise AuthError(501, "Session transcripts are not captured by canonical project memory")

    return router
