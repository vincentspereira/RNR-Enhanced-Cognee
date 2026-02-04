#!/usr/bin/env python3
"""
Enhanced Cognee MCP Server
Integrates with enterprise-grade memory stack: PostgreSQL+pgVector, Qdrant, Neo4j, Redis
Provides DYNAMIC and CONFIGURABLE memory architecture (not hardcoded to specific categories)
"""

import os
import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
import qdrant_client
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from neo4j import GraphDatabase, Driver
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
class EnhancedConfig:
    def __init__(self):
        self.enhanced_mode = os.getenv("ENHANCED_COGNEE_MODE", "false").lower() == "true"

        # Enhanced Stack Configuration with Enhanced ports
        self.postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "25432"))  # Enhanced port
        self.postgres_db = os.getenv("POSTGRES_DB", "cognee_db")
        self.postgres_user = os.getenv("POSTGRES_USER", "cognee_user")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "cognee_password")

        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "26333"))  # Enhanced port
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.qdrant_collection_prefix = os.getenv("QDRANT_COLLECTION_PREFIX", "cognee_")

        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:27687")  # Enhanced port
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "cognee_password")
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

        # Fallback to legacy environment variables for backward compatibility
        if os.getenv("ATS_MEMORY_PREFIX"):
            return {
                "ATS": os.getenv("ATS_MEMORY_PREFIX", "ats_"),
                "OMA": os.getenv("OMA_MEMORY_PREFIX", "oma_"),
                "SMC": os.getenv("SMC_MEMORY_PREFIX", "smc_"),
            }

        # Default to no prefixes (simple mode)
        logger.info("Using default category configuration (no custom prefixes)")
        return {}

config = EnhancedConfig()

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

class EnhancedCogneeMCPServer:
    """Enhanced Cognee MCP Server with enterprise-grade memory stack integration"""

    def __init__(self):
        self.postgres_pool = None
        self.qdrant_client = None
        self.neo4j_driver = None
        self.redis_client = None
        self.app = FastAPI(title="Enhanced Cognee MCP Server")
        self.setup_routes()

    async def initialize(self):
        """Initialize all Enhanced stack connections"""
        if not config.enhanced_mode:
            logger.warning("Enhanced Cognee mode is not enabled")
            return

        logger.info("Initializing Enhanced Cognee MCP Server...")

        await self._init_postgresql()
        await self._init_qdrant()
        await self._init_neo4j()
        await self._init_redis()

        logger.info("Enhanced Cognee MCP Server initialized successfully")

    async def _init_postgresql(self):
        """Initialize PostgreSQL connection (replaces SQLite)"""
        try:
            self.postgres_pool = await asyncpg.create_pool(
                host=config.postgres_host,
                port=config.postgres_port,
                database=config.postgres_db,
                user=config.postgres_user,
                password=config.postgres_password,
                min_size=5,
                max_size=20
            )
            logger.info("PostgreSQL connection established")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def _init_qdrant(self):
        """Initialize Qdrant client (replaces LanceDB)"""
        try:
            self.qdrant_client = QdrantClient(
                host=config.qdrant_host,
                port=config.qdrant_port,
                api_key=config.qdrant_api_key
            )

            # Test connection
            collections = self.qdrant_client.get_collections()
            logger.info(f"Qdrant connection established. Collections: {len(collections.collections)}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    async def _init_neo4j(self):
        """Initialize Neo4j driver (replaces Kuzu)"""
        try:
            self.neo4j_driver = GraphDatabase.driver(
                config.neo4j_uri,
                auth=(config.neo4j_user, config.neo4j_password)
            )

            # Test connection
            with self.neo4j_driver.session(database=config.neo4j_database) as session:
                result = session.run("RETURN 1")
                result.single()

            logger.info("Neo4j connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def _init_redis(self):
        """Initialize Redis client (new cache layer)"""
        try:
            self.redis_client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                password=config.redis_password,
                db=config.redis_db,
                decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
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
            entry.created_at = datetime.utcnow()

            # Store in PostgreSQL (metadata)
            async with self.postgres_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO shared_memory.documents
                    (id, title, content, agent_id, memory_category, tags, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, entry.id, f"Memory from {entry.agent_id}", entry.content,
                    entry.agent_id, entry.memory_category, entry.tags, entry.metadata, entry.created_at)

            # Store embedding in Qdrant (vector search)
            if entry.embedding:
                collection_name = self._get_collection_name(entry.memory_category, entry.agent_id)

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
        Search memory using Enhanced vector database with DYNAMIC categories

        Supports searching across dynamically configured categories
        """
        try:
            results = []

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
        """Get list of active agents from PostgreSQL"""
        try:
            async with self.postgres_pool.acquire() as conn:
                if memory_category:
                    query = """
                        SELECT DISTINCT agent_id
                        FROM shared_memory.documents
                        WHERE memory_category = $1
                    """
                    result = await conn.fetch(query, memory_category)
                else:
                    query = "SELECT DISTINCT agent_id FROM shared_memory.documents"
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
                created_at=datetime.utcnow().isoformat()
                )

                relation_id = str(uuid.uuid4())
                logger.info(f"Added knowledge relation {relation_id}")
                return relation_id

        except Exception as e:
            logger.error(f"Failed to add knowledge relation: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics from Enhanced stack"""
        try:
            stats = {}

            # PostgreSQL stats
            async with self.postgres_pool.acquire() as conn:
                result = await conn.fetch("""
                    SELECT
                        memory_category,
                        agent_id,
                        COUNT(*) as document_count,
                        MAX(created_at) as last_activity
                    FROM shared_memory.documents
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

        @self.app.get("/stats")
        async def get_stats_endpoint():
            """MCP Tool: Get memory statistics"""
            return await self.get_memory_stats()

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint with Enhanced stack status"""
            health = {
                "status": "healthy",
                "enhanced_mode": config.enhanced_mode,
                "timestamp": datetime.utcnow().isoformat(),
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

# Global server instance
server = EnhancedCogneeMCPServer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    await server.initialize()
    yield
    # Cleanup (if needed)

app = FastAPI(title="Enhanced Cognee MCP Server", lifespan=lifespan)
app.include_router(server.app.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)