#!/usr/bin/env python3
"""
Enhanced Cognee Agent Memory Integration Layer
Provides DYNAMIC and CONFIGURABLE memory integration for agents
Projects can define their own categories and agent registries
Integrates with Enhanced stack: PostgreSQL+pgVector, Qdrant, Neo4j, Redis
"""

import os
import asyncio
import json
import logging
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import asyncpg
import qdrant_client
from qdrant_client import QdrantClient, models
from neo4j import GraphDatabase, Driver
import redis.asyncio as redis
import numpy as np

# Import dynamic memory configuration system
from memory_config import (
    MemoryConfigManager,
    MemoryCategoryConfig,
    AgentConfig,
    get_config_manager,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory entries (common across all projects)"""
    FACTUAL = "factual"        # Factual information
    PROCEDURAL = "procedural"  # Procedures and workflows
    EPISODIC = "episodic"      # Event-based memories
    SEMANTIC = "semantic"      # Conceptual knowledge
    WORKING = "working"        # Temporary working memory

@dataclass
class MemoryEntry:
    """Standard memory entry structure"""
    id: str
    content: str
    agent_id: str
    category: str  # Category name (dynamically configured)
    memory_type: MemoryType
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = None
    tags: List[str] = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    importance: float = 1.0
    confidence: float = 1.0

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

@dataclass
class MemorySearchResult:
    """Memory search result"""
    id: str
    content: str
    agent_id: str
    category: str  # Category name (dynamically configured)
    similarity_score: float
    metadata: Dict[str, Any]
    created_at: datetime

class AgentMemoryIntegration:
    """
    Enhanced Cognee Memory Integration Layer with DYNAMIC configuration

    Projects can define their own categories and agents through:
    1. JSON config file (.enhanced-cognee-config.json)
    2. Environment variable (ENHANCED_COGNEE_CONFIG_PATH)
    3. Programmatic configuration
    """

    def __init__(self, config_manager: Optional[MemoryConfigManager] = None):
        """
        Initialize with dynamic configuration

        Parameters:
        -----------
        - config_manager: Optional custom config manager.
                         If None, uses the global default which loads from
                         .enhanced-cognee-config.json or environment variables.
        """
        # Use dynamic configuration system
        self.config_manager = config_manager or get_config_manager()

        # Enhanced stack connections
        self.postgres_pool = None
        self.qdrant_client = None
        self.neo4j_driver = None
        self.redis_client = None

        # Configuration
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "26333"))
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.qdrant_collection_prefix = os.getenv("QDRANT_COLLECTION_PREFIX", "cognee_")

        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:27687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "cognee_password")

        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "26379"))
        self.redis_password = os.getenv("REDIS_PASSWORD")

        self.postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "25432"))
        self.postgres_db = os.getenv("POSTGRES_DB", "cognee_db")
        self.postgres_user = os.getenv("POSTGRES_USER", "cognee_user")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "cognee_password")

        # Performance optimization
        self.cache_ttl = int(os.getenv("REDIS_CACHE_TTL", "3600"))
        self.batch_size = int(os.getenv("BATCH_SIZE", "50"))
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))

        # Log loaded configuration
        categories = self.config_manager.get_all_categories()
        agents = self.config_manager.get_all_agents()
        logger.info(f"Initialized with {len(categories)} categories and {len(agents)} agents")
        for cat_name, cat_config in categories.items():
            logger.info(f"  Category: {cat_name} (prefix: {cat_config.prefix})")

    def _initialize_agent_registry(self) -> Dict[str, Dict[str, Any]]:
        """
        DEPRECATED: Agent registry is now loaded from configuration

        This method is kept for backward compatibility but should not be used.
        Use the dynamic configuration system instead via .enhanced-cognee-config.json
        """
        logger.warning(
            "_initialize_agent_registry is deprecated. "
            "Use .enhanced-cognee-config.json for agent configuration."
        )
        return {}
        return {
            # ATS (Algorithmic Trading System) - ats_ prefix
            "algorithmic-trading-system": {
                "category": MemoryCategory.ATS,
                "prefix": "ats_",
                "description": "High-frequency trading and market analysis",
                "memory_types": [MemoryType.FACTUAL, MemoryType.PROCEDURAL, MemoryType.EPISODIC],
                "priority": 1,
                "data_retention_days": 30
            },
            "risk-management": {
                "category": MemoryCategory.ATS,
                "prefix": "ats_",
                "description": "Risk assessment and portfolio management",
                "memory_types": [MemoryType.FACTUAL, MemoryType.PROCEDURAL],
                "priority": 1,
                "data_retention_days": 90
            },
            "portfolio-optimizer": {
                "category": MemoryCategory.ATS,
                "prefix": "ats_",
                "description": "Portfolio optimization and rebalancing",
                "memory_types": [MemoryType.FACTUAL, MemoryType.SEMANTIC],
                "priority": 1,
                "data_retention_days": 60
            },
            "market-analyzer": {
                "category": MemoryCategory.ATS,
                "prefix": "ats_",
                "description": "Market trend analysis and prediction",
                "memory_types": [MemoryType.EPISODIC, MemoryType.SEMANTIC],
                "priority": 1,
                "data_retention_days": 45
            },
            "execution-engine": {
                "category": MemoryCategory.ATS,
                "prefix": "ats_",
                "description": "Trade execution and order management",
                "memory_types": [MemoryType.PROCEDURAL, MemoryType.WORKING],
                "priority": 1,
                "data_retention_days": 15
            },
            "signal-processor": {
                "category": MemoryCategory.ATS,
                "prefix": "ats_",
                "description": "Trading signal generation and processing",
                "memory_types": [MemoryType.EPISODIC, MemoryType.SEMANTIC],
                "priority": 1,
                "data_retention_days": 30
            },
            "compliance-monitor": {
                "category": MemoryCategory.ATS,
                "prefix": "ats_",
                "description": "Regulatory compliance and monitoring",
                "memory_types": [MemoryType.FACTUAL, MemoryType.PROCEDURAL],
                "priority": 1,
                "data_retention_days": 365
            },

            # OMA (Other Multi-Agent Agents) - oma_ prefix
            "code-reviewer": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Code review and quality analysis",
                "memory_types": [MemoryType.FACTUAL, MemoryType.PROCEDURAL],
                "priority": 2,
                "data_retention_days": 60
            },
            "code-analyzer": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Static code analysis and optimization",
                "memory_types": [MemoryType.FACTUAL, MemoryType.SEMANTIC],
                "priority": 2,
                "data_retention_days": 45
            },
            "bug-detector": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Automated bug detection and reporting",
                "memory_types": [MemoryType.EPISODIC, MemoryType.FACTUAL],
                "priority": 2,
                "data_retention_days": 90
            },
            "test-generator": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Automated test case generation",
                "memory_types": [MemoryType.PROCEDURAL, MemoryType.FACTUAL],
                "priority": 2,
                "data_retention_days": 30
            },
            "documentation-writer": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Documentation generation and maintenance",
                "memory_types": [MemoryType.PROCEDURAL, MemoryType.SEMANTIC],
                "priority": 2,
                "data_retention_days": 120
            },
            "security-auditor": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Security vulnerability assessment",
                "memory_types": [MemoryType.FACTUAL, MemoryType.PROCEDURAL],
                "priority": 2,
                "data_retention_days": 180
            },
            "performance-analyzer": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Performance profiling and optimization",
                "memory_types": [MemoryType.FACTUAL, MemoryType.EPISODIC],
                "priority": 2,
                "data_retention_days": 45
            },
            "log-analyzer": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Log analysis and anomaly detection",
                "memory_types": [MemoryType.EPISODIC, MemoryType.SEMANTIC],
                "priority": 2,
                "data_retention_days": 30
            },
            "dependency-manager": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Dependency management and updates",
                "memory_types": [MemoryType.FACTUAL, MemoryType.PROCEDURAL],
                "priority": 2,
                "data_retention_days": 60
            },
            "ci-cd-orchestrator": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "CI/CD pipeline orchestration",
                "memory_types": [MemoryType.PROCEDURAL, MemoryType.EPISODIC],
                "priority": 2,
                "data_retention_days": 45
            },

            # Enhanced SDLC Agents (Phase 1)
            "code_reviewer_enhanced": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Memory-enhanced code reviewer with learning capabilities",
                "memory_types": [MemoryType.PROCEDURAL, MemoryType.FACTUAL, MemoryType.EPISODIC],
                "priority": 2,
                "data_retention_days": 90
            },
            "test_engineer_enhanced": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Memory-enhanced test engineer with pattern learning",
                "memory_types": [MemoryType.PROCEDURAL, MemoryType.EPISODIC],
                "priority": 2,
                "data_retention_days": 60
            },
            "debug_specialist_enhanced": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Memory-enhanced debug specialist with bug pattern recognition",
                "memory_types": [MemoryType.EPISODIC, MemoryType.PROCEDURAL],
                "priority": 2,
                "data_retention_days": 90
            },
            "technical_writer_enhanced": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Memory-enhanced technical writer with template learning",
                "memory_types": [MemoryType.PROCEDURAL, MemoryType.SEMANTIC],
                "priority": 2,
                "data_retention_days": 120
            },
            "context_engineer_enhanced": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Memory-enhanced context engineer with relationship tracking",
                "memory_types": [MemoryType.SEMANTIC, MemoryType.FACTUAL],
                "priority": 2,
                "data_retention_days": 90
            },
            "code_implementer_enhanced": {
                "category": MemoryCategory.OMA,
                "prefix": "oma_",
                "description": "Memory-enhanced code implementer with pattern library",
                "memory_types": [MemoryType.PROCEDURAL, MemoryType.FACTUAL],
                "priority": 2,
                "data_retention_days": 60
            },

            # SMC (Shared Multi-Agent Components) - smc_ prefix
            "context-manager": {
                "category": MemoryCategory.SMC,
                "prefix": "smc_",
                "description": "Context management and sharing",
                "memory_types": [MemoryType.WORKING, MemoryType.PROCEDURAL],
                "priority": 3,
                "data_retention_days": 15
            },
            "knowledge-graph": {
                "category": MemoryCategory.SMC,
                "prefix": "smc_",
                "description": "Knowledge graph construction and management",
                "memory_types": [MemoryType.SEMANTIC, MemoryType.FACTUAL],
                "priority": 3,
                "data_retention_days": 180
            },
            "message-broker": {
                "category": MemoryCategory.SMC,
                "prefix": "smc_",
                "description": "Inter-agent communication broker",
                "memory_types": [MemoryType.PROCEDURAL, MemoryType.EPISODIC],
                "priority": 3,
                "data_retention_days": 7
            },
            "task-scheduler": {
                "category": MemoryCategory.SMC,
                "prefix": "smc_",
                "description": "Task scheduling and coordination",
                "memory_types": [MemoryType.PROCEDURAL, MemoryType.WORKING],
                "priority": 3,
                "data_retention_days": 14
            },
            "data-processor": {
                "category": MemoryCategory.SMC,
                "prefix": "smc_",
                "description": "Data processing and transformation",
                "memory_types": [MemoryType.PROCEDURAL, MemoryType.FACTUAL],
                "priority": 3,
                "data_retention_days": 30
            },
            "api-gateway": {
                "category": MemoryCategory.SMC,
                "prefix": "smc_",
                "description": "API management and routing",
                "memory_types": [MemoryType.PROCEDURAL, MemoryType.EPISODIC],
                "priority": 3,
                "data_retention_days": 14
            }
        }

    async def initialize(self):
        """Initialize connections to Enhanced stack components"""
        try:
            # Initialize PostgreSQL (Enhanced relational database)
            self.postgres_pool = await asyncpg.create_pool(
                host=self.postgres_host,
                port=self.postgres_port,
                database=self.postgres_db,
                user=self.postgres_user,
                password=self.postgres_password,
                min_size=5,
                max_size=20
            )
            logger.info("PostgreSQL connection established")

            # Initialize Qdrant (Enhanced vector database)
            self.qdrant_client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port,
                api_key=self.qdrant_api_key,
                prefer_grpc=False,
                check_compatibility=False  # Suppress version compatibility warning
            )

            # Test Qdrant connection
            collections = self.qdrant_client.get_collections()
            logger.info(f"Qdrant connection established. Collections: {len(collections.collections)}")

            # Initialize Neo4j (Enhanced graph database)
            self.neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )

            # Test Neo4j connection
            with self.neo4j_driver.session() as session:
                result = session.run("RETURN 1")
                result.single()
            logger.info("Neo4j connection established")

            # Initialize Redis (Cache layer)
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                decode_responses=True
            )

            # Test Redis connection
            await self.redis_client.ping()
            logger.info("Redis connection established")

            # Initialize agent collections in Qdrant
            await self._initialize_qdrant_collections()

        except Exception as e:
            logger.error(f"Failed to initialize Enhanced stack connections: {e}")
            raise

    async def _initialize_qdrant_collections(self):
        """Initialize Qdrant collections for each configured category"""
        categories = self.config_manager.get_all_categories()

        for category_name, category_config in categories.items():
            collection_name = f"{self.qdrant_collection_prefix}{category_config.prefix}memory"

            try:
                # Check if collection exists
                self.qdrant_client.get_collection(collection_name)
                logger.info(f"Qdrant collection {collection_name} already exists")
            except:
                # Create collection
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE)
                )
                logger.info(f"Created Qdrant collection: {collection_name}")

    async def add_memory(
        self,
        agent_id: str,
        content: str,
        memory_type: MemoryType,
        category_name: Optional[str] = None,
        metadata: Dict[str, Any] = None,
        embedding: List[float] = None,
        tags: List[str] = None,
        expires_at: datetime = None
    ) -> str:
        """
        Add memory entry for specific agent with Enhanced stack integration

        Parameters:
        -----------
        - agent_id: Agent identifier (must be registered in config)
        - content: Memory content
        - memory_type: Type of memory (factual, procedural, etc.)
        - category_name: Optional category override (defaults to agent's configured category)
        - metadata: Optional metadata dictionary
        - embedding: Optional pre-computed embedding
        - tags: Optional tags
        - expires_at: Optional expiration time
        """

        # Validate agent exists in dynamic configuration
        agent_config = self.config_manager.get_agent_config(agent_id)
        if not agent_config:
            raise ValueError(f"Unknown agent: {agent_id}. "
                           f"Please register agents in .enhanced-cognee-config.json")

        # Get category (use override if provided, otherwise use agent's category)
        if category_name:
            category_config = self.config_manager.get_category(category_name)
            if not category_config:
                raise ValueError(f"Unknown category: {category_name}")
        else:
            category_name = agent_config.category
            category_config = self.config_manager.get_category(category_name)

        if not category_config:
            raise ValueError(f"Category '{category_name}' not found in configuration")

        # Generate memory entry
        memory_id = str(uuid.uuid4())

        # Create memory entry object (using category name string instead of Enum)
        memory_entry = MemoryEntry(
            id=memory_id,
            content=content,
            agent_id=agent_id,
            category=category_name,  # Store as string (category name)
            memory_type=memory_type,
            embedding=embedding,
            metadata=metadata or {},
            tags=tags or [],
            expires_at=expires_at,
            importance=metadata.get("importance", 1.0) if metadata else 1.0,
            confidence=metadata.get("confidence", 1.0) if metadata else 1.0
        )

        try:
            # Store in PostgreSQL (metadata and structured data)
            await self._store_postgresql_memory(memory_entry)

            # Store embedding in Qdrant (vector search)
            if embedding:
                await self._store_qdrant_memory(memory_entry)

            # Cache in Redis for fast access
            await self._cache_memory(memory_entry)

            # Create knowledge graph relations if needed
            if memory_type in [MemoryType.SEMANTIC, MemoryType.FACTUAL]:
                await self._create_knowledge_relations(memory_entry)

            logger.info(f"Added memory entry {memory_id} for agent {agent_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to add memory entry {memory_id}: {e}")
            raise

    async def _store_postgresql_memory(self, memory_entry: MemoryEntry):
        """Store memory entry in PostgreSQL"""
        async with self.postgres_pool.acquire() as conn:
            # Store in main documents table (without expires_at if column doesn't exist)
            await conn.execute("""
                INSERT INTO shared_memory.documents
                (id, title, content, agent_id, memory_category, tags, metadata,
                 created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """,
                memory_entry.id,
                f"{memory_entry.memory_type.value} memory from {memory_entry.agent_id}",
                memory_entry.content,
                memory_entry.agent_id,
                memory_entry.category,  # Use category name string directly
                memory_entry.tags,
                json.dumps(memory_entry.metadata),  # Convert dict to JSON string
                memory_entry.created_at
            )

            # Store embeddings in specialized table
            if memory_entry.embedding:
                await conn.execute("""
                    INSERT INTO shared_memory.embeddings
                    (id, document_id, content, embedding, agent_id, memory_category, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (id) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    memory_entry.id,
                    memory_entry.id,
                    memory_entry.content,
                    memory_entry.embedding,
                    memory_entry.agent_id,
                    memory_entry.category,  # Use category name string directly
                    memory_entry.created_at
                )

    async def _store_qdrant_memory(self, memory_entry: MemoryEntry):
        """Store memory entry embedding in Qdrant"""
        # Get category configuration
        category_config = self.config_manager.get_category(memory_entry.category)
        if not category_config:
            logger.warning(f"Category '{memory_entry.category}' not found, using default prefix")
            category_prefix = f"{memory_entry.category}_"
        else:
            category_prefix = category_config.prefix

        collection_name = f"{self.qdrant_collection_prefix}{category_prefix}memory"

        # Create point for Qdrant
        point = models.PointStruct(
            id=memory_entry.id,
            vector=memory_entry.embedding,
            payload={
                "content": memory_entry.content,
                "agent_id": memory_entry.agent_id,
                "category_name": memory_entry.category,  # Store category name
                "memory_type": memory_entry.memory_type.value,
                "tags": memory_entry.tags,
                "importance": memory_entry.importance,
                "confidence": memory_entry.confidence,
                "created_at": memory_entry.created_at.isoformat()
            }
        )

        # Store in Qdrant
        self.qdrant_client.upsert(
            collection_name=collection_name,
            points=[point]
        )

    async def _cache_memory(self, memory_entry: MemoryEntry):
        """Cache memory entry in Redis"""
        cache_key = f"memory:{memory_entry.agent_id}:{memory_entry.id}"
        cache_data = {
            "id": memory_entry.id,
            "content": memory_entry.content,
            "category": memory_entry.category,  # Use category name directly
            "memory_type": memory_entry.memory_type.value,
            "tags": memory_entry.tags,
            "created_at": memory_entry.created_at.isoformat()
        }

        await self.redis_client.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(cache_data)
        )

    async def _create_knowledge_relations(self, memory_entry: MemoryEntry):
        """Create knowledge graph relations for semantic/factual memories"""
        # Extract entities and relationships (simplified)
        entities = self._extract_entities(memory_entry.content)

        if len(entities) > 1:
            with self.neo4j_driver.session() as session:
                # Create entities if they don't exist
                for entity in entities:
                    session.run("""
                        MERGE (e:Entity {name: $name})
                        SET e.category = $category,
                            e.agent_id = $agent_id,
                            e.last_seen = $timestamp
                    """,
                    name=entity,
                    category=memory_entry.category,  # Use category name directly
                    agent_id=memory_entry.agent_id,
                    timestamp=datetime.now(timezone.utc).isoformat()
                    )

                # Create relationships between entities
                for i in range(len(entities) - 1):
                    session.run("""
                        MATCH (e1:Entity {name: $name1}), (e2:Entity {name: $name2})
                        MERGE (e1)-[r:RELATED_TO]->(e2)
                        SET r.agent_id = $agent_id,
                            r.memory_type = $memory_type,
                            r.confidence = $confidence,
                            r.created_at = $timestamp
                    """,
                    name1=entities[i],
                    name2=entities[i + 1],
                    agent_id=memory_entry.agent_id,
                    memory_type=memory_entry.memory_type.value,
                    confidence=memory_entry.confidence,
                    timestamp=datetime.now(timezone.utc).isoformat()
                    )

    def _extract_entities(self, text: str) -> List[str]:
        """Simple entity extraction (could be enhanced with NLP)"""
        # Simple keyword extraction for demo
        words = text.lower().split()
        entities = []

        # Look for capitalized words (simple approach)
        for word in words:
            if len(word) > 3 and word[0].isupper():
                entities.append(word.lower())

        return list(set(entities))

    async def search_memory(
        self,
        agent_id: str = None,
        query: str = None,
        embedding: List[float] = None,
        memory_type: MemoryType = None,
        category_name: str = None,
        limit: int = 10,
        similarity_threshold: float = None
    ) -> List[MemorySearchResult]:
        """
        Search memory with enhanced stack capabilities

        Parameters:
        -----------
        - agent_id: Optional agent ID to filter by
        - query: Optional text query
        - embedding: Optional vector embedding for semantic search
        - memory_type: Optional memory type filter
        - category_name: Optional category name filter
        - limit: Maximum results to return
        - similarity_threshold: Optional similarity threshold for vector search
        """

        results = []
        qdrant_results = []  # Initialize to prevent UnboundLocalError

        # Search in PostgreSQL for exact matches and metadata
        postgres_results = await self._search_postgresql_memory(
            agent_id, query, memory_type, category_name, limit
        )

        # Search in Qdrant for semantic similarity
        if embedding:
            qdrant_results = await self._search_qdrant_memory(
                embedding, category_name, limit, similarity_threshold
            )
            results.extend(qdrant_results)

        # Merge and deduplicate results
        seen_ids = set()
        final_results = []

        # Add PostgreSQL results first
        for result in postgres_results:
            if result['id'] not in seen_ids:
                final_results.append(MemorySearchResult(
                    id=result['id'],
                    content=result['content'],
                    agent_id=result['agent_id'],
                    category=result['memory_category'],  # Use string directly
                    similarity_score=1.0,  # Exact match
                    metadata=result.get('metadata', {}),
                    created_at=result['created_at']
                ))
                seen_ids.add(result['id'])

        # Add Qdrant results with similarity scores
        for result in qdrant_results:
            if result['id'] not in seen_ids:
                final_results.append(MemorySearchResult(
                    id=result['id'],
                    content=result['content'],
                    agent_id=result['agent_id'],
                    category=result['memory_category'],  # Use string directly
                    similarity_score=result['similarity_score'],
                    metadata=result.get('metadata', {}),
                    created_at=result['created_at']
                ))
                seen_ids.add(result['id'])

        # Sort by similarity score and limit
        final_results.sort(key=lambda x: x.similarity_score, reverse=True)
        return final_results[:limit]

    async def _search_postgresql_memory(
        self,
        agent_id: str = None,
        query: str = None,
        memory_type: MemoryType = None,
        category_name: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search in PostgreSQL database"""
        async with self.postgres_pool.acquire() as conn:
            conditions = []
            params = []
            param_idx = 1

            if agent_id:
                conditions.append(f"agent_id = ${param_idx}")
                params.append(agent_id)
                param_idx += 1

            if query:
                conditions.append(f"content ILIKE ${param_idx}")
                params.append(f"%{query}%")
                param_idx += 1

            if memory_type:
                conditions.append(f"title LIKE ${param_idx}")
                params.append(f"%{memory_type.value}%")
                param_idx += 1

            if category_name:
                conditions.append(f"memory_category = ${param_idx}")
                params.append(category_name)
                param_idx += 1

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query_sql = f"""
                SELECT id, content, agent_id, memory_category, metadata, created_at
                FROM shared_memory.documents
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_idx}
            """
            params.append(limit)
            param_idx += 1

            rows = await conn.fetch(query_sql, *params)
            return [dict(row) for row in rows]

    async def _search_qdrant_memory(
        self,
        embedding: List[float],
        category_name: str = None,
        limit: int = 10,
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """Search in Qdrant vector database with dynamic categories"""
        if category_name:
            # Search specific category
            category_config = self.config_manager.get_category(category_name)
            if category_config:
                collection_name = f"{self.qdrant_collection_prefix}{category_config.prefix}memory"
                collection_names = [collection_name]
            else:
                logger.warning(f"Category '{category_name}' not found, trying direct lookup")
                collection_name = f"{self.qdrant_collection_prefix}{category_name}_memory"
                collection_names = [collection_name]
        else:
            # Search all configured category collections
            categories = self.config_manager.get_all_categories()
            collection_names = [
                f"{self.qdrant_collection_prefix}{cat_config.prefix}memory"
                for cat_config in categories.values()
            ]

        all_results = []
        search_threshold = threshold or self.similarity_threshold

        for collection_name in collection_names:
            try:
                search_result = self.qdrant_client.search(
                    collection_name=collection_name,
                    query_vector=embedding,
                    limit=limit,
                    score_threshold=search_threshold
                )

                for hit in search_result:
                    all_results.append({
                        'id': hit.id,
                        'content': hit.payload['content'],
                        'agent_id': hit.payload['agent_id'],
                        'memory_category': hit.payload.get('category_name', 'unknown'),
                        'similarity_score': hit.score,
                        'metadata': {
                            'tags': hit.payload.get('tags', []),
                            'importance': hit.payload.get('importance', 1.0),
                            'confidence': hit.payload.get('confidence', 1.0)
                        },
                        'created_at': datetime.fromisoformat(hit.payload['created_at'])
                    })
            except Exception as e:
                logger.warning(f"Failed to search collection {collection_name}: {e}")
                continue

        return all_results

    async def get_agent_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get memory statistics for specific agent"""
        # Validate agent exists in dynamic configuration
        agent_config = self.config_manager.get_agent_config(agent_id)
        if not agent_config:
            raise ValueError(f"Unknown agent: {agent_id}. "
                           f"Please register agents in .enhanced-cognee-config.json")

        category_name = agent_config.category
        category_config = self.config_manager.get_category(category_name)

        stats = {
            "agent_id": agent_id,
            "agent_config": {
                "agent_id": agent_config.agent_id,
                "category": agent_config.category,
                "description": agent_config.description,
                "memory_types": agent_config.memory_types,
                "priority": agent_config.priority,
                "data_retention_days": agent_config.data_retention_days,
            },
            "memory_stats": {}
        }

        if category_config:
            stats["category_config"] = {
                "name": category_config.name,
                "description": category_config.description,
                "prefix": category_config.prefix,
                "retention_days": category_config.retention_days,
                "priority": category_config.priority,
            }

        try:
            # Get PostgreSQL stats
            async with self.postgres_pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT
                        COUNT(*) as total_memories,
                        COUNT(DISTINCT memory_type) as memory_types,
                        MIN(created_at) as first_memory,
                        MAX(created_at) as last_memory
                    FROM shared_memory.documents
                    WHERE agent_id = $1
                """, agent_id)

                stats["memory_stats"]["postgresql"] = dict(result) if result else {}

            # Get Qdrant stats
            if category_config:
                collection_name = f"{self.qdrant_collection_prefix}{category_config.prefix}memory"
            else:
                collection_name = f"{self.qdrant_collection_prefix}{category_name}_memory"

            try:
                collection_info = self.qdrant_client.get_collection(collection_name)
                points_count = self.qdrant_client.count(collection_name).count

                stats["memory_stats"]["qdrant"] = {
                    "collection": collection_name,
                    "points_count": points_count,
                    "vector_count": collection_info.config.params.vectors.size
                }
            except:
                stats["memory_stats"]["qdrant"] = {"error": "Collection not found"}

            # Get Redis cache stats
            cache_pattern = f"memory:{agent_id}:*"
            cache_keys = await self.redis_client.keys(cache_pattern)
            stats["memory_stats"]["redis"] = {
                "cached_memories": len(cache_keys)
            }

        except Exception as e:
            logger.error(f"Failed to get memory stats for agent {agent_id}: {e}")
            stats["error"] = str(e)

        return stats

    async def cleanup_expired_memory(self) -> int:
        """Clean up expired memory entries"""
        cleanup_count = 0

        try:
            # Clean up PostgreSQL expired entries
            async with self.postgres_pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM shared_memory.documents
                    WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
                    RETURNING id
                """)
                cleanup_count += len(result)

            # Clean up Redis expired keys
            keys = await self.redis_client.keys("memory:*")
            for key in keys:
                ttl = await self.redis_client.ttl(key)
                if ttl == -1:  # No expiration set, skip
                    continue
                # Key with expiration is handled automatically by Redis

            logger.info(f"Cleaned up {cleanup_count} expired memory entries")
            return cleanup_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired memory: {e}")
            return 0

    async def get_all_agents_info(self) -> Dict[str, Any]:
        """Get information about all configured agents"""
        agents = self.config_manager.get_all_agents()
        categories = self.config_manager.get_all_categories()

        # Group agents by category
        category_counts = {}
        for agent_config in agents.values():
            cat_name = agent_config.category
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

        return {
            "project_info": {
                "total_categories": len(categories),
                "total_agents": len(agents),
            },
            "categories": {
                name: {
                    "name": cat_config.name,
                    "description": cat_config.description,
                    "prefix": cat_config.prefix,
                    "agent_count": category_counts.get(name, 0),
                }
                for name, cat_config in categories.items()
            },
            "agents": {
                agent_id: {
                    "agent_id": agent_config.agent_id,
                    "category": agent_config.category,
                    "description": agent_config.description,
                    "memory_types": agent_config.memory_types,
                    "priority": agent_config.priority,
                    "data_retention_days": agent_config.data_retention_days,
                }
                for agent_id, agent_config in agents.items()
            }
        }

    async def close(self):
        """Close all connections"""
        if self.postgres_pool:
            await self.postgres_pool.close()

        if self.neo4j_driver:
            self.neo4j_driver.close()

        if self.redis_client:
            await self.redis_client.close()

        logger.info("Closed all Enhanced stack connections")

# Example usage and initialization
async def main():
    """
    Example usage of the Agent Memory Integration with DYNAMIC configuration

    This example shows how the system now uses dynamic configuration instead of
    hardcoded categories. Projects can define their own categories and agents.
    """
    integration = AgentMemoryIntegration()

    try:
        # Initialize the integration
        await integration.initialize()

        # Get all agents info (now dynamically loaded)
        agents_info = await integration.get_all_agents_info()
        print(f"\n=== Enhanced Cognee Memory Integration ===")
        print(f"Project: {agents_info['project_info']['total_categories']} categories, "
              f"{agents_info['project_info']['total_agents']} agents")

        # Show configured categories
        print("\nConfigured Categories:")
        for cat_name, cat_info in agents_info['categories'].items():
            print(f"  - {cat_name}: {cat_info['description']} "
                  f"(prefix: {cat_info['prefix']}, agents: {cat_info['agent_count']})")

        # Show configured agents
        print("\nConfigured Agents:")
        for agent_id, agent_info in agents_info['agents'].items():
            print(f"  - {agent_id}: {agent_info['description']} "
                  f"(category: {agent_info['category']})")

        # Example: Add memory for a configured agent
        # NOTE: Agent must be registered in .enhanced-cognee-config.json
        try:
            memory_id = await integration.add_memory(
                agent_id="algorithmic-trading-system",  # Must exist in config
                content="Market volatility increased by 15% in the last hour. Consider adjusting position sizes.",
                memory_type=MemoryType.FACTUAL,
                metadata={
                    "importance": 0.8,
                    "source": "market_data_feed",
                    "market_conditions": "high_volatility"
                },
                tags=["market", "volatility", "risk"],
                embedding=[0.1, 0.2, 0.3] * 341  # Example embedding
            )

            print(f"\n✅ Added memory: {memory_id}")

            # Search memory
            results = await integration.search_memory(
                agent_id="algorithmic-trading-system",
                query="volatility",
                limit=5
            )

            print(f"✅ Found {len(results)} matching memories")

            # Get agent stats
            stats = await integration.get_agent_memory_stats("algorithmic-trading-system")
            print(f"✅ Agent stats: {stats}")

        except ValueError as e:
            print(f"\n⚠️ {e}")
            print("To add memory for agents, create a .enhanced-cognee-config.json file")
            print("with your project's agents and categories.")

    except Exception as e:
        logger.error(f"Error in example usage: {e}")
    finally:
        await integration.close()


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════╗
║   Enhanced Cognee Agent Memory Integration - DYNAMIC CONFIGURATION   ║
╠════════════════════════════════════════════════════════════════════╣
║   Categories are now DYNAMIC and CONFIGURABLE per project!          ║
║   No more hardcoded ATS/OMA/SMC categories.                         ║
║                                                                     ║
║   Configure your project via:                                       ║
║   1. Create .enhanced-cognee-config.json in your project root      ║
║   2. Define your own categories and agents                         ║
║   3. Or use ENHANCED_COGNEE_CONFIG_PATH environment variable       ║
╚════════════════════════════════════════════════════════════════════╝
    """)
    asyncio.run(main())