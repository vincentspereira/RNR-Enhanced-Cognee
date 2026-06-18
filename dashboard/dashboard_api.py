"""
Enhanced Cognee - Dashboard REST API

FastAPI-based REST API for the web dashboard (dashboard/nextjs-dashboard).
Provides real, database-backed endpoints for memory management, search,
sessions, graph visualization, activity metrics, and real-time updates.

Storage layout (shared with src/enhanced_cognee_mcp.py):
  - PostgreSQL  shared_memory.documents       memories
                shared_memory.sessions        sessions
                shared_memory.entities        graph fallback nodes
                shared_memory.relationships   graph fallback edges
  - Neo4j/ArcadeDB (bolt)                     knowledge graph (preferred)
  - Redis/Valkey                              optional cache (not required)

The API degrades gracefully: if a backend is down, endpoints return empty
data plus accurate database_status flags instead of crashing, so the
dashboard stays usable.

All output is ASCII-only (Windows cp1252 compatible).

Author: Enhanced Cognee Team
Version: 2.0.0
"""

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional outside Docker
    pass

# ---------------------------------------------------------------------------
# Configuration (mirrors EnhancedConfig defaults in src/enhanced_cognee_mcp.py)
# ---------------------------------------------------------------------------

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "25432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "cognee_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "cognee_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "cognee_password")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:27687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "cognee_password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "26379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "26333"))

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:9050,http://127.0.0.1:9050",
    ).split(",")
    if o.strip()
]

DOCUMENTS = "shared_memory.documents"
SESSIONS = "shared_memory.sessions"
ENTITIES = "shared_memory.entities"
RELATIONSHIPS = "shared_memory.relationships"

SERVER_STARTED_AT = datetime.now(timezone.utc)

# ---------------------------------------------------------------------------
# ArcadeDB HTTP transport (fallback when the Bolt plugin is not enabled)
# ---------------------------------------------------------------------------

ARCADEDB_HOST = os.getenv("ARCADEDB_HOST", "localhost")
ARCADEDB_USER = os.getenv("ARCADEDB_USER", "root")
ARCADEDB_PASSWORD = os.getenv("ARCADEDB_PASSWORD", "cognee_password")
ARCADEDB_DATABASE = os.getenv("ARCADEDB_DATABASE", "cognee_graph")
# Enhanced host-mapped port first, then the in-container default.
ARCADEDB_HTTP_PORTS = [
    int(p)
    for p in (
        [os.getenv("ARCADEDB_HTTP_PORT")] if os.getenv("ARCADEDB_HTTP_PORT") else []
    )
    + ["22480", "2480"]
]


def _arcadedb_request(cfg: Dict[str, Any], path: str, body: Optional[Dict] = None):
    """Issue a request against the ArcadeDB HTTP API (sync, stdlib only)."""
    import base64
    from urllib.request import Request, urlopen

    url = f"http://{cfg['host']}:{cfg['port']}{path}"
    token = base64.b64encode(
        f"{cfg['user']}:{cfg['password']}".encode("utf-8")
    ).decode("ascii")
    req = Request(
        url,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST" if body is not None else "GET",
    )
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _probe_arcadedb_http() -> Optional[Dict[str, Any]]:
    """Find a reachable ArcadeDB HTTP endpoint, or None."""
    for port in ARCADEDB_HTTP_PORTS:
        cfg = {
            "host": ARCADEDB_HOST,
            "port": port,
            "user": ARCADEDB_USER,
            "password": ARCADEDB_PASSWORD,
            "database": ARCADEDB_DATABASE,
        }
        try:
            payload = _arcadedb_request(cfg, "/api/v1/databases")
            databases = payload.get("result", [])
            if ARCADEDB_DATABASE in databases:
                return cfg
            if databases:
                cfg["database"] = databases[0]
                return cfg
        except Exception:
            continue
    return None


def _http_cypher(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
    """Run a Cypher query via the ArcadeDB HTTP API; returns dict rows."""
    cfg = conns.graph_http
    body: Dict[str, Any] = {"language": "cypher", "command": query}
    if params:
        body["params"] = params
    payload = _arcadedb_request(cfg, f"/api/v1/command/{cfg['database']}", body)
    rows = payload.get("result", [])
    return [r if isinstance(r, dict) else {"value": r} for r in rows]


# ---------------------------------------------------------------------------
# Connection state
# ---------------------------------------------------------------------------


class Connections:
    """Lazily-initialized connections shared by all endpoints."""

    def __init__(self) -> None:
        self.pg_pool = None
        self.neo4j_driver = None
        self.redis_client = None
        # ArcadeDB HTTP transport config (fallback when Bolt is unavailable)
        self.graph_http: Optional[Dict[str, Any]] = None

    async def init(self) -> None:
        await self._init_postgres()
        self._init_neo4j()
        await self._init_redis()

    async def _init_postgres(self) -> None:
        try:
            import asyncpg

            self.pg_pool = await asyncpg.create_pool(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                min_size=1,
                max_size=10,
                command_timeout=30,
            )
            logger.info("OK PostgreSQL pool ready (%s:%s)", POSTGRES_HOST, POSTGRES_PORT)
        except Exception as exc:
            self.pg_pool = None
            logger.error("ERR PostgreSQL unavailable: %s", exc)

    def _init_neo4j(self) -> None:
        # ArcadeDB's Bolt plugin only supports direct connections, so the
        # routing scheme neo4j:// must be normalized to bolt://.
        bolt_uri = NEO4J_URI.replace("neo4j://", "bolt://").replace(
            "neo4j+s://", "bolt+s://"
        )
        try:
            from neo4j import GraphDatabase

            self.neo4j_driver = GraphDatabase.driver(
                bolt_uri, auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            with self.neo4j_driver.session(database=NEO4J_DATABASE) as session:
                session.run("RETURN 1").single()
            logger.info("OK Graph database ready via Bolt (%s)", bolt_uri)
            return
        except Exception as exc:
            if self.neo4j_driver is not None:
                try:
                    self.neo4j_driver.close()
                except Exception:
                    pass
            self.neo4j_driver = None
            logger.warning("WARN Bolt graph transport unavailable: %s", exc)

        # Fallback: ArcadeDB HTTP/JSON command API (no Bolt plugin needed).
        self.graph_http = _probe_arcadedb_http()
        if self.graph_http is not None:
            logger.info(
                "OK Graph database ready via ArcadeDB HTTP (%s:%s/%s)",
                self.graph_http["host"],
                self.graph_http["port"],
                self.graph_http["database"],
            )
        else:
            logger.warning("WARN Graph database unavailable (Bolt and HTTP)")

    async def _init_redis(self) -> None:
        try:
            import redis.asyncio as aioredis

            self.redis_client = aioredis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=3,
            )
            await self.redis_client.ping()
            logger.info("OK Redis ready (%s:%s)", REDIS_HOST, REDIS_PORT)
        except Exception as exc:
            self.redis_client = None
            logger.warning("WARN Redis unavailable: %s", exc)

    async def close(self) -> None:
        if self.pg_pool is not None:
            try:
                await self.pg_pool.close()
            except Exception:
                pass
        if self.neo4j_driver is not None:
            try:
                self.neo4j_driver.close()
            except Exception:
                pass
        if self.redis_client is not None:
            try:
                await self.redis_client.aclose()
            except Exception:
                pass


conns = Connections()


def require_pg():
    """Return the Postgres pool or raise 503 with a clear message."""
    if conns.pg_pool is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "PostgreSQL is not reachable. Start the database stack "
                "(docker compose -f docker/docker-compose-enhanced-cognee.yml up -d) "
                "and restart the dashboard API."
            ),
        )
    return conns.pg_pool


# ---------------------------------------------------------------------------
# App + lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    await conns.init()
    yield
    await conns.close()


app = FastAPI(
    title="Enhanced Cognee Dashboard API",
    description="REST API for the Enhanced Cognee web dashboard",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class MemoryResponse(BaseModel):
    memory_id: str
    content: str
    data_type: str
    memory_type: Optional[str] = None
    memory_concept: Optional[str] = None
    summary: Optional[str] = None
    created_at: str
    updated_at: str
    char_count: Optional[int] = None
    estimated_tokens: Optional[int] = None
    agent_id: Optional[str] = None
    tags: Optional[List[str]] = None
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    files: Optional[List[str]] = None
    facts: Optional[List[str]] = None


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    agent_id: str
    start_time: str
    end_time: Optional[str] = None
    summary: Optional[str] = None
    memory_count: int


class SystemStatsResponse(BaseModel):
    total_memories: int
    total_sessions: int
    active_sessions: int
    avg_tokens_per_memory: float
    token_efficiency_percent: float
    database_status: Dict[str, bool]
    server_uptime: str


class SearchResponse(BaseModel):
    query: str
    result_count: int
    results: List[MemoryResponse]
    token_savings: Dict[str, Any]


class MemoryCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100000)
    agent_id: str = "default"
    memory_type: Optional[str] = None
    memory_concept: Optional[str] = None
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    files: Optional[List[str]] = None
    facts: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class MemoryUpdateRequest(BaseModel):
    content: Optional[str] = Field(None, max_length=100000)
    memory_type: Optional[str] = None
    memory_concept: Optional[str] = None
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    files: Optional[List[str]] = None
    facts: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_metadata(raw: Any) -> Dict[str, Any]:
    """asyncpg returns jsonb columns as str by default."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    return {}


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def _iso(dt: Any) -> str:
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return str(dt)


def _row_to_memory(row: Any) -> MemoryResponse:
    meta = _parse_metadata(row["metadata"])
    content = row["content"] or ""
    summary = meta.get("summary")
    if not summary:
        summary = content[:200] + "..." if len(content) > 200 else content
    return MemoryResponse(
        memory_id=str(row["id"]),
        content=content,
        data_type=meta.get("data_type", "text"),
        memory_type=meta.get("memory_type") or row["memory_category"],
        memory_concept=meta.get("memory_concept"),
        summary=summary,
        created_at=_iso(row["created_at"]),
        updated_at=_iso(row["updated_at"] or row["created_at"]),
        char_count=len(content),
        estimated_tokens=_estimate_tokens(content),
        agent_id=row["agent_id"],
        tags=list(row["tags"]) if row["tags"] else [],
        before_state=meta.get("before_state"),
        after_state=meta.get("after_state"),
        files=meta.get("files"),
        facts=meta.get("facts"),
    )


MEMORY_COLUMNS = (
    "id, content, agent_id, memory_category, tags, metadata, created_at, updated_at"
)


async def _check_postgres() -> bool:
    if conns.pg_pool is None:
        return False
    try:
        async with conns.pg_pool.acquire() as conn:
            await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=3)
        return True
    except Exception:
        return False


def _check_neo4j_sync() -> bool:
    if conns.neo4j_driver is not None:
        try:
            with conns.neo4j_driver.session(database=NEO4J_DATABASE) as session:
                session.run("RETURN 1").single()
            return True
        except Exception:
            return False
    if conns.graph_http is not None:
        try:
            _arcadedb_request(conns.graph_http, "/api/v1/databases")
            return True
        except Exception:
            return False
    return False


async def _check_redis() -> bool:
    if conns.redis_client is None:
        return False
    try:
        return bool(await asyncio.wait_for(conns.redis_client.ping(), timeout=3))
    except Exception:
        return False


async def _check_qdrant() -> bool:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"http://{QDRANT_HOST}:{QDRANT_PORT}/readyz")
            return resp.status_code == 200
    except Exception:
        return False


async def _database_status() -> Dict[str, bool]:
    pg, redis_ok, qdrant_ok = await asyncio.gather(
        _check_postgres(), _check_redis(), _check_qdrant()
    )
    neo4j_ok = await asyncio.to_thread(_check_neo4j_sync)
    return {
        "postgresql": pg,
        "qdrant": qdrant_ok,
        "neo4j": neo4j_ok,
        "redis": redis_ok,
    }


def _run_cypher(query: str, params: Optional[Dict[str, Any]] = None) -> List[Any]:
    """Run a read query against the graph DB (sync driver, call via to_thread)."""
    with conns.neo4j_driver.session(database=NEO4J_DATABASE) as session:
        return list(session.run(query, params or {}))


def _graph_node_dict(node: Any) -> Dict[str, Any]:
    labels = list(getattr(node, "labels", [])) or ["node"]
    props = dict(node)
    label_text = (
        props.get("name")
        or props.get("title")
        or props.get("content", "")[:60]
        or str(node.element_id)
    )
    return {
        "id": str(node.element_id),
        "label": str(label_text),
        "type": labels[0].lower(),
        "properties": {k: str(v)[:500] for k, v in props.items()},
        "importance": float(props.get("importance", 1.0) or 1.0),
    }


def _graph_edge_dict(rel: Any) -> Dict[str, Any]:
    props = dict(rel)
    return {
        "id": str(rel.element_id),
        "source": str(rel.start_node.element_id),
        "target": str(rel.end_node.element_id),
        "label": rel.type.lower(),
        "type": rel.type.lower(),
        "strength": float(props.get("strength", props.get("confidence", 1.0)) or 1.0),
        "properties": {k: str(v)[:500] for k, v in props.items()},
    }


def _arcade_node_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an ArcadeDB HTTP vertex document to the dashboard node shape."""
    rid = str(doc.get("@rid", ""))
    props = {k: v for k, v in doc.items() if not k.startswith("@")}
    label = (
        props.get("name")
        or props.get("title")
        or str(props.get("content", ""))[:60]
        or rid
    )
    try:
        importance = float(props.get("importance", 1.0) or 1.0)
    except (TypeError, ValueError):
        importance = 1.0
    return {
        "id": rid,
        "label": str(label),
        "type": str(doc.get("@type", "node")).lower(),
        "properties": {k: str(v)[:500] for k, v in props.items()},
        "importance": importance,
    }


def _arcade_edge_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an ArcadeDB HTTP edge document to the dashboard edge shape."""
    props = {k: v for k, v in doc.items() if not k.startswith("@")}
    edge_type = str(doc.get("@type", "related")).lower()
    try:
        strength = float(props.get("strength", props.get("confidence", 1.0)) or 1.0)
    except (TypeError, ValueError):
        strength = 1.0
    return {
        "id": str(doc.get("@rid", "")),
        "source": str(doc.get("@out", "")),
        "target": str(doc.get("@in", "")),
        "label": edge_type,
        "type": edge_type,
        "strength": strength,
        "properties": {k: str(v)[:500] for k, v in props.items()},
    }


def _graph_payload(
    nodes: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]]
) -> Dict[str, Any]:
    node_types: Dict[str, int] = {}
    for n in nodes.values():
        node_types[n["type"]] = node_types.get(n["type"], 0) + 1
    edge_types: Dict[str, int] = {}
    for e in edges:
        edge_types[e["type"]] = edge_types.get(e["type"], 0) + 1
    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "metadata": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "node_types": node_types,
            "edge_types": edge_types,
        },
    }


async def _graph_from_postgres(limit: int) -> Dict[str, Any]:
    """Fallback graph built from shared_memory.entities/relationships."""
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    if conns.pg_pool is None:
        return _graph_payload(nodes, edges)
    try:
        async with conns.pg_pool.acquire() as conn:
            entity_rows = await conn.fetch(
                f"""SELECT id, name, entity_type, confidence_score
                    FROM {ENTITIES} ORDER BY created_at DESC LIMIT $1""",
                limit,
            )
            for row in entity_rows:
                nodes[str(row["id"])] = {
                    "id": str(row["id"]),
                    "label": row["name"],
                    "type": (row["entity_type"] or "entity").lower(),
                    "properties": {},
                    "importance": float(row["confidence_score"] or 1.0),
                }
            rel_rows = await conn.fetch(
                f"""SELECT id, source_entity_id, target_entity_id,
                           relationship_type, confidence_score
                    FROM {RELATIONSHIPS}
                    WHERE source_entity_id = ANY($1::uuid[])
                      AND target_entity_id = ANY($1::uuid[])
                    LIMIT $2""",
                [uuid.UUID(k) for k in nodes],
                limit * 4,
            )
            for row in rel_rows:
                edges.append(
                    {
                        "id": str(row["id"]),
                        "source": str(row["source_entity_id"]),
                        "target": str(row["target_entity_id"]),
                        "label": (row["relationship_type"] or "related").lower(),
                        "type": (row["relationship_type"] or "related").lower(),
                        "strength": float(row["confidence_score"] or 1.0),
                        "properties": {},
                    }
                )
    except Exception as exc:
        logger.warning("WARN Postgres graph fallback failed: %s", exc)
    return _graph_payload(nodes, edges)


# ---------------------------------------------------------------------------
# Health + stats
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_check():
    """Health check endpoint with real backend connectivity flags."""
    status = await _database_status()
    healthy = status["postgresql"]
    return {
        "status": "healthy" if healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
        "databases": status,
    }


@app.get("/api/stats", response_model=SystemStatsResponse)
async def get_system_stats():
    """Get system statistics from the live databases."""
    db_status = await _database_status()
    uptime = datetime.now(timezone.utc) - SERVER_STARTED_AT
    uptime_str = str(uptime).split(".")[0]

    total_memories = 0
    total_sessions = 0
    active_sessions = 0
    avg_tokens = 0.0
    efficiency = 0.0

    if conns.pg_pool is not None:
        try:
            async with conns.pg_pool.acquire() as conn:
                total_memories = (
                    await conn.fetchval(f"SELECT COUNT(*) FROM {DOCUMENTS}") or 0
                )
                avg_chars = (
                    await conn.fetchval(
                        f"SELECT AVG(LENGTH(coalesce(content, ''))) FROM {DOCUMENTS}"
                    )
                    or 0
                )
                avg_tokens = round(float(avg_chars) / 4.0, 1)
                try:
                    total_sessions = (
                        await conn.fetchval(f"SELECT COUNT(*) FROM {SESSIONS}") or 0
                    )
                    active_sessions = (
                        await conn.fetchval(
                            f"SELECT COUNT(*) FROM {SESSIONS} WHERE end_time IS NULL"
                        )
                        or 0
                    )
                except Exception:
                    # sessions table may not exist on older deployments
                    total_sessions = 0
                    active_sessions = 0
                # Token efficiency: how much smaller summaries are vs content
                # for memories that carry a summary in metadata.
                row = await conn.fetchrow(
                    f"""SELECT AVG(LENGTH(coalesce(content, ''))) AS avg_content,
                               AVG(LENGTH(metadata->>'summary')) AS avg_summary
                        FROM {DOCUMENTS}
                        WHERE metadata ? 'summary'"""
                )
                if row and row["avg_content"] and row["avg_summary"]:
                    saved = 1.0 - float(row["avg_summary"]) / float(row["avg_content"])
                    efficiency = round(max(0.0, min(1.0, saved)) * 100.0, 1)
        except Exception as exc:
            logger.error("ERR stats query failed: %s", exc)

    return SystemStatsResponse(
        total_memories=int(total_memories),
        total_sessions=int(total_sessions),
        active_sessions=int(active_sessions),
        avg_tokens_per_memory=avg_tokens,
        token_efficiency_percent=efficiency,
        database_status=db_status,
        server_uptime=uptime_str,
    )


# ---------------------------------------------------------------------------
# Memories CRUD
# ---------------------------------------------------------------------------


@app.get("/api/memories", response_model=List[MemoryResponse])
async def list_memories(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    agent_id: Optional[str] = Query(None),
    memory_type: Optional[str] = Query(None),
    memory_concept: Optional[str] = Query(None),
):
    """List memories with pagination and filtering (newest first)."""
    pool = require_pg()
    clauses = []
    params: List[Any] = []

    def param(value: Any) -> str:
        params.append(value)
        return f"${len(params)}"

    if agent_id:
        clauses.append(f"agent_id = {param(agent_id)}")
    if memory_type:
        ph = param(memory_type)
        clauses.append(f"(metadata->>'memory_type' = {ph} OR memory_category = {ph})")
    if memory_concept:
        clauses.append(f"metadata->>'memory_concept' = {param(memory_concept)}")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""SELECT {MEMORY_COLUMNS} FROM {DOCUMENTS} {where}
              ORDER BY created_at DESC
              LIMIT {param(limit)} OFFSET {param(offset)}"""
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        return [_row_to_memory(r) for r in rows]
    except Exception as exc:
        logger.error("ERR list_memories failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list memories")


@app.get("/api/memories/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: str):
    """Get a specific memory by ID."""
    pool = require_pg()
    try:
        mem_uuid = uuid.UUID(memory_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid memory id format")
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {MEMORY_COLUMNS} FROM {DOCUMENTS} WHERE id = $1", mem_uuid
            )
    except Exception as exc:
        logger.error("ERR get_memory failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch memory")
    if row is None:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
    return _row_to_memory(row)


@app.post("/api/memories", response_model=MemoryResponse, status_code=201)
async def add_memory(request: MemoryCreateRequest):
    """Add a new memory (persisted to PostgreSQL)."""
    pool = require_pg()
    memory_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    metadata: Dict[str, Any] = {"source": "dashboard"}
    for key in ("memory_type", "memory_concept", "before_state", "after_state"):
        value = getattr(request, key)
        if value:
            metadata[key] = value
    if request.files:
        metadata["files"] = request.files
    if request.facts:
        metadata["facts"] = request.facts

    category = (request.memory_type or "general").lower()
    title = request.content.strip().splitlines()[0][:200] or "Dashboard memory"
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                f"""INSERT INTO {DOCUMENTS}
                    (id, title, content, agent_id, memory_category, tags,
                     metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $8)""",
                memory_id,
                title,
                request.content,
                request.agent_id,
                category,
                request.tags or [],
                json.dumps(metadata),
                now,
            )
            row = await conn.fetchrow(
                f"SELECT {MEMORY_COLUMNS} FROM {DOCUMENTS} WHERE id = $1", memory_id
            )
        logger.info("OK memory added: %s", memory_id)
        return _row_to_memory(row)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("ERR add_memory failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to add memory")


@app.patch("/api/memories/{memory_id}", response_model=MemoryResponse)
async def update_memory(memory_id: str, request: MemoryUpdateRequest):
    """Update an existing memory (content and/or structured metadata)."""
    pool = require_pg()
    try:
        mem_uuid = uuid.UUID(memory_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid memory id format")

    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {MEMORY_COLUMNS} FROM {DOCUMENTS} WHERE id = $1", mem_uuid
            )
            if row is None:
                raise HTTPException(
                    status_code=404, detail=f"Memory {memory_id} not found"
                )
            meta = _parse_metadata(row["metadata"])
            for key in (
                "memory_type",
                "memory_concept",
                "before_state",
                "after_state",
                "files",
                "facts",
            ):
                if key in updates and updates[key] is not None:
                    meta[key] = updates[key]
            new_content = updates.get("content", row["content"])
            new_category = (
                updates["memory_type"].lower()
                if updates.get("memory_type")
                else row["memory_category"]
            )
            await conn.execute(
                f"""UPDATE {DOCUMENTS}
                    SET content = $2, metadata = $3::jsonb,
                        memory_category = $4, updated_at = $5
                    WHERE id = $1""",
                mem_uuid,
                new_content,
                json.dumps(meta),
                new_category,
                datetime.now(timezone.utc),
            )
            row = await conn.fetchrow(
                f"SELECT {MEMORY_COLUMNS} FROM {DOCUMENTS} WHERE id = $1", mem_uuid
            )
        logger.info("OK memory updated: %s", memory_id)
        return _row_to_memory(row)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("ERR update_memory failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update memory")


@app.delete("/api/memories/{memory_id}", status_code=204)
async def delete_memory(memory_id: str):
    """Delete a memory by ID."""
    pool = require_pg()
    try:
        mem_uuid = uuid.UUID(memory_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid memory id format")
    try:
        async with pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {DOCUMENTS} WHERE id = $1", mem_uuid
            )
    except Exception as exc:
        logger.error("ERR delete_memory failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to delete memory")
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
    logger.info("OK memory deleted: %s", memory_id)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@app.get("/api/search", response_model=SearchResponse)
async def search_memories(
    query: str = Query(..., min_length=1),
    agent_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Full-text search over memories (ts_rank ordered, ILIKE fallback)."""
    pool = require_pg()
    results: List[MemoryResponse] = []
    try:
        async with pool.acquire() as conn:
            agent_clause = "AND agent_id = $3" if agent_id else ""
            params: List[Any] = [query, limit]
            if agent_id:
                params.append(agent_id)
            rows = await conn.fetch(
                f"""SELECT {MEMORY_COLUMNS},
                           ts_rank(to_tsvector('english', coalesce(content, '')),
                                   plainto_tsquery('english', $1)) AS rank
                    FROM {DOCUMENTS}
                    WHERE to_tsvector('english', coalesce(content, ''))
                          @@ plainto_tsquery('english', $1)
                      {agent_clause}
                    ORDER BY rank DESC, created_at DESC
                    LIMIT $2""",
                *params,
            )
            if not rows:
                # Fallback for partial words / non-English terms
                rows = await conn.fetch(
                    f"""SELECT {MEMORY_COLUMNS} FROM {DOCUMENTS}
                        WHERE content ILIKE '%' || $1 || '%'
                          {agent_clause}
                        ORDER BY created_at DESC
                        LIMIT $2""",
                    *params,
                )
            results = [_row_to_memory(r) for r in rows]
    except Exception as exc:
        logger.error("ERR search failed: %s", exc)
        raise HTTPException(status_code=500, detail="Search failed")

    full_tokens = sum(m.estimated_tokens or 0 for m in results)
    summary_tokens = sum(_estimate_tokens(m.summary or "") for m in results)
    return SearchResponse(
        query=query,
        result_count=len(results),
        results=results,
        token_savings={
            "full_content_tokens": full_tokens,
            "summary_tokens": summary_tokens,
            "saved_tokens": max(0, full_tokens - summary_tokens),
        },
    )


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

SESSION_QUERY = f"""
    SELECT s.id, s.user_id, s.agent_id, s.start_time, s.end_time, s.summary,
           (SELECT COUNT(*) FROM {DOCUMENTS} d WHERE d.session_id = s.id)
               AS memory_count
    FROM {SESSIONS} s
"""


def _row_to_session(row: Any) -> SessionResponse:
    return SessionResponse(
        session_id=str(row["id"]),
        user_id=row["user_id"],
        agent_id=row["agent_id"],
        start_time=_iso(row["start_time"]),
        end_time=_iso(row["end_time"]) or None,
        summary=row["summary"],
        memory_count=int(row["memory_count"] or 0),
    )


@app.get("/api/sessions", response_model=List[SessionResponse])
async def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    agent_id: Optional[str] = Query(None),
    active_only: bool = Query(False),
):
    """List sessions (newest first)."""
    pool = require_pg()
    clauses = []
    params: List[Any] = []
    if agent_id:
        params.append(agent_id)
        clauses.append(f"s.agent_id = ${len(params)}")
    if active_only:
        clauses.append("s.end_time IS NULL")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"{SESSION_QUERY} {where} ORDER BY s.start_time DESC LIMIT ${len(params)}",
                *params,
            )
        return [_row_to_session(r) for r in rows]
    except Exception as exc:
        logger.warning("WARN list_sessions failed (table missing?): %s", exc)
        return []


@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session details."""
    pool = require_pg()
    try:
        sess_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session id format")
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(f"{SESSION_QUERY} WHERE s.id = $1", sess_uuid)
    except Exception as exc:
        logger.error("ERR get_session failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch session")
    if row is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return _row_to_session(row)


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


@app.get("/api/timeline/{memory_id}")
async def get_timeline(
    memory_id: str,
    before: int = Query(5, ge=0, le=20),
    after: int = Query(5, ge=0, le=20),
):
    """Get timeline context (chronological neighbors by the same agent)."""
    pool = require_pg()
    try:
        mem_uuid = uuid.UUID(memory_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid memory id format")
    try:
        async with pool.acquire() as conn:
            current = await conn.fetchrow(
                f"SELECT {MEMORY_COLUMNS} FROM {DOCUMENTS} WHERE id = $1", mem_uuid
            )
            if current is None:
                raise HTTPException(
                    status_code=404, detail=f"Memory {memory_id} not found"
                )
            before_rows = await conn.fetch(
                f"""SELECT {MEMORY_COLUMNS} FROM {DOCUMENTS}
                    WHERE agent_id = $1 AND created_at < $2
                    ORDER BY created_at DESC LIMIT $3""",
                current["agent_id"],
                current["created_at"],
                before,
            )
            after_rows = await conn.fetch(
                f"""SELECT {MEMORY_COLUMNS} FROM {DOCUMENTS}
                    WHERE agent_id = $1 AND created_at > $2
                    ORDER BY created_at ASC LIMIT $3""",
                current["agent_id"],
                current["created_at"],
                after,
            )
        return {
            "memory_id": memory_id,
            "before": [
                _row_to_memory(r).model_dump() for r in reversed(before_rows)
            ],
            "current": _row_to_memory(current).model_dump(),
            "after": [_row_to_memory(r).model_dump() for r in after_rows],
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("ERR timeline failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to build timeline")


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


@app.get("/api/graph")
async def get_graph_data(
    limit: int = Query(100, ge=1, le=1000),
    node_type: Optional[str] = Query(None),
    edge_type: Optional[str] = Query(None),
    node_id: Optional[str] = Query(None),
    depth: int = Query(2, ge=1, le=5),
):
    """Get knowledge-graph data for visualization (graph DB, PG fallback)."""
    if conns.neo4j_driver is not None:
        try:
            if node_id:
                records = await asyncio.to_thread(
                    _run_cypher,
                    "MATCH (n) WHERE elementId(n) = $node_id "
                    f"MATCH path = (n)-[*1..{depth}]-(m) "
                    "UNWIND relationships(path) AS r "
                    "RETURN DISTINCT startNode(r) AS a, r, endNode(r) AS b "
                    "LIMIT $limit",
                    {"node_id": node_id, "limit": limit},
                )
            else:
                records = await asyncio.to_thread(
                    _run_cypher,
                    "MATCH (a)-[r]->(b) RETURN a, r, b LIMIT $limit",
                    {"limit": limit},
                )
            nodes: Dict[str, Dict[str, Any]] = {}
            edges: List[Dict[str, Any]] = []
            seen_edges = set()
            for record in records:
                a, r, b = record["a"], record["r"], record["b"]
                for node in (a, b):
                    nd = _graph_node_dict(node)
                    if not node_type or nd["type"] == node_type.lower():
                        nodes[nd["id"]] = nd
                ed = _graph_edge_dict(r)
                if edge_type and ed["type"] != edge_type.lower():
                    continue
                if ed["id"] not in seen_edges and ed["source"] in nodes and ed["target"] in nodes:
                    seen_edges.add(ed["id"])
                    edges.append(ed)
            if not nodes:
                # Graph may have isolated nodes only
                records = await asyncio.to_thread(
                    _run_cypher, "MATCH (n) RETURN n LIMIT $limit", {"limit": limit}
                )
                for record in records:
                    nd = _graph_node_dict(record["n"])
                    nodes[nd["id"]] = nd
            return _graph_payload(nodes, edges)
        except Exception as exc:
            logger.warning("WARN graph query failed, using PG fallback: %s", exc)
    if conns.graph_http is not None:
        try:
            rows = await asyncio.to_thread(
                _http_cypher, f"MATCH (a)-[r]->(b) RETURN a, r, b LIMIT {int(limit)}"
            )
            nodes: Dict[str, Dict[str, Any]] = {}
            edges: List[Dict[str, Any]] = []
            seen_edges = set()
            for row in rows:
                a, r, b = row.get("a"), row.get("r"), row.get("b")
                if not (isinstance(a, dict) and isinstance(b, dict)):
                    continue
                for doc in (a, b):
                    nd = _arcade_node_dict(doc)
                    if not node_type or nd["type"] == node_type.lower():
                        nodes[nd["id"]] = nd
                if isinstance(r, dict):
                    ed = _arcade_edge_dict(r)
                    if edge_type and ed["type"] != edge_type.lower():
                        continue
                    if (
                        ed["id"] not in seen_edges
                        and ed["source"] in nodes
                        and ed["target"] in nodes
                    ):
                        seen_edges.add(ed["id"])
                        edges.append(ed)
            if not nodes:
                rows = await asyncio.to_thread(
                    _http_cypher, f"MATCH (n) RETURN n LIMIT {int(limit)}"
                )
                for row in rows:
                    doc = row.get("n")
                    if isinstance(doc, dict):
                        nd = _arcade_node_dict(doc)
                        nodes[nd["id"]] = nd
            return _graph_payload(nodes, edges)
        except Exception as exc:
            logger.warning("WARN HTTP graph query failed, using PG fallback: %s", exc)
    return await _graph_from_postgres(limit)


@app.get("/api/graph/node/{node_id}")
async def get_node_neighbors(node_id: str, depth: int = Query(1, ge=1, le=3)):
    """Get neighbors for a specific node."""
    if conns.neo4j_driver is None:
        if conns.graph_http is not None:
            try:
                rows = await asyncio.to_thread(
                    _http_cypher,
                    "MATCH (a)-[r]-(b) WHERE id(a) = $node_id "
                    "RETURN a, r, b LIMIT 500",
                    {"node_id": node_id},
                )
                nodes: Dict[str, Dict[str, Any]] = {}
                edges: List[Dict[str, Any]] = []
                seen = set()
                for row in rows:
                    for doc in (row.get("a"), row.get("b")):
                        if isinstance(doc, dict):
                            nd = _arcade_node_dict(doc)
                            nodes[nd["id"]] = nd
                    r = row.get("r")
                    if isinstance(r, dict):
                        ed = _arcade_edge_dict(r)
                        if ed["id"] not in seen:
                            seen.add(ed["id"])
                            edges.append(ed)
                return _graph_payload(nodes, edges)
            except Exception as exc:
                logger.error("ERR HTTP node neighbors failed: %s", exc)
        return _graph_payload({}, [])
    try:
        records = await asyncio.to_thread(
            _run_cypher,
            "MATCH (n) WHERE elementId(n) = $node_id "
            f"MATCH path = (n)-[*1..{depth}]-(m) "
            "UNWIND relationships(path) AS r "
            "RETURN DISTINCT startNode(r) AS a, r, endNode(r) AS b LIMIT 500",
            {"node_id": node_id},
        )
        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []
        seen = set()
        for record in records:
            for node in (record["a"], record["b"]):
                nd = _graph_node_dict(node)
                nodes[nd["id"]] = nd
            ed = _graph_edge_dict(record["r"])
            if ed["id"] not in seen:
                seen.add(ed["id"])
                edges.append(ed)
        return _graph_payload(nodes, edges)
    except Exception as exc:
        logger.error("ERR node neighbors failed: %s", exc)
        return _graph_payload({}, [])


@app.get("/api/graph/search")
async def search_graph_nodes(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Search for nodes in the graph by name/title/content."""
    if conns.neo4j_driver is not None:
        try:
            records = await asyncio.to_thread(
                _run_cypher,
                "MATCH (n) WHERE toLower(coalesce(n.name, '')) CONTAINS toLower($q) "
                "OR toLower(coalesce(n.title, '')) CONTAINS toLower($q) "
                "OR toLower(coalesce(n.content, '')) CONTAINS toLower($q) "
                "RETURN n LIMIT $limit",
                {"q": query, "limit": limit},
            )
            return [_graph_node_dict(r["n"]) for r in records]
        except Exception as exc:
            logger.warning("WARN graph search failed, using PG fallback: %s", exc)
    if conns.graph_http is not None:
        try:
            rows = await asyncio.to_thread(
                _http_cypher,
                "MATCH (n) WHERE toLower(coalesce(n.name, '')) CONTAINS toLower($q) "
                "OR toLower(coalesce(n.title, '')) CONTAINS toLower($q) "
                f"RETURN n LIMIT {int(limit)}",
                {"q": query},
            )
            return [
                _arcade_node_dict(row["n"])
                for row in rows
                if isinstance(row.get("n"), dict)
            ]
        except Exception as exc:
            logger.warning("WARN HTTP graph search failed, using PG fallback: %s", exc)
    if conns.pg_pool is not None:
        try:
            async with conns.pg_pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""SELECT id, name, entity_type, confidence_score
                        FROM {ENTITIES}
                        WHERE name ILIKE '%' || $1 || '%'
                        LIMIT $2""",
                    query,
                    limit,
                )
            return [
                {
                    "id": str(r["id"]),
                    "label": r["name"],
                    "type": (r["entity_type"] or "entity").lower(),
                    "properties": {},
                    "importance": float(r["confidence_score"] or 1.0),
                }
                for r in rows
            ]
        except Exception as exc:
            logger.error("ERR entity search failed: %s", exc)
    return []


# Backwards-compatible alias for the old (typo) route shipped in v1.
@app.get("/api_graph/search", include_in_schema=False)
async def search_graph_nodes_legacy(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    return await search_graph_nodes(query=query, limit=limit)


@app.get("/api/graph/node/{node_id}/details")
async def get_node_details(node_id: str):
    """Get detailed information about a node, including direct connections."""
    if conns.neo4j_driver is not None:
        try:
            records = await asyncio.to_thread(
                _run_cypher,
                "MATCH (n) WHERE elementId(n) = $node_id "
                "OPTIONAL MATCH (n)-[r]-(m) "
                "RETURN n, r, m LIMIT 100",
                {"node_id": node_id},
            )
            if records:
                node = _graph_node_dict(records[0]["n"])
                connections = []
                related = []
                for record in records:
                    if record["r"] is not None and record["m"] is not None:
                        connections.append(_graph_edge_dict(record["r"]))
                        related.append(_graph_node_dict(record["m"]))
                return {"node": node, "connections": connections, "related_nodes": related}
        except Exception as exc:
            logger.error("ERR node details failed: %s", exc)
    if conns.graph_http is not None:
        try:
            rows = await asyncio.to_thread(
                _http_cypher,
                "MATCH (n) WHERE id(n) = $node_id RETURN n LIMIT 1",
                {"node_id": node_id},
            )
            if rows and isinstance(rows[0].get("n"), dict):
                node = _arcade_node_dict(rows[0]["n"])
                neighbor_rows = await asyncio.to_thread(
                    _http_cypher,
                    "MATCH (a)-[r]-(b) WHERE id(a) = $node_id "
                    "RETURN r, b LIMIT 100",
                    {"node_id": node_id},
                )
                connections = []
                related = []
                for row in neighbor_rows:
                    if isinstance(row.get("r"), dict):
                        connections.append(_arcade_edge_dict(row["r"]))
                    if isinstance(row.get("b"), dict):
                        related.append(_arcade_node_dict(row["b"]))
                return {
                    "node": node,
                    "connections": connections,
                    "related_nodes": related,
                }
        except Exception as exc:
            logger.error("ERR HTTP node details failed: %s", exc)
    raise HTTPException(status_code=404, detail=f"Node {node_id} not found")


@app.get("/api/graph/stats")
async def get_graph_statistics():
    """Get graph statistics."""
    if conns.neo4j_driver is not None:
        try:
            node_records = await asyncio.to_thread(
                _run_cypher,
                "MATCH (n) UNWIND labels(n) AS label "
                "RETURN label, count(*) AS cnt",
            )
            edge_records = await asyncio.to_thread(
                _run_cypher,
                "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt",
            )
            node_dist = {r["label"].lower(): r["cnt"] for r in node_records}
            edge_dist = {r["type"].lower(): r["cnt"] for r in edge_records}
            total_nodes = sum(node_dist.values())
            total_edges = sum(edge_dist.values())
            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "node_type_distribution": node_dist,
                "edge_type_distribution": edge_dist,
                "avg_degree": round(2.0 * total_edges / total_nodes, 2)
                if total_nodes
                else 0.0,
                "connected_components": 0,
            }
        except Exception as exc:
            logger.warning("WARN graph stats failed: %s", exc)
    if conns.graph_http is not None:
        try:
            node_rows = await asyncio.to_thread(
                _http_cypher, "MATCH (n) RETURN n LIMIT 2000"
            )
            edge_rows = await asyncio.to_thread(
                _http_cypher, "MATCH ()-[r]->() RETURN r LIMIT 4000"
            )
            node_dist: Dict[str, int] = {}
            for row in node_rows:
                doc = row.get("n")
                if isinstance(doc, dict):
                    t = str(doc.get("@type", "node")).lower()
                    node_dist[t] = node_dist.get(t, 0) + 1
            edge_dist: Dict[str, int] = {}
            for row in edge_rows:
                doc = row.get("r")
                if isinstance(doc, dict):
                    t = str(doc.get("@type", "related")).lower()
                    edge_dist[t] = edge_dist.get(t, 0) + 1
            total_nodes = sum(node_dist.values())
            total_edges = sum(edge_dist.values())
            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "node_type_distribution": node_dist,
                "edge_type_distribution": edge_dist,
                "avg_degree": round(2.0 * total_edges / total_nodes, 2)
                if total_nodes
                else 0.0,
                "connected_components": 0,
            }
        except Exception as exc:
            logger.warning("WARN HTTP graph stats failed: %s", exc)
    payload = await _graph_from_postgres(1000)
    meta = payload["metadata"]
    return {
        "total_nodes": meta["total_nodes"],
        "total_edges": meta["total_edges"],
        "node_type_distribution": meta["node_types"],
        "edge_type_distribution": meta["edge_types"],
        "avg_degree": round(2.0 * meta["total_edges"] / meta["total_nodes"], 2)
        if meta["total_nodes"]
        else 0.0,
        "connected_components": 0,
    }


# ---------------------------------------------------------------------------
# Activity + structured stats
# ---------------------------------------------------------------------------


@app.get("/api/activity")
async def get_activity_data(
    days: int = Query(365, ge=1, le=365),
    agent_id: Optional[str] = Query(None),
):
    """Get per-day memory counts for the heatmap."""
    pool = require_pg()
    params: List[Any] = [days]
    agent_clause = ""
    if agent_id:
        params.append(agent_id)
        agent_clause = "AND agent_id = $2"
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""SELECT DATE(created_at) AS day, COUNT(*) AS cnt
                    FROM {DOCUMENTS}
                    WHERE created_at >= NOW() - ($1::int * INTERVAL '1 day')
                      {agent_clause}
                    GROUP BY DATE(created_at)
                    ORDER BY day""",
                *params,
            )
        activity = {str(r["day"]): int(r["cnt"]) for r in rows}
        return {
            "activity": activity,
            "total": sum(activity.values()),
            "max_per_day": max(activity.values()) if activity else 0,
        }
    except Exception as exc:
        logger.error("ERR activity query failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load activity data")


@app.get("/api/structured-stats")
async def get_structured_stats():
    """Get structured memory statistics grouped by memory type."""
    pool = require_pg()
    counts = {
        "total_observations": 0,
        "bugfix_count": 0,
        "feature_count": 0,
        "decision_count": 0,
        "refactor_count": 0,
        "discovery_count": 0,
        "general_count": 0,
    }
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""SELECT LOWER(coalesce(metadata->>'memory_type',
                                          memory_category, 'general')) AS mtype,
                           COUNT(*) AS cnt
                    FROM {DOCUMENTS}
                    GROUP BY mtype"""
            )
        for row in rows:
            counts["total_observations"] += int(row["cnt"])
            key = f"{row['mtype']}_count"
            if key in counts:
                counts[key] += int(row["cnt"])
            else:
                counts["general_count"] += int(row["cnt"])
        return counts
    except Exception as exc:
        logger.error("ERR structured stats failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load structured stats")


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


@app.get("/api/agents")
async def list_agents():
    """List all agents that own memories, with counts and last activity."""
    pool = require_pg()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""SELECT agent_id,
                           COUNT(*) AS memory_count,
                           MAX(created_at) AS last_activity,
                           COUNT(DISTINCT memory_category) AS category_count
                    FROM {DOCUMENTS}
                    WHERE agent_id IS NOT NULL
                    GROUP BY agent_id
                    ORDER BY memory_count DESC"""
            )
        return [
            {
                "agent_id": r["agent_id"],
                "memory_count": int(r["memory_count"]),
                "last_activity": _iso(r["last_activity"]),
                "category_count": int(r["category_count"]),
            }
            for r in rows
        ]
    except Exception as exc:
        logger.error("ERR list_agents failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list agents")


# ---------------------------------------------------------------------------
# Auth (local single-user mode unless DASHBOARD_JWT_SECRET is configured)
# ---------------------------------------------------------------------------


@app.get("/api/security/user")
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Get current user. In local mode (no JWT secret) returns a default user."""
    jwt_secret = os.getenv("DASHBOARD_JWT_SECRET")
    if not jwt_secret:
        return {
            "user_id": "local",
            "username": "Local User",
            "role": "admin",
            "auth_mode": "local",
        }
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        import jwt as pyjwt

        payload = pyjwt.decode(credentials.credentials, jwt_secret, algorithms=["HS256"])
        return {
            "user_id": payload.get("sub", "unknown"),
            "username": payload.get("name", payload.get("sub", "unknown")),
            "role": payload.get("role", "user"),
            "auth_mode": "jwt",
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ---------------------------------------------------------------------------
# SSE stream (real updates: polls for new memories)
# ---------------------------------------------------------------------------


@app.get("/api/stream")
async def stream_updates():
    """
    SSE endpoint for real-time dashboard updates.

    Emits a "message" event whenever new memories appear (5s polling), and a
    "keepalive" event every 30 seconds.
    """

    async def event_generator():
        last_count: Optional[int] = None
        ticks = 0
        try:
            while True:
                ticks += 1
                if conns.pg_pool is not None:
                    try:
                        async with conns.pg_pool.acquire() as conn:
                            count = await conn.fetchval(
                                f"SELECT COUNT(*) FROM {DOCUMENTS}"
                            )
                        if last_count is not None and count != last_count:
                            payload = json.dumps(
                                {
                                    "type": "memories_changed",
                                    "total": int(count),
                                    "timestamp": datetime.now(
                                        timezone.utc
                                    ).isoformat(),
                                }
                            )
                            yield f"event: message\ndata: {payload}\n\n"
                        last_count = count
                    except Exception:
                        pass
                if ticks % 6 == 0:
                    ka = json.dumps(
                        {"timestamp": datetime.now(timezone.utc).isoformat()}
                    )
                    yield f"event: keepalive\ndata: {ka}\n\n"
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("SSE client disconnected")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ---------------------------------------------------------------------------
# Built-in lightweight HTML view (fallback when Next.js frontend is not used)
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def dashboard_root():
    """Serve a minimal built-in dashboard (the full UI runs on port 9050)."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Enhanced Cognee Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header a { color: #3b82f6; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stat-value { font-size: 2em; font-weight: bold; color: #3b82f6; }
            .stat-label { color: #64748b; font-size: 0.9em; }
            .memories-list { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .memory-item { padding: 15px; border-bottom: 1px solid #e5e7eb; }
            .memory-item:last-child { border-bottom: none; }
            .memory-type { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; background: #dbeafe; color: #1e40af; margin-right: 8px; }
            .search-box { display: flex; gap: 10px; margin-bottom: 20px; }
            .search-box input { flex: 1; padding: 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
            .search-box button { padding: 12px 24px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; }
            .search-box button:hover { background: #2563eb; }
            .status { position: fixed; bottom: 20px; right: 20px; padding: 10px 20px; background: #10b981; color: white; border-radius: 6px; font-size: 0.9em; }
            .status.err { background: #ef4444; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Enhanced Cognee Dashboard (built-in view)</h1>
                <p>Quick status view. The full dashboard runs at
                   <a href="http://localhost:9050">http://localhost:9050</a>.</p>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" id="total-memories">-</div>
                    <div class="stat-label">Total Memories</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="total-sessions">-</div>
                    <div class="stat-label">Sessions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="token-efficiency">-</div>
                    <div class="stat-label">Token Efficiency</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="server-status">...</div>
                    <div class="stat-label">System Status</div>
                </div>
            </div>

            <div class="search-box">
                <input type="text" id="search-input" placeholder="Search memories..."
                       onkeydown="if(event.key==='Enter')searchMemories()" />
                <button onclick="searchMemories()">Search</button>
            </div>

            <div class="memories-list" id="memories-list">
                <div style="text-align: center; color: #9ca3af; padding: 40px;">
                    Loading memories...
                </div>
            </div>

            <div class="status" id="status"><span>Connecting...</span></div>
        </div>

        <script>
            function esc(s) {
                return String(s ?? '').replace(/[&<>"']/g, c => ({
                    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
                })[c]);
            }

            function renderMemories(memories) {
                const listDiv = document.getElementById('memories-list');
                if (!memories.length) {
                    listDiv.innerHTML = '<div style="text-align:center;color:#9ca3af;padding:40px;">' +
                        'No memories yet. Add one via the full dashboard or the MCP tools.</div>';
                    return;
                }
                listDiv.innerHTML = memories.map(m => `
                    <div class="memory-item">
                        <div>
                            ${m.memory_type ? `<span class="memory-type">${esc(m.memory_type)}</span>` : ''}
                            ${m.agent_id ? `<span class="memory-type" style="background:#fef3c7;color:#92400e;">${esc(m.agent_id)}</span>` : ''}
                        </div>
                        <div>${esc(m.summary || m.content.substring(0, 200))}</div>
                        <div style="font-size: 0.8em; color: #9ca3af; margin-top: 8px;">
                            ${new Date(m.created_at).toLocaleString()}
                        </div>
                    </div>
                `).join('');
            }

            async function loadStats() {
                try {
                    const response = await fetch('/api/stats');
                    const stats = await response.json();
                    document.getElementById('total-memories').textContent = stats.total_memories;
                    document.getElementById('total-sessions').textContent = stats.total_sessions;
                    document.getElementById('token-efficiency').textContent = stats.token_efficiency_percent + '%';
                    const allOk = stats.database_status.postgresql;
                    document.getElementById('server-status').textContent = allOk ? 'OK' : 'ERR';
                    const statusEl = document.getElementById('status');
                    statusEl.className = allOk ? 'status' : 'status err';
                    statusEl.innerHTML = allOk ? '<span>[OK] Connected</span>'
                                               : '<span>[ERR] Database offline</span>';
                } catch (error) {
                    document.getElementById('status').className = 'status err';
                    document.getElementById('status').innerHTML = '<span>[ERR] API unreachable</span>';
                }
            }

            async function loadMemories() {
                try {
                    const response = await fetch('/api/memories?limit=20');
                    renderMemories(await response.json());
                } catch (error) {
                    document.getElementById('memories-list').innerHTML =
                        '<div style="text-align:center;color:#ef4444;padding:40px;">Failed to load memories</div>';
                }
            }

            async function searchMemories() {
                const query = document.getElementById('search-input').value;
                if (!query) { loadMemories(); return; }
                try {
                    const response = await fetch(`/api/search?query=${encodeURIComponent(query)}&limit=20`);
                    const results = await response.json();
                    renderMemories(results.results);
                } catch (error) {
                    console.error('Search failed:', error);
                }
            }

            function connectStream() {
                const eventSource = new EventSource('/api/stream');
                eventSource.addEventListener('message', () => { loadStats(); loadMemories(); });
                eventSource.onerror = () => {
                    eventSource.close();
                    setTimeout(connectStream, 5000);
                };
            }

            loadStats();
            loadMemories();
            connectStream();
            setInterval(loadStats, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn

    print("Starting Enhanced Cognee Dashboard API...")
    print("Built-in view:        http://localhost:8000")
    print("API documentation:    http://localhost:8000/docs")
    print("Full dashboard (run separately): http://localhost:9050")

    uvicorn.run(app, host="0.0.0.0", port=8000)
