"""Restricted native memory API. Reviewed ingestion only; no administrative tools."""
from __future__ import annotations

import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.memory_keys import canonical_cipher_from_environment
from src.memory_service import MemoryConflict, MemoryClarificationRequired, MemoryScope, MemoryService
from src.memory_contracts import MemoryEvidence
from src.index_contracts import KnowledgeLink
from src.security.enterprise_auth import AuthError
from src.security.http_boundary import SecurityBoundary


class RememberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=65536)
    idempotency_key: str = Field(min_length=1, max_length=200)
    category: str = Field(default="general", min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    evidence: Optional[MemoryEvidence] = None
    fact_key: Optional[str] = Field(default=None, pattern=r"^[a-z][a-z0-9_.:-]{0,159}$")
    knowledge_links: list[KnowledgeLink] = Field(default_factory=list, max_length=16)


class IngestRequest(BaseModel):
    """Reviewed ingestion (Stage D family 1): exactly one source, chunked and
    stored through the normal remember() admission with provenance."""
    model_config = ConfigDict(extra="forbid")
    url: Optional[str] = Field(default=None, max_length=2048)
    text: Optional[str] = Field(default=None, min_length=1, max_length=131072)
    title: Optional[str] = Field(default=None, max_length=200)
    category: str = Field(default="ingested", min_length=1, max_length=100)
    base_key: str = Field(min_length=8, max_length=100,
                          pattern=r"^[a-z0-9][a-z0-9_-]*$")


class SummarizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=20, ge=2, le=50)
    title: Optional[str] = Field(default=None, max_length=200)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)


class ConsolidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=20, ge=2, le=50)


class TranslateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=8000)
    target_language: str = Field(min_length=2, max_length=32)


class DetectLanguageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=8000)


class RecallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    include_shared: bool = True


class CorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    content: str = Field(min_length=1, max_length=65536)
    evidence: Optional[MemoryEvidence] = None
    knowledge_links: Optional[list[KnowledgeLink]] = Field(default=None, max_length=16)
    metadata: Optional[dict[str, Any]] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)


class ConnectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity: str = Field(min_length=1, max_length=160)
    depth: int = Field(default=2, ge=1, le=3)
    limit: int = Field(default=10, ge=1, le=20)
    include_shared: bool = True


class VersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class ShareRequest(VersionRequest):
    target_project: str = Field(min_length=1, max_length=32)
    revoke: bool = False


class LibraryMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    library: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    member_project: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    admitted: bool
    can_publish: bool = False


class LibraryPublicationRequest(VersionRequest):
    library: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    revoke: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncpg
    from src.mcp_security import enforce_production_auth
    enforce_production_auth()
    from src.security.enterprise_auth import jwt_secret_configured, oidc_configured
    if not jwt_secret_configured() and not oidc_configured():
        raise RuntimeError("The project-memory API requires a scoped JWT/OIDC verifier")
    cipher = canonical_cipher_from_environment()
    # No fallback credentials, local database, or generated encryption key.
    pool = await asyncpg.create_pool(os.environ["ENHANCED_MEMORY_DATABASE_URL"], min_size=1, max_size=5,
                                    command_timeout=10)
    try:
        embedder = None
        if os.getenv("ENHANCED_EMBEDDING_MODEL"):
            from src.local_embeddings import LocalEmbeddings
            embedder = LocalEmbeddings(os.environ["ENHANCED_EMBEDDING_MODEL"],
                                       os.environ["ENHANCED_MODEL_CACHE"])
        derived = None
        if os.getenv("ENHANCED_INDEX_CONFIG"):
            from src.index_runtime import configured_sinks
            from src.recall_service import DerivedRecall
            derived = DerivedRecall(configured_sinks(readonly=True))
            if embedder is None or embedder.model != derived.sinks.model:
                raise ValueError("Configured index recall requires the same prepared local embedding model")
        service = MemoryService(pool, cipher, embedder, derived=derived)
        # Provisioning belongs to a separate operator, never runtime credentials.
        await service.check_schema()
        app.state.memory_service = service
        from src import llm_summarize
        app.state.llm_route = llm_summarize.load_route(
            os.environ.get("CREDENTIALS_DIRECTORY"))
        app.state.llm_budget = llm_summarize.TokenBudget()
        yield
    finally:
        if 'derived' in locals() and derived is not None:
            await derived.sinks.close()
        await pool.close()


def create_app(service: Optional[MemoryService] = None) -> FastAPI:
    app = FastAPI(title="Enhanced Cognee Project Memory", version="1.1.0", lifespan=lifespan)
    app.add_middleware(SecurityBoundary)
    # Browser dashboards are separate processes. Admit only explicitly named
    # origins, never a wildcard carrying a private project's token.
    origins = [value.strip() for value in os.getenv("ENHANCED_DASHBOARD_ORIGINS", "").split(",") if value.strip()]
    if origins:
        from src.index_sinks import checked_origin
        from fastapi.middleware.cors import CORSMiddleware
        checked = [checked_origin(value) for value in origins]
        if len(checked) > 8:
            raise ValueError("Configure at most eight explicit dashboard origins")
        app.add_middleware(CORSMiddleware, allow_origins=checked, allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"],
            expose_headers=["X-Next-Offset"])
    app.state.canonical_memory = True
    if service is not None:
        app.state.memory_service = service

    def store() -> MemoryService:
        return app.state.memory_service

    def scope(request: Request) -> MemoryScope:
        return MemoryScope.from_principal(request.state.principal)

    @app.exception_handler(AuthError)
    async def denied(request, exc):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(MemoryConflict)
    async def conflict(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(MemoryClarificationRequired)
    async def clarify(request, exc):
        return JSONResponse({"detail": str(exc), "clarification_required": True}, status_code=409)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail": "Memory not found in this scope"}, status_code=404)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def invalid_fields(request, exc):
        # Validation errors must not echo a submitted password or private field.
        return JSONResponse({"detail": "Invalid memory fields; check the API contract"}, status_code=422)

    @app.exception_handler(Exception)
    async def unavailable(request, exc):
        # Never leak database URLs, model configuration or decrypted content.
        return JSONResponse({"detail": "Memory service unavailable"}, status_code=503)

    @app.get("/health/live")
    async def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    @app.get("/health")
    async def ready():
        try:
            await store().check_schema()
            return {"ready": True, "retrieval": "semantic" if store().embedder else "text",
                    "encryption": "AES-256-GCM", "graph": "configured" if store().derived else "unavailable",
                    "index_readiness": "see_authenticated_status" if store().derived else "unconfigured",
                    "sharing": "reviewed_projects_and_libraries"}
        except Exception:
            return JSONResponse({"ready": False}, status_code=503)

    @app.post("/v1/memories")
    async def remember(body: RememberRequest, request: Request):
        return await store().remember(scope(request), **body.model_dump())

    @app.post("/v1/memories/ingest")
    async def ingest(body: IngestRequest, request: Request):
        import asyncio

        from src.ingestion import (IngestRefused, build_records, chunk_text,
                                   fetch_public_text)
        if (body.url is None) == (body.text is None):
            raise IngestRefused("Provide exactly one of url or text")
        if body.url is not None:
            document, content_type = await asyncio.to_thread(fetch_public_text, body.url)
            label = body.url
        else:
            document, content_type = body.text, "inline"
            label = body.title or "inline document"
        chunks = chunk_text(document)
        records = build_records(chunks, label, body.category, body.base_key)
        stored = []
        for record in records:
            stored.append(await store().remember(scope(request), **record))
        return {"ingested": len(stored), "chunks": len(chunks),
                "content_type": content_type,
                "record_ids": [row.get("id") or row.get("record_id")
                               for row in stored if isinstance(row, dict)]}

    def _llm():
        from src import llm_summarize
        route = getattr(app.state, "llm_route", None)
        if route is None:
            raise llm_summarize.LlmUnavailable(
                "The model route is not configured for this service")
        budget = getattr(app.state, "llm_budget", None)
        return llm_summarize, route, budget

    def _project(request):
        return scope(request).project

    @app.post("/v1/memories/summarize")
    async def summarize(body: SummarizeRequest, request: Request):
        import asyncio
        import uuid

        llm, route, budget = _llm()
        records = await store().list_records(
            scope(request), limit=body.limit, offset=0,
            category=body.category, agent=None, include_shared=True)
        rows = records if isinstance(records, list) else \
            (records.get("records") or records.get("items") or [])
        messages = llm.summarize_messages(rows, body.title)
        if not budget.allows(route, _project(request), 4000):
            raise llm.LlmUnavailable("The daily model budget for this project is exhausted")
        text, tokens = await asyncio.to_thread(llm.chat, route, messages)
        budget.charge(_project(request), tokens)
        stored = await store().remember(
            scope(request), content=text[:65536],
            idempotency_key="summarize-" + uuid.uuid4().hex,
            category="summary",
            metadata={"origin": "summarize", "source": "llm_summary",
                      "sources": min(len(rows), 100), "model": route["model"]})
        return {"summary": text, "record_id": stored.get("id") if isinstance(stored, dict) else None,
                "sources": len(rows), "tokens_used": tokens,
                "budget_used_today": budget.used(_project(request))}

    @app.get("/v1/memories/summarization/status")
    async def summarization_status(request: Request):
        route = getattr(app.state, "llm_route", None)
        budget = getattr(app.state, "llm_budget", None)
        return {"configured": route is not None,
                "model": route["model"] if route else None,
                "daily_token_cap": route["daily_token_cap"] if route else None,
                "used_today": budget.used(_project(request)) if budget else 0,
                "project_id": _project(request)}

    @app.post("/v1/memories/consolidation/candidates")
    async def consolidation(body: ConsolidateRequest, request: Request):
        import asyncio

        llm, route, budget = _llm()
        records = await store().list_records(
            scope(request), limit=body.limit, offset=0,
            category=None, agent=None, include_shared=True)
        rows = records if isinstance(records, list) else \
            (records.get("records") or records.get("items") or [])
        messages = llm.consolidation_messages(rows)
        if not budget.allows(route, _project(request), 4000):
            raise llm.LlmUnavailable("The daily model budget for this project is exhausted")
        reply, tokens = await asyncio.to_thread(llm.chat, route, messages,
                                                max_tokens=600)
        budget.charge(_project(request), tokens)
        return {"candidates": llm.parse_consolidation(reply), "compared": len(rows),
                "tokens_used": tokens, "report_only": True}

    @app.post("/v1/memories/translate")
    async def translate(body: TranslateRequest, request: Request):
        import asyncio

        llm, route, budget = _llm()
        messages = llm.translate_messages(body.text, body.target_language)
        if not budget.allows(route, _project(request), 4000):
            raise llm.LlmUnavailable("The daily model budget for this project is exhausted")
        translation, tokens = await asyncio.to_thread(llm.chat, route, messages,
                                                      max_tokens=2000)
        budget.charge(_project(request), tokens)
        return {"translation": translation, "target_language": body.target_language,
                "tokens_used": tokens, "stored": False}

    @app.post("/v1/memories/detect-language")
    async def detect_language(body: DetectLanguageRequest):
        from src.llm_summarize import detect_language as detect
        return detect(body.text)

    @app.post("/v1/memories/recall")
    async def recall(body: RecallRequest, request: Request):
        return await store().recall(scope(request), **body.model_dump())

    @app.get("/v1/memories")
    async def list_records(request: Request, limit: int = Query(50, ge=1, le=200),
                           offset: int = Query(0, ge=0, le=100000), category: Optional[str] = None,
                           agent: Optional[str] = None, include_shared: bool = True):
        return await store().list_records(scope(request), limit=limit, offset=offset, category=category,
                                          agent=agent, include_shared=include_shared)

    @app.get("/v1/memories/agents")
    async def agents(request: Request):
        return await store().agents(scope(request))

    @app.post("/v1/memories/connections")
    async def connections(body: ConnectionRequest, request: Request):
        return await store().connections(scope(request), **body.model_dump())

    @app.get("/v1/memories/status")
    async def status(request: Request):
        return await store().status(scope(request))

    @app.post("/v1/memories/library/membership")
    async def library_member(body: LibraryMemberRequest, request: Request):
        return await store().set_library_member(scope(request), **body.model_dump())

    @app.post("/v1/memories/{record_id}/library")
    async def library_publish(record_id: str, body: LibraryPublicationRequest, request: Request):
        return await store().publish_library(scope(request), record_id, **body.model_dump())

    @app.get("/v1/memories/{record_id}")
    async def get(record_id: str, request: Request):
        return await store().get(scope(request), record_id)

    @app.get("/v1/memories/{record_id}/history")
    async def history(record_id: str, request: Request, limit: int = Query(50, ge=1, le=100),
                      before_version: Optional[int] = Query(None, ge=1)):
        return await store().history(scope(request), record_id, limit=limit, before_version=before_version)

    @app.patch("/v1/memories/{record_id}")
    async def correct(record_id: str, body: CorrectionRequest, request: Request):
        return await store().correct(scope(request), record_id, **body.model_dump())

    @app.post("/v1/memories/{record_id}/retract")
    async def retract(record_id: str, body: VersionRequest, request: Request):
        return await store().correct(scope(request), record_id, retract=True, **body.model_dump())

    @app.post("/v1/memories/{record_id}/share")
    async def share(record_id: str, body: ShareRequest, request: Request):
        return await store().share(scope(request), record_id, **body.model_dump())

    from src.canonical_adapters import adapter_router
    app.include_router(adapter_router())
    return app


app = create_app()
