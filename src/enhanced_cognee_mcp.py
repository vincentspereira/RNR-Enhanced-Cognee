#!/usr/bin/env python3
"""
Enhanced Cognee MCP Server
Integrates with enterprise-grade memory stack: PostgreSQL+pgVector, Qdrant, Neo4j, Redis
Provides DYNAMIC and CONFIGURABLE memory architecture (not hardcoded to specific categories)
"""

import os
import time
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
import qdrant_client
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from neo4j import GraphDatabase, Driver
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.db_factory import (
    get_cache_client,
    get_graph_driver,
    get_relational_pool,
    get_vector_client,
)
from src.secure_config import require_secret

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
class EnhancedConfig:
    def __init__(self):
        # Default to enabled. Set ENHANCED_COGNEE_MODE=false only when you
        # want to import the module without bringing up DB connections
        # (e.g. for unit tests that mock the storage layer entirely).
        self.enhanced_mode = os.getenv("ENHANCED_COGNEE_MODE", "true").lower() == "true"

        # Enhanced Stack Configuration with Enhanced ports
        self.postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "25432"))  # Enhanced port
        self.postgres_db = os.getenv("POSTGRES_DB", "cognee_db")
        self.postgres_user = os.getenv("POSTGRES_USER", "cognee_user")
        self.postgres_password = require_secret("POSTGRES_PASSWORD", dev_default="cognee_password")

        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "26333"))  # Enhanced port
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.qdrant_collection_prefix = os.getenv("QDRANT_COLLECTION_PREFIX", "cognee_")

        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:27687")  # Enhanced port
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = require_secret("NEO4J_PASSWORD", dev_default="cognee_password")
        self.neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "26379"))  # Enhanced port
        self.redis_password = os.getenv("REDIS_PASSWORD")
        self.redis_db = int(os.getenv("REDIS_DB", "0"))

        # Dynamic category configuration
        self.memory_categorization = os.getenv("MEMORY_CATEGORIZATION", "true").lower() == "true"
        self.config_path = os.getenv("ENHANCED_COGNEE_CONFIG_PATH")

        # Load dynamic category configuration
        self.category_prefixes = self._load_category_prefixes()

        # Performance Settings
        self.performance_monitoring = os.getenv("PERFORMANCE_MONITORING", "false").lower() == "true"
        self.auto_optimization = os.getenv("AUTO_OPTIMIZATION", "false").lower() == "true"
        self.vector_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))

    def _load_category_prefixes(self) -> Dict[str, str]:
        """Load dynamic category prefixes from configuration file"""
        # Try to load from JSON config
        config_paths = [
            self.config_path,
            ".enhanced-cognee-config.json",
            "config/.enhanced-cognee-config.json",
        ]

        for config_path in config_paths:
            if config_path and Path(config_path).exists():
                try:
                    with open(config_path, 'r') as f:
                        config_data = json.load(f)

                    prefixes = {}
                    if "categories" in config_data:
                        for cat_name, cat_config in config_data["categories"].items():
                            prefixes[cat_name] = cat_config.get("prefix", f"{cat_name.lower()}_")

                    logger.info(f"Loaded {len(prefixes)} category prefixes from {config_path}")
                    return prefixes
                except Exception as e:
                    logger.warning(f"Failed to load config from {config_path}: {e}")

        # Default to no prefixes (simple mode)
        logger.info("Using default category configuration (no custom prefixes)")
        return {}

config = EnhancedConfig()

# In-process HTTP request counter for the /metrics endpoint (dependency-free).
# Keyed by (method, status_class) e.g. ("POST", 200).
_HTTP_REQUEST_COUNTS: Dict[Tuple[str, int], int] = {}

# Data Models
class MemoryEntry(BaseModel):
    id: Optional[str] = None
    content: str
    agent_id: str
    memory_category: str  # Now dynamic - any category name allowed
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None

class SearchQuery(BaseModel):
    query: str
    embedding: Optional[List[float]] = None
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    memory_category: Optional[str] = None
    agent_id: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeRelation(BaseModel):
    source_entity: str
    target_entity: str
    relationship_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# /mcp/* endpoint models -- looser shapes that match the standard MCP tool
# surface (mcp_memory_tools.py + bin/enhanced_cognee_mcp_server.py). The
# locustfile + cross-language SDKs both target this surface, so the FastAPI
# server has to expose it alongside the existing /memory/* routes.

class McpAddMemoryRequest(BaseModel):
    content: str
    user_id: str = "default"
    agent_id: str = "claude-code"
    memory_category: str = "general"
    metadata: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)


class McpSearchMemoriesRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=100)
    user_id: str = "default"
    agent_id: Optional[str] = None


class McpGetMemoriesRequest(BaseModel):
    user_id: str = "default"
    agent_id: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=500)


class McpUpdateMemoryRequest(BaseModel):
    memory_id: str
    content: str


class McpDeleteMemoryRequest(BaseModel):
    memory_id: str

@asynccontextmanager
async def lifespan(app: "FastAPI"):
    """Application lifecycle: enforce prod auth, init tracing, connect stack.

    Startup never hard-crashes on a single dependency outage -- see
    ``EnhancedCogneeMCPServer.initialize`` for the retry + graceful-degrade
    behaviour. It DOES refuse to start in production without auth configured.
    """
    try:
        from src.mcp_security import enforce_production_auth, log_security_status
        enforce_production_auth()  # raises in production when no auth configured
        log_security_status()
        from src.security.enterprise_auth import log_enterprise_auth_status
        log_enterprise_auth_status()
    except RuntimeError:
        raise
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(f"Security status check skipped: {e}")

    # Best-effort OpenTelemetry tracing (no-op unless OTEL_* env configured).
    try:
        from src.tracing import init_tracing
        if init_tracing(service_name="enhanced-cognee-mcp"):
            logger.info("OpenTelemetry tracing initialized")
    except Exception as e:  # pragma: no cover
        logger.debug(f"Tracing not initialized: {e}")

    srv = getattr(app.state, "server", None) or server
    await srv.initialize()
    try:
        yield
    finally:
        await srv.shutdown()


class EnhancedCogneeMCPServer:
    """Enhanced Cognee MCP Server with enterprise-grade memory stack integration"""

    def __init__(self):
        self.postgres_pool = None
        self.qdrant_client = None
        self.neo4j_driver = None
        self.redis_client = None
        self.app = FastAPI(title="Enhanced Cognee MCP Server", lifespan=lifespan)
        self.app.state.server = self
        self._install_cors_middleware()
        self._install_security_middleware()
        self._install_tenant_middleware()
        self._install_metrics_middleware()
        # Registered last -> outermost middleware, so it observes the final
        # status code (including 401/403 from the auth layer).
        self._install_audit_middleware()
        self.setup_routes()

    def _install_cors_middleware(self) -> None:
        """Restrictive CORS driven by ENHANCED_CORS_ORIGINS (comma-separated).

        Default is NO cross-origin access. A literal '*' is downgraded to
        allow_credentials=False (wildcard origin + credentials is invalid and
        insecure).
        """
        raw = os.getenv("ENHANCED_CORS_ORIGINS", "")
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        if origins == ["*"]:
            logger.warning(
                "ENHANCED_CORS_ORIGINS='*'; forcing allow_credentials=False "
                "(wildcard origin with credentials is invalid)."
            )
            allow_credentials = False
        else:
            allow_credentials = bool(origins)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _install_security_middleware(self) -> None:
        """Authenticate + authorize every request, and cap payload size.

        Authentication resolves a Principal from the request (Bearer OIDC/JWT or
        ``X-API-Key``); authorization enforces the per-route permission defined
        in ``src.security.enterprise_auth``. The resolved Principal is stored on
        ``request.state.principal`` for downstream handlers and the audit log.

        Fail-open in dev (no auth configured -> implicit local admin), fail-closed
        in production. ``/health*`` (and ``/metrics`` unless
        ``ENHANCED_METRICS_PUBLIC=0``) stay public so probes / scrapers work
        without credentials. Per-tool rate limiting is applied at the route level
        (the middleware can't know which tool was invoked from the path alone).
        """
        from src.mcp_security import _payload_byte_cap
        from src.security.enterprise_auth import (
            AuthError,
            authenticate_request,
            authorize,
            route_required_permission,
        )

        @self.app.middleware("http")
        async def _security_scope(request, call_next):
            path = request.url.path
            public_paths = {"/health", "/health/live", "/health/ready"}
            # /metrics stays public by default for Prometheus scraping; set
            # ENHANCED_METRICS_PUBLIC=0 to require authentication on it too.
            if os.getenv("ENHANCED_METRICS_PUBLIC", "1").strip().lower() in (
                "1", "true", "yes", "on",
            ):
                public_paths.add("/metrics")

            if path not in public_paths:
                try:
                    principal = authenticate_request(request.headers)
                    request.state.principal = principal
                    authorize(
                        principal,
                        route_required_permission(request.method, path),
                    )
                except AuthError as e:
                    return JSONResponse(
                        status_code=e.status_code,
                        content={"detail": e.detail},
                    )

            cap = _payload_byte_cap()
            if cap is not None:
                content_length = request.headers.get("content-length")
                if content_length:
                    try:
                        size = int(content_length)
                    except ValueError:
                        size = 0
                    if size > cap:
                        return JSONResponse(
                            status_code=413,
                            content={
                                "detail": (
                                    f"Payload size {size} bytes exceeds "
                                    f"ENHANCED_MAX_PAYLOAD_BYTES cap of {cap} bytes."
                                )
                            },
                        )

            return await call_next(request)

    def _install_tenant_middleware(self) -> None:
        """Extract X-Tenant-ID header into the TenantContext for the request.

        FastAPI's middleware runs in the request's context, so any
        downstream call to a storage helper sees the tenant set here.
        Returns the response untouched.
        """
        from src.multi_tenant import TenantContext, tenant_required

        @self.app.middleware("http")
        async def _tenant_scope(request, call_next):
            path = request.url.path
            exempt = {"/health", "/health/live", "/health/ready", "/metrics"}
            tenant_id = request.headers.get("x-tenant-id") or request.headers.get(
                "X-Tenant-ID"
            )
            # Enforced by default in production (see multi_tenant.tenant_required);
            # explicit ENHANCED_REQUIRE_TENANT always wins.
            require_tenant = tenant_required()
            if not tenant_id and require_tenant and path not in exempt:
                return JSONResponse(
                    status_code=400,
                    content={
                        "detail": (
                            "X-Tenant-ID header is required "
                            "(ENHANCED_REQUIRE_TENANT=1)."
                        )
                    },
                )
            if tenant_id:
                async with TenantContext(tenant_id):
                    return await call_next(request)
            return await call_next(request)

    def _install_metrics_middleware(self) -> None:
        """Count HTTP requests by (method, status class) for the /metrics endpoint."""

        @self.app.middleware("http")
        async def _count_requests(request, call_next):
            response = await call_next(request)
            try:
                key = (request.method, (response.status_code // 100) * 100)
                _HTTP_REQUEST_COUNTS[key] = _HTTP_REQUEST_COUNTS.get(key, 0) + 1
            except Exception:
                pass
            return response

    def _install_audit_middleware(self) -> None:
        """Record an audit-log entry for mutations and authorization failures.

        Registered last so it is the OUTERMOST middleware and therefore observes
        the final status code -- including 401/403 produced by the auth layer.
        Reads the resolved Principal from ``request.state.principal`` (set by the
        security middleware) and the tenant from the ``X-Tenant-ID`` header.

        Best-effort: an audit-logging failure never affects the response, and
        the call is skipped silently when the audit logger is not initialized.
        Reads (GET) of non-sensitive routes are not logged to avoid log spam;
        the security-relevant trail is mutations + denied requests.
        """
        from src.audit_logger import AuditOperationType, get_audit_logger

        op_by_path = {
            "/memory/add": AuditOperationType.MEMORY_ADD,
            "/mcp/add_memory": AuditOperationType.MEMORY_ADD,
            "/mcp/update_memory": AuditOperationType.MEMORY_UPDATE,
            "/mcp/delete_memory": AuditOperationType.MEMORY_DELETE,
            "/knowledge/add_relation": AuditOperationType.MEMORY_ADD,
            "/memory/search": AuditOperationType.MEMORY_SEARCH,
            "/mcp/search_memories": AuditOperationType.MEMORY_SEARCH,
        }
        exempt = {"/health", "/health/live", "/health/ready", "/metrics"}

        @self.app.middleware("http")
        async def _audit_scope(request, call_next):
            start = time.monotonic()
            response = await call_next(request)
            try:
                path = request.url.path
                method = request.method
                is_mutation = method in ("POST", "PUT", "PATCH", "DELETE")
                is_auth_failure = response.status_code in (401, 403)
                if (is_mutation or is_auth_failure) and path not in exempt:
                    al = get_audit_logger()
                    if al is not None:
                        principal = getattr(request.state, "principal", None)
                        agent_id = getattr(principal, "subject", None) or "anonymous"
                        tenant = request.headers.get("x-tenant-id")
                        if is_auth_failure:
                            op = AuditOperationType.AUTH_DENIED
                        else:
                            op = op_by_path.get(path, AuditOperationType.API_REQUEST)
                        status = "success" if response.status_code < 400 else "failure"
                        await al.log(
                            operation_type=op,
                            agent_id=str(agent_id),
                            status=status,
                            details={
                                "method": method,
                                "path": path,
                                "status_code": response.status_code,
                                "auth_method": getattr(principal, "auth_method", "none"),
                                "role": getattr(
                                    getattr(principal, "role", None), "value", None
                                ),
                            },
                            execution_time_ms=(time.monotonic() - start) * 1000.0,
                            additional_context={"tenant": tenant} if tenant else None,
                        )
            except Exception:
                pass
            return response

    async def initialize(self):
        """Initialize all Enhanced stack connections with retry + graceful degrade.

        No single dependency failure crashes the server. Each connector is
        retried with backoff; on final failure the client is left as None and
        the server starts DEGRADED (the readiness probe reports 503 until the
        dependency recovers, and routes needing it return 503).
        """
        if not config.enhanced_mode:
            logger.warning("Enhanced Cognee mode is not enabled")
            return

        logger.info("Initializing Enhanced Cognee MCP Server...")

        await self._connect_with_retry(self._init_postgresql, "PostgreSQL")
        await self._connect_with_retry(self._init_qdrant, "Qdrant")
        await self._connect_with_retry(self._init_neo4j, "Neo4j/graph")
        await self._connect_with_retry(self._init_redis, "Redis/cache")

        # Audit logger (file + optional DB) so the audit middleware has a sink.
        # Best-effort: a failure here must not block server startup.
        try:
            from src.audit_logger import get_audit_logger, init_audit_logger
            if get_audit_logger() is None:
                init_audit_logger(db_pool=self.postgres_pool)
                logger.info("Audit logger initialized")
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"Audit logger init skipped: {e}")

        connected = [
            name for name, ok in (
                ("postgresql", self.postgres_pool is not None),
                ("qdrant", self.qdrant_client is not None),
                ("neo4j", self.neo4j_driver is not None),
                ("redis", self.redis_client is not None),
            ) if ok
        ]
        if self.postgres_pool is None:
            logger.error(
                "Enhanced Cognee started DEGRADED: PostgreSQL unavailable. "
                "Readiness will report 503 until it recovers."
            )
        else:
            logger.info(
                f"Enhanced Cognee MCP Server initialized "
                f"(connected: {', '.join(connected) or 'none'})"
            )

    async def _connect_with_retry(self, init_coro, name: str) -> None:
        """Call an _init_* coroutine with bounded retries; never raise.

        Retries ENHANCED_DB_CONNECT_ATTEMPTS times (default 3) with linear
        backoff (ENHANCED_DB_CONNECT_BACKOFF_SECONDS, default 2). On
        exhaustion logs an error and returns -- the _init_* method leaves its
        client as None so degraded state is detected accurately.
        """
        attempts = max(1, int(os.getenv("ENHANCED_DB_CONNECT_ATTEMPTS", "3")))
        backoff = float(os.getenv("ENHANCED_DB_CONNECT_BACKOFF_SECONDS", "2"))
        for attempt in range(1, attempts + 1):
            try:
                await init_coro()
                return
            except Exception as e:
                if attempt >= attempts:
                    logger.error(
                        f"{name}: connection failed after {attempt} attempt(s): "
                        f"{e}. Continuing in degraded mode."
                    )
                    return
                logger.warning(
                    f"{name}: connection attempt {attempt}/{attempts} failed: "
                    f"{e}. Retrying in {backoff * attempt:.1f}s."
                )
                await asyncio.sleep(backoff * attempt)

    async def shutdown(self) -> None:
        """Best-effort cleanup of all stack connections."""
        try:
            if self.postgres_pool is not None:
                await self.postgres_pool.close()
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(f"Postgres pool close failed: {e}")
        try:
            if self.redis_client is not None:
                close = getattr(self.redis_client, "aclose", None) or getattr(
                    self.redis_client, "close", None
                )
                if close is not None:
                    res = close()
                    if asyncio.iscoroutine(res):
                        await res
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(f"Redis close failed: {e}")
        try:
            if self.neo4j_driver is not None:
                self.neo4j_driver.close()
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(f"Neo4j driver close failed: {e}")

    async def _init_postgresql(self):
        """Initialize PostgreSQL connection (replaces SQLite)"""
        try:
            self.postgres_pool = await get_relational_pool(
                host=config.postgres_host,
                port=config.postgres_port,
                database=config.postgres_db,
                user=config.postgres_user,
                password=config.postgres_password,
                min_size=5,
                max_size=20,
            )
            logger.info("PostgreSQL connection established")
        except Exception as e:
            self.postgres_pool = None
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def _init_qdrant(self):
        """Initialize Qdrant client (replaces LanceDB)"""
        try:
            self.qdrant_client = get_vector_client(
                host=config.qdrant_host,
                port=config.qdrant_port,
                api_key=config.qdrant_api_key,
            )

            # Test connection
            collections = self.qdrant_client.get_collections()
            logger.info(f"Qdrant connection established. Collections: {len(collections.collections)}")
        except Exception as e:
            self.qdrant_client = None
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    async def _init_neo4j(self):
        """Initialize Neo4j driver (replaces Kuzu)"""
        try:
            self.neo4j_driver = get_graph_driver(
                uri=config.neo4j_uri,
                user=config.neo4j_user,
                password=config.neo4j_password,
            )

            # Test connection
            with self.neo4j_driver.session(database=config.neo4j_database) as session:
                result = session.run("RETURN 1")
                result.single()

            logger.info("Neo4j connection established")
        except Exception as e:
            self.neo4j_driver = None
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def _init_redis(self):
        """Initialize Redis client (new cache layer)"""
        try:
            self.redis_client = get_cache_client(
                host=config.redis_host,
                port=config.redis_port,
                password=config.redis_password,
                db=config.redis_db,
                decode_responses=True,
            )

            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            self.redis_client = None
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _get_collection_name(self, memory_category: str, agent_id: str) -> str:
        """
        Generate Qdrant collection name with DYNAMIC categorization

        Supports dynamic category prefixes from configuration file
        Falls back to simple {prefix}{category}_memory format
        """
        if config.memory_categorization and config.category_prefixes:
            # Use dynamic category prefix from configuration
            prefix = config.category_prefixes.get(memory_category, f"{memory_category.lower()}_")
            return f"{config.qdrant_collection_prefix}{prefix}memory"
        else:
            # Simple format without category prefixes
            return f"{config.qdrant_collection_prefix}{memory_category.lower()}_memory"

    async def add_memory(self, entry: MemoryEntry) -> str:
        """Add memory entry to Enhanced stack"""
        try:
            # Generate ID if not provided
            entry.id = entry.id or str(uuid.uuid4())
            entry.created_at = datetime.now(timezone.utc)

            # Store in PostgreSQL (metadata) -- tenant-scoped when active.
            from src.multi_tenant import (
                ensure_tenant_schema,
                get_tenant,
                tenant_scoped_collection,
                tenant_scoped_table,
            )

            if get_tenant() is not None:
                await ensure_tenant_schema(self.postgres_pool)

            documents_table = tenant_scoped_table("shared_memory.documents")
            # asyncpg's default JSONB codec expects str -- serialise here so
            # callers can keep passing dicts.
            metadata_json = json.dumps(entry.metadata or {})
            async with self.postgres_pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {documents_table}
                    (id, title, content, agent_id, memory_category, tags, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
                """, entry.id, f"Memory from {entry.agent_id}", entry.content,
                    entry.agent_id, entry.memory_category, entry.tags, metadata_json, entry.created_at)

            # Store embedding in Qdrant (vector search) -- tenant-scoped collection
            if entry.embedding:
                collection_name = self._get_collection_name(entry.memory_category, entry.agent_id)
                collection_name = tenant_scoped_collection(collection_name)

                # Create collection if it doesn't exist
                try:
                    self.qdrant_client.get_collection(collection_name)
                except:
                    self.qdrant_client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(size=config.vector_dimensions, distance=Distance.COSINE)
                    )

                # Add vector point
                point = PointStruct(
                    id=entry.id,
                    vector=entry.embedding,
                    payload={
                        "content": entry.content,
                        "agent_id": entry.agent_id,
                        "memory_category": entry.memory_category,
                        "tags": entry.tags,
                        "created_at": entry.created_at.isoformat()
                    }
                )

                self.qdrant_client.upsert(
                    collection_name=collection_name,
                    points=[point]
                )

            # Cache in Redis
            await self.redis_client.setex(
                f"memory:{entry.id}",
                timedelta(hours=1),
                json.dumps({
                    "content": entry.content,
                    "agent_id": entry.agent_id,
                    "memory_category": entry.memory_category
                })
            )

            logger.info(f"Added memory entry {entry.id} for agent {entry.agent_id}")
            return entry.id

        except Exception as e:
            logger.error(f"Failed to add memory entry: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def search_memory(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """
        Search memory using Enhanced vector database with DYNAMIC categories.

        Supports searching across dynamically configured categories.

        When ``query.embedding`` is provided, runs vector search against Qdrant.
        When it's absent, falls back to Postgres full-text search over
        ``shared_memory.documents.content`` (tenant-scoped) so HTTP callers
        without local embedding capability still get useful results.
        """
        try:
            results = []

            if not query.embedding:
                # Postgres text-search fallback. Use plainto_tsquery for safety
                # (handles raw user input without parser errors). Returns
                # results ordered by ts_rank descending. Tenant-scoped via the
                # multi_tenant naming helper.
                from src.multi_tenant import tenant_scoped_table
                documents_table = tenant_scoped_table("shared_memory.documents")
                try:
                    async with self.postgres_pool.acquire() as conn:
                        if query.agent_id:
                            rows = await conn.fetch(
                                f"""
                                SELECT id, content, agent_id, memory_category,
                                       created_at,
                                       ts_rank(
                                           to_tsvector('english',
                                                       coalesce(content, '')),
                                           plainto_tsquery('english', $1)
                                       ) AS rank
                                FROM {documents_table}
                                WHERE to_tsvector('english',
                                                  coalesce(content, ''))
                                      @@ plainto_tsquery('english', $1)
                                  AND agent_id = $2
                                ORDER BY rank DESC, created_at DESC
                                LIMIT $3
                                """,
                                query.query, query.agent_id, query.limit,
                            )
                        else:
                            rows = await conn.fetch(
                                f"""
                                SELECT id, content, agent_id, memory_category,
                                       created_at,
                                       ts_rank(
                                           to_tsvector('english',
                                                       coalesce(content, '')),
                                           plainto_tsquery('english', $1)
                                       ) AS rank
                                FROM {documents_table}
                                WHERE to_tsvector('english',
                                                  coalesce(content, ''))
                                      @@ plainto_tsquery('english', $1)
                                ORDER BY rank DESC, created_at DESC
                                LIMIT $2
                                """,
                                query.query, query.limit,
                            )
                    for r in rows:
                        results.append({
                            "id": str(r["id"]),
                            "content": r["content"],
                            "agent_id": r["agent_id"],
                            "memory_category": r["memory_category"],
                            "similarity_score": float(r["rank"]),
                            "created_at": (
                                r["created_at"].isoformat()
                                if r["created_at"] else None
                            ),
                            "source": "postgres_fts",
                        })
                    return results
                except Exception as e:
                    logger.warning(
                        f"Postgres FTS fallback failed: {e}; "
                        f"returning empty result set."
                    )
                    return results

            if query.embedding:
                # Search across relevant Qdrant collections
                collection_names = []

                if query.memory_category and query.agent_id:
                    collection_names.append(self._get_collection_name(query.memory_category, query.agent_id))
                else:
                    # Search across all configured category collections
                    if config.memory_categorization and config.category_prefixes:
                        # Use dynamic categories from configuration
                        for category_name in config.category_prefixes.keys():
                            if not query.memory_category or query.memory_category.lower() == category_name.lower():
                                collection_name = self._get_collection_name(category_name, "")
                                # Check if collection exists before searching
                                try:
                                    self.qdrant_client.get_collection(collection_name)
                                    collection_names.append(collection_name)
                                except:
                                    logger.debug(f"Collection {collection_name} does not exist, skipping")
                    else:
                        # No categorization - search default collection
                        collection_names.append(f"{config.qdrant_collection_prefix}memory")

                # Search each collection
                for collection_name in collection_names:
                    try:
                        search_result = self.qdrant_client.search(
                            collection_name=collection_name,
                            query_vector=query.embedding,
                            query_filter=self._build_qdrant_filter(query),
                            limit=query.limit,
                            score_threshold=query.similarity_threshold
                        )

                        for hit in search_result:
                            results.append({
                                "id": hit.id,
                                "content": hit.payload["content"],
                                "agent_id": hit.payload["agent_id"],
                                "memory_category": hit.payload["memory_category"],
                                "similarity_score": hit.score,
                                "created_at": hit.payload["created_at"]
                            })
                    except Exception as e:
                        logger.warning(f"Failed to search collection {collection_name}: {e}")
                        continue

                # Sort by similarity and limit results
                results.sort(key=lambda x: x["similarity_score"], reverse=True)
                results = results[:query.limit]

            return results

        except Exception as e:
            logger.error(f"Failed to search memory: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def _build_qdrant_filter(self, query: SearchQuery) -> Optional[Filter]:
        """Build Qdrant filter from search query"""
        conditions = []

        if query.agent_id:
            conditions.append(FieldCondition(key="agent_id", match=MatchValue(value=query.agent_id)))

        if query.memory_category:
            conditions.append(FieldCondition(key="memory_category", match=MatchValue(value=query.memory_category)))

        # Add custom filters
        for key, value in query.filters.items():
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

        return Filter(must=conditions) if conditions else None

    async def _get_active_agents(self, memory_category: Optional[str] = None) -> List[str]:
        """Get list of active agents from PostgreSQL (tenant-scoped when active)."""
        from src.multi_tenant import tenant_scoped_table

        documents_table = tenant_scoped_table("shared_memory.documents")
        try:
            async with self.postgres_pool.acquire() as conn:
                if memory_category:
                    query = (
                        "SELECT DISTINCT agent_id "
                        f"FROM {documents_table} "
                        "WHERE memory_category = $1"
                    )
                    result = await conn.fetch(query, memory_category)
                else:
                    query = f"SELECT DISTINCT agent_id FROM {documents_table}"
                    result = await conn.fetch(query)

                return [row["agent_id"] for row in result]
        except Exception as e:
            logger.warning(f"Failed to get active agents: {e}")
            return []

    async def add_knowledge_relation(self, relation: KnowledgeRelation) -> str:
        """Add knowledge graph relation using Neo4j"""
        try:
            with self.neo4j_driver.session(database=config.neo4j_database) as session:
                # Create nodes if they don't exist
                session.run("""
                    MERGE (source:Entity {name: $source_name})
                    MERGE (target:Entity {name: $target_name})
                """, source_name=relation.source_entity, target_name=relation.target_entity)

                # Create relationship
                result = session.run("""
                    MATCH (source:Entity {name: $source_name})
                    MATCH (target:Entity {name: $target_name})
                    CREATE (source)-[r:RELATES_TO {
                        type: $rel_type,
                        properties: $properties,
                        confidence: $confidence,
                        created_at: $created_at
                    }]->(target)
                    RETURN r
                """,
                source_name=relation.source_entity,
                target_name=relation.target_entity,
                rel_type=relation.relationship_type,
                properties=relation.properties,
                confidence=relation.confidence,
                created_at=datetime.now(timezone.utc).isoformat()
                )

                relation_id = str(uuid.uuid4())
                logger.info(f"Added knowledge relation {relation_id}")
                return relation_id

        except Exception as e:
            logger.error(f"Failed to add knowledge relation: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics from Enhanced stack (tenant-scoped when active)."""
        from src.multi_tenant import tenant_scoped_table

        documents_table = tenant_scoped_table("shared_memory.documents")
        try:
            stats = {}

            # PostgreSQL stats
            async with self.postgres_pool.acquire() as conn:
                result = await conn.fetch(f"""
                    SELECT
                        memory_category,
                        agent_id,
                        COUNT(*) as document_count,
                        MAX(created_at) as last_activity
                    FROM {documents_table}
                    GROUP BY memory_category, agent_id
                """)

                stats["documents"] = [dict(row) for row in result]
                stats["total_documents"] = sum(row["document_count"] for row in result)

            # Qdrant stats
            collections = self.qdrant_client.get_collections()
            stats["vector_collections"] = len(collections.collections)
            stats["total_vector_points"] = sum(
                self.qdrant_client.count(collection.name).count
                for collection in collections.collections
            )

            # Neo4j stats
            with self.neo4j_driver.session(database=config.neo4j_database) as session:
                result = session.run("MATCH (n:Entity) RETURN COUNT(n) as entity_count")
                stats["total_entities"] = result.single()["entity_count"]

                result = session.run("MATCH ()-[r]->() RETURN COUNT(r) as relation_count")
                stats["total_relations"] = result.single()["relation_count"]

            # Redis stats
            info = await self.redis_client.info()
            stats["cache_memory_used"] = info.get("used_memory_human", "N/A")
            stats["cache_keys"] = info.get("db0", {}).get("keys", 0)

            return stats

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _dependency_health(self) -> Dict[str, Any]:
        """Probe each dependency; return per-dep status + overall readiness.

        PostgreSQL is the only HARD dependency for readiness; the vector /
        graph / cache tiers degrade gracefully. A single (fast) reconnect is
        attempted for PostgreSQL when it is currently disconnected, so the
        server self-heals once the database recovers -- without a restart.
        """
        deps: Dict[str, str] = {}

        # PostgreSQL (critical) -- one-shot reconnect attempt if down.
        if self.postgres_pool is None:
            try:
                await self._init_postgresql()
            except Exception:
                self.postgres_pool = None
        try:
            if self.postgres_pool is not None:
                async with self.postgres_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                deps["postgresql"] = "connected"
            else:
                deps["postgresql"] = "disconnected"
        except Exception as e:
            deps["postgresql"] = f"error: {e}"

        # Qdrant (degrade gracefully)
        try:
            if self.qdrant_client is not None:
                cols = self.qdrant_client.get_collections()
                deps["qdrant"] = f"connected ({len(cols.collections)} collections)"
            else:
                deps["qdrant"] = "disconnected"
        except Exception as e:
            deps["qdrant"] = f"error: {e}"

        # Neo4j / graph (degrade gracefully)
        try:
            if self.neo4j_driver is not None:
                with self.neo4j_driver.session() as session:
                    session.run("RETURN 1").consume()
                deps["neo4j"] = "connected"
            else:
                deps["neo4j"] = "disconnected"
        except Exception as e:
            deps["neo4j"] = f"error: {e}"

        # Redis / cache (degrade gracefully)
        try:
            if self.redis_client is not None:
                await self.redis_client.ping()
                deps["redis"] = "connected"
            else:
                deps["redis"] = "disconnected"
        except Exception as e:
            deps["redis"] = f"error: {e}"

        critical_ok = deps.get("postgresql") == "connected"
        degraded = any(
            not str(v).startswith("connected") for v in deps.values()
        )
        if not critical_ok:
            overall = "unhealthy"
        elif degraded:
            overall = "degraded"
        else:
            overall = "healthy"
        return {"overall": overall, "ready": critical_ok, "dependencies": deps}

    async def _render_prometheus_metrics(self) -> str:
        """Render Prometheus text-format metrics (no external dependency)."""
        lines = [
            "# HELP enhanced_cognee_up Server process up indicator",
            "# TYPE enhanced_cognee_up gauge",
            "enhanced_cognee_up 1",
        ]
        h = await self._dependency_health()
        lines.append(
            "# HELP enhanced_cognee_dependency_up Dependency state (1=up,0=down)"
        )
        lines.append("# TYPE enhanced_cognee_dependency_up gauge")
        for dep, status in h["dependencies"].items():
            up = 1 if str(status).startswith("connected") else 0
            lines.append(
                f'enhanced_cognee_dependency_up{{dependency="{dep}"}} {up}'
            )
        lines.append("# HELP enhanced_cognee_ready Readiness (1=ready,0=not)")
        lines.append("# TYPE enhanced_cognee_ready gauge")
        lines.append(f"enhanced_cognee_ready {1 if h['ready'] else 0}")
        lines.append(
            "# HELP enhanced_cognee_http_requests_total HTTP requests by "
            "method and status class"
        )
        lines.append("# TYPE enhanced_cognee_http_requests_total counter")
        for (method, status_class), count in sorted(_HTTP_REQUEST_COUNTS.items()):
            lines.append(
                f'enhanced_cognee_http_requests_total'
                f'{{method="{method}",status="{status_class}"}} {count}'
            )
        try:
            if self.postgres_pool is not None:
                from src.multi_tenant import tenant_scoped_table
                table = tenant_scoped_table("shared_memory.documents")
                async with self.postgres_pool.acquire() as conn:
                    total = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                lines.append(
                    "# HELP enhanced_cognee_total_memories Total stored memories"
                )
                lines.append("# TYPE enhanced_cognee_total_memories gauge")
                lines.append(f"enhanced_cognee_total_memories {int(total)}")
        except Exception:
            pass
        return "\n".join(lines) + "\n"

    def setup_routes(self):
        """Setup FastAPI routes for MCP interface"""

        @self.app.post("/memory/add")
        async def add_memory_endpoint(entry: MemoryEntry):
            """MCP Tool: Add memory entry"""
            return {"id": await self.add_memory(entry)}

        @self.app.post("/memory/search")
        async def search_memory_endpoint(query: SearchQuery):
            """MCP Tool: Search memory"""
            results = await self.search_memory(query)
            return {"results": results, "count": len(results)}

        @self.app.post("/knowledge/add_relation")
        async def add_relation_endpoint(relation: KnowledgeRelation):
            """MCP Tool: Add knowledge graph relation"""
            return {"id": await self.add_knowledge_relation(relation)}

        # -------------------------------------------------------------------
        # /mcp/* endpoints -- standard MCP tool surface mirrored over HTTP.
        # Same semantics as bin/enhanced_cognee_mcp_server.py stdio tools;
        # locustfile + cross-language SDKs target these routes.
        # Rate limiting is per-(tool, agent_id) via src.mcp_security; gated
        # behind ENHANCED_RATE_LIMIT_<TOOL>_PER_MIN so dev stays frictionless.
        # -------------------------------------------------------------------

        def _enforce_rate_limit(tool: str, agent_id: Optional[str]) -> None:
            from src.mcp_security import RateLimitExceeded, check_rate_limit
            try:
                check_rate_limit(tool, agent_id or "_default_")
            except RateLimitExceeded as e:
                raise HTTPException(status_code=429, detail=str(e))

        @self.app.post("/mcp/add_memory")
        async def mcp_add_memory(req: McpAddMemoryRequest):
            _enforce_rate_limit("add_memory", req.agent_id)
            entry = MemoryEntry(
                content=req.content,
                agent_id=req.agent_id,
                memory_category=req.memory_category,
                metadata=req.metadata or {},
                tags=req.tags,
            )
            return {"id": await self.add_memory(entry)}

        @self.app.post("/mcp/search_memories")
        async def mcp_search_memories(req: McpSearchMemoriesRequest):
            _enforce_rate_limit("search_memories", req.agent_id)
            query = SearchQuery(
                query=req.query,
                limit=req.limit,
                agent_id=req.agent_id,
            )
            results = await self.search_memory(query)
            return {"results": results, "count": len(results)}

        @self.app.post("/mcp/get_memories")
        async def mcp_get_memories(req: McpGetMemoriesRequest):
            _enforce_rate_limit("get_memories", req.agent_id)
            from src.multi_tenant import tenant_scoped_table
            documents_table = tenant_scoped_table("shared_memory.documents")
            try:
                async with self.postgres_pool.acquire() as conn:
                    if req.agent_id:
                        rows = await conn.fetch(
                            f"SELECT id, content, agent_id, memory_category, "
                            f"created_at, metadata FROM {documents_table} "
                            f"WHERE agent_id = $1 ORDER BY created_at DESC LIMIT $2",
                            req.agent_id, req.limit,
                        )
                    else:
                        rows = await conn.fetch(
                            f"SELECT id, content, agent_id, memory_category, "
                            f"created_at, metadata FROM {documents_table} "
                            f"ORDER BY created_at DESC LIMIT $1",
                            req.limit,
                        )
                items = [
                    {
                        "memory_id": str(r["id"]),
                        "content": r["content"],
                        "agent_id": r["agent_id"],
                        "memory_category": r["memory_category"],
                        "created_at": (
                            r["created_at"].isoformat()
                            if r["created_at"] else None
                        ),
                        "metadata": r["metadata"],
                    }
                    for r in rows
                ]
                return {"memories": items, "count": len(items)}
            except Exception as e:
                logger.error(f"mcp_get_memories failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/mcp/update_memory")
        async def mcp_update_memory(req: McpUpdateMemoryRequest):
            _enforce_rate_limit("update_memory", None)
            from src.multi_tenant import tenant_scoped_table
            documents_table = tenant_scoped_table("shared_memory.documents")
            try:
                async with self.postgres_pool.acquire() as conn:
                    result = await conn.execute(
                        f"UPDATE {documents_table} SET content = $1 "
                        f"WHERE id = $2",
                        req.content, req.memory_id,
                    )
                # asyncpg returns "UPDATE 0" / "UPDATE 1"; parse the count
                affected = 0
                if isinstance(result, str) and result.startswith("UPDATE "):
                    try:
                        affected = int(result.split()[1])
                    except (ValueError, IndexError):
                        affected = 0
                # Best-effort cache invalidation; ignore failures
                if self.redis_client:
                    try:
                        await self.redis_client.delete(f"memory:{req.memory_id}")
                    except Exception:
                        pass
                return {"updated": affected, "memory_id": req.memory_id}
            except Exception as e:
                logger.error(f"mcp_update_memory failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/mcp/delete_memory")
        async def mcp_delete_memory(req: McpDeleteMemoryRequest):
            _enforce_rate_limit("delete_memory", None)
            from src.multi_tenant import tenant_scoped_table
            documents_table = tenant_scoped_table("shared_memory.documents")
            try:
                async with self.postgres_pool.acquire() as conn:
                    result = await conn.execute(
                        f"DELETE FROM {documents_table} WHERE id = $1",
                        req.memory_id,
                    )
                affected = 0
                if isinstance(result, str) and result.startswith("DELETE "):
                    try:
                        affected = int(result.split()[1])
                    except (ValueError, IndexError):
                        affected = 0
                if self.redis_client:
                    try:
                        await self.redis_client.delete(f"memory:{req.memory_id}")
                    except Exception:
                        pass
                return {"deleted": affected, "memory_id": req.memory_id}
            except Exception as e:
                logger.error(f"mcp_delete_memory failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/mcp/list_agents")
        async def mcp_list_agents():
            _enforce_rate_limit("list_agents", None)
            from src.multi_tenant import tenant_scoped_table
            documents_table = tenant_scoped_table("shared_memory.documents")
            try:
                async with self.postgres_pool.acquire() as conn:
                    rows = await conn.fetch(
                        f"SELECT agent_id, COUNT(*) AS memory_count "
                        f"FROM {documents_table} GROUP BY agent_id "
                        f"ORDER BY memory_count DESC"
                    )
                agents = [
                    {"agent_id": r["agent_id"], "memory_count": r["memory_count"]}
                    for r in rows
                ]
                return {"agents": agents, "count": len(agents)}
            except Exception as e:
                logger.error(f"mcp_list_agents failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/stats")
        async def get_stats_endpoint():
            """MCP Tool: Get memory statistics"""
            return await self.get_memory_stats()

        @self.app.get("/health/live")
        async def health_live():
            """Liveness probe: the process is up. Always 200 while serving."""
            return {
                "status": "alive",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        @self.app.get("/health/ready")
        async def health_ready():
            """Readiness probe: 200 when critical deps are up, else 503."""
            h = await self._dependency_health()
            body = {
                "status": h["overall"],
                "ready": h["ready"],
                "enhanced_mode": config.enhanced_mode,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dependencies": h["dependencies"],
            }
            return JSONResponse(
                status_code=200 if h["ready"] else 503, content=body
            )

        @self.app.get("/metrics")
        async def metrics_endpoint():
            """Prometheus text-format metrics (dependency-free exposition)."""
            text = await self._render_prometheus_metrics()
            return PlainTextResponse(
                content=text, media_type="text/plain; version=0.0.4"
            )

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint with Enhanced stack status"""
            health = {
                "status": "healthy",
                "enhanced_mode": config.enhanced_mode,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stack": {
                    "postgresql": f"{config.postgres_host}:{config.postgres_port}",
                    "qdrant": f"{config.qdrant_host}:{config.qdrant_port}",
                    "neo4j": config.neo4j_uri,
                    "redis": f"{config.redis_host}:{config.redis_port}",
                },
                "categories": {
                    "enabled": config.memory_categorization,
                    "count": len(config.category_prefixes),
                    "configured": list(config.category_prefixes.keys()) if config.category_prefixes else []
                }
            }

            # Check each component
            try:
                if self.postgres_pool:
                    async with self.postgres_pool.acquire() as conn:
                        await conn.fetchval("SELECT 1")
                    health["postgresql"] = "connected"
                else:
                    health["postgresql"] = "disconnected"
            except Exception as e:
                health["postgresql"] = f"error: {str(e)}"

            try:
                if self.qdrant_client:
                    collections = self.qdrant_client.get_collections()
                    health["qdrant"] = f"connected ({len(collections.collections)} collections)"
                else:
                    health["qdrant"] = "disconnected"
            except Exception as e:
                health["qdrant"] = f"error: {str(e)}"

            try:
                if self.neo4j_driver:
                    with self.neo4j_driver.session() as session:
                        session.run("RETURN 1")
                    health["neo4j"] = "connected"
                else:
                    health["neo4j"] = "disconnected"
            except Exception as e:
                health["neo4j"] = f"error: {str(e)}"

            try:
                if self.redis_client:
                    await self.redis_client.ping()
                    health["redis"] = "connected"
                else:
                    health["redis"] = "disconnected"
            except Exception as e:
                health["redis"] = f"error: {str(e)}"

            return health

# Global server instance. The lifespan (defined above the class) drives
# startup/shutdown; `app` IS the server's own app so the security, tenant,
# CORS and metrics middleware actually apply to served requests (the previous
# include_router wrapper silently dropped all middleware).
server = EnhancedCogneeMCPServer()
app = server.app

if __name__ == "__main__":
    import uvicorn

    # HTTPS / TLS support. Set ENHANCED_HTTPS_CERT_FILE + ENHANCED_HTTPS_KEY_FILE
    # to PEM file paths and the server listens on HTTPS instead of HTTP.
    # ENHANCED_HTTPS_CA_CERTS (optional) for client-cert verification.
    # When neither cert nor key is set, falls back to plain HTTP -- the
    # historical default, suitable for local Claude Code MCP usage behind
    # localhost or a reverse proxy that terminates TLS.
    host = os.getenv("ENHANCED_HTTPS_HOST", "0.0.0.0")
    port = int(os.getenv("ENHANCED_HTTPS_PORT", "8080"))
    cert_file = os.getenv("ENHANCED_HTTPS_CERT_FILE")
    key_file = os.getenv("ENHANCED_HTTPS_KEY_FILE")
    ca_certs = os.getenv("ENHANCED_HTTPS_CA_CERTS")

    kwargs = {"host": host, "port": port}
    if cert_file and key_file:
        kwargs["ssl_certfile"] = cert_file
        kwargs["ssl_keyfile"] = key_file
        if ca_certs:
            kwargs["ssl_ca_certs"] = ca_certs
        logger.info(
            f"Enhanced Cognee MCP starting on HTTPS https://{host}:{port} "
            f"(cert={cert_file}, key={key_file}, ca={ca_certs or 'none'})"
        )
    else:
        logger.info(
            f"Enhanced Cognee MCP starting on HTTP http://{host}:{port} "
            f"(set ENHANCED_HTTPS_CERT_FILE + ENHANCED_HTTPS_KEY_FILE to "
            f"enable TLS termination at the application layer)"
        )

    uvicorn.run(app, **kwargs)