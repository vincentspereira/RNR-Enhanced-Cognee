"""Restricted native memory API. No arbitrary ingestion or administrative tools."""
from __future__ import annotations

import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field

from src.memory_keys import canonical_cipher_from_environment
from src.memory_service import MemoryConflict, MemoryClarificationRequired, MemoryScope, MemoryService
from src.memory_contracts import MemoryEvidence
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
        service = MemoryService(pool, cipher, embedder)
        # Provisioning belongs to a separate operator, never runtime credentials.
        await service.check_schema()
        app.state.memory_service = service
        yield
    finally:
        await pool.close()


def create_app(service: Optional[MemoryService] = None) -> FastAPI:
    app = FastAPI(title="Enhanced Cognee Project Memory", version="1.1.0", lifespan=lifespan)
    app.add_middleware(SecurityBoundary)
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
    async def ready():
        try:
            await store().check_schema()
            return {"ready": True, "retrieval": "semantic" if store().embedder else "text",
                    "encryption": "AES-256-GCM", "graph": "unavailable",
                    "sharing": "reviewed_projects_and_libraries"}
        except Exception:
            return JSONResponse({"ready": False}, status_code=503)

    @app.post("/v1/memories")
    async def remember(body: RememberRequest, request: Request):
        return await store().remember(scope(request), **body.model_dump())

    @app.post("/v1/memories/recall")
    async def recall(body: RecallRequest, request: Request):
        return await store().recall(scope(request), **body.model_dump())

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

    @app.patch("/v1/memories/{record_id}")
    async def correct(record_id: str, body: CorrectionRequest, request: Request):
        return await store().correct(scope(request), record_id, **body.model_dump())

    @app.post("/v1/memories/{record_id}/retract")
    async def retract(record_id: str, body: VersionRequest, request: Request):
        return await store().correct(scope(request), record_id, retract=True, **body.model_dump())

    @app.post("/v1/memories/{record_id}/share")
    async def share(record_id: str, body: ShareRequest, request: Request):
        return await store().share(scope(request), record_id, **body.model_dump())

    return app


app = create_app()
