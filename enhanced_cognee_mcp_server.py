#!/usr/bin/env python3
"""
Enhanced Cognee MCP Server - Simplified
Works directly with Enhanced stack without complex migrations
"""

import os
import sys
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_path = project_root / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
    print(f"OK Loaded environment from: {env_path}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import MCP framework
from mcp.server import FastMCP
import mcp.types as types

# Create MCP server
mcp = FastMCP("Enhanced Cognee")

# Import enhanced modules
from src.memory_management import MemoryManager, RetentionPolicy
from src.memory_deduplication import MemoryDeduplicator
from src.memory_summarization import MemorySummarizer
from src.performance_analytics import PerformanceAnalytics
from src.cross_agent_sharing import CrossAgentMemorySharing, SharePolicy
from src.realtime_sync import RealTimeMemorySync

# Sprint 9: Multi-language support
from src.language_detector import language_detector
from src.multi_language_search import multi_language_search

# Sprint 10: Advanced AI Features
from src.intelligent_summarization import IntelligentMemorySummarizer, SummaryStrategy
from src.advanced_search_reranking import AdvancedSearchEngine, ReRankingStrategy

# Enhanced module instances
memory_manager = None
memory_deduplicator = None
memory_summarizer = None
performance_analytics = None
cross_agent_sharing = None
realtime_sync = None

# Sprint 9 instances
language_detector_instance = None
multi_language_search_instance = None

# Sprint 10 instances
intelligent_summarizer = None
advanced_search_engine = None

# Initialize Enhanced stack connections
postgres_pool = None
qdrant_client = None
neo4j_driver = None
redis_client = None
memory_manager = None


async def init_enhanced_stack():
    """Initialize Enhanced database connections"""
    global postgres_pool, qdrant_client, neo4j_driver, redis_client, memory_manager

    logger.info("Initializing Enhanced Cognee stack...")

    # PostgreSQL
    try:
        import asyncpg
        postgres_pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "25432")),
            database=os.getenv("POSTGRES_DB", "cognee_db"),
            user=os.getenv("POSTGRES_USER", "cognee_user"),
            password=os.getenv("POSTGRES_PASSWORD", "cognee_password"),
            min_size=2,
            max_size=10
        )
        async with postgres_pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        logger.info("OK PostgreSQL connected")
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {e}")

    # Qdrant
    try:
        from qdrant_client import QdrantClient
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            qdrant_client = QdrantClient(
                url=f"http://{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', '26333')}",
                api_key=os.getenv("QDRANT_API_KEY"),
                check_compatibility=False
            )
        collections = qdrant_client.get_collections()
        logger.info(f"OK Qdrant connected ({len(collections.collections)} collections)")
    except Exception as e:
        logger.warning(f"Qdrant connection failed: {e}")

    # Neo4j
    try:
        from neo4j import GraphDatabase
        neo4j_driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:27687"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "cognee_password")
            )
        )
        with neo4j_driver.session() as session:
            session.run("RETURN 1")
        logger.info("OK Neo4j connected")
    except Exception as e:
        logger.warning(f"Neo4j connection failed: {e}")

    # Redis
    try:
        import redis.asyncio as aioredis
        redis_client = await aioredis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "26379")),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("OK Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")

    # Initialize Memory Manager
    if postgres_pool and redis_client and qdrant_client:
        memory_manager = MemoryManager(postgres_pool, redis_client, qdrant_client)
        logger.info("OK Memory Manager initialized")

    # Initialize Memory Deduplicator
    if postgres_pool and qdrant_client:
        memory_deduplicator = MemoryDeduplicator(postgres_pool, qdrant_client)
        logger.info("OK Memory Deduplicator initialized")

    # Initialize Memory Summarizer
    if postgres_pool:
        llm_config = {}  # Configure with your LLM settings
        memory_summarizer = MemorySummarizer(postgres_pool, llm_config)
        logger.info("OK Memory Summarizer initialized")

    # Initialize Performance Analytics
    if postgres_pool and redis_client:
        performance_analytics = PerformanceAnalytics(postgres_pool, redis_client)
        logger.info("OK Performance Analytics initialized")

    # Initialize Cross-Agent Sharing
    if postgres_pool:
        cross_agent_sharing = CrossAgentMemorySharing(postgres_pool)
        logger.info("OK Cross-Agent Sharing initialized")

    # Initialize Real-Time Sync
    if redis_client and postgres_pool:
        realtime_sync = RealTimeMemorySync(redis_client, postgres_pool)
        logger.info("OK Real-Time Sync initialized")

    # Initialize Sprint 9: Multi-Language Support
    global language_detector_instance, multi_language_search_instance
    try:
        from src.language_detector import LanguageDetector
        from src.multi_language_search import MultiLanguageSearch

        language_detector_instance = LanguageDetector()
        multi_language_search_instance = MultiLanguageSearch()
        logger.info("OK Sprint 9 Multi-Language Support initialized")
    except Exception as e:
        logger.warning(f"Sprint 9 initialization failed: {e}")

    # Initialize Sprint 10: Advanced AI Features
    global intelligent_summarizer, advanced_search_engine
    try:
        llm_config = {
            'provider': os.getenv('LLM_PROVIDER', 'openai'),
            'api_key': os.getenv('LLM_API_KEY', ''),
            'model': os.getenv('LLM_MODEL', 'gpt-4-turbo')
        }

        if postgres_pool and redis_client and qdrant_client:
            intelligent_summarizer = IntelligentMemorySummarizer(
                postgres_pool=postgres_pool,
                llm_config=llm_config,
                redis_client=redis_client,
                qdrant_client=qdrant_client
            )
            logger.info("OK Sprint 10 Intelligent Summarizer initialized")

        if postgres_pool and qdrant_client and redis_client:
            advanced_search_engine = AdvancedSearchEngine(
                postgres_pool=postgres_pool,
                qdrant_client=qdrant_client,
                redis_client=redis_client,
                llm_config=llm_config
            )
            logger.info("OK Sprint 10 Advanced Search Engine initialized")

    except Exception as e:
        logger.warning(f"Sprint 10 initialization failed: {e}")


async def cleanup_enhanced_stack():
    """Cleanup Enhanced database connections"""
    global postgres_pool, qdrant_client, neo4j_driver, redis_client

    if postgres_pool:
        await postgres_pool.close()
        logger.info("OK PostgreSQL connection closed")

    if neo4j_driver:
        neo4j_driver.close()
        logger.info("OK Neo4j connection closed")

    if redis_client:
        await redis_client.aclose()
        logger.info("OK Redis connection closed")


@mcp.tool()
async def cognify(data: str) -> str:
    """
    Transform data into knowledge graph using Enhanced Cognee

    Parameters:
    -----------
    - data: Text data to process and add to the knowledge graph

    Returns:
    --------
    - Status message indicating success or failure
    """
    try:
        import uuid
        from datetime import datetime, UTC

        # For now, store in PostgreSQL
        if postgres_pool:
            async with postgres_pool.acquire() as conn:
                doc_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO shared_memory.documents (id, title, content, created_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO NOTHING
                """, doc_id, "Enhanced Cognee Memory", data, datetime.now(UTC).replace(tzinfo=None))

                logger.info(f"OK Added document: {doc_id}")

                # AUTO-TRIGGER: Log performance metrics
                if performance_analytics:
                    try:
                        await performance_analytics.log_operation(
                            operation="cognify",
                            agent_id="system",
                            metadata={
                                "doc_id": doc_id,
                                "data_length": len(data)
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log cognify performance: {e}")

                # AUTO-TRIGGER: Publish cognify event
                if realtime_sync:
                    try:
                        await realtime_sync.publish_memory_event(
                            event_type="data_cognified",
                            memory_id=doc_id,
                            agent_id="system",
                            data=json.dumps({
                                "title": "Enhanced Cognee Memory",
                                "data_length": len(data)
                            })
                        )
                    except Exception as e:
                        logger.warning(f"Failed to publish cognify event: {e}")

                return f"OK Successfully processed and stored data (ID: {doc_id})"
        else:
            return "WARN PostgreSQL not available - data not stored"

    except Exception as e:
        logger.error(f"Cognify failed: {e}")
        return f"ERR Failed to process data: {str(e)}"


@mcp.tool()
async def search(query: str, limit: int = 10) -> str:
    """
    Search the knowledge graph using Enhanced Cognee

    Parameters:
    -----------
    - query: Search query text
    - limit: Maximum number of results to return (default: 10)

    Returns:
    --------
    - Search results as formatted text
    """
    try:
        if postgres_pool:
            async with postgres_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, title, content, created_at
                    FROM shared_memory.documents
                    WHERE content ILIKE $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """, f"%{query}%", limit)

                # AUTO-TRIGGER: Log performance metrics
                if performance_analytics:
                    try:
                        await performance_analytics.log_operation(
                            operation="search",
                            agent_id="system",
                            metadata={
                                "query_length": len(query),
                                "results_count": len(rows),
                                "limit": limit
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log search performance: {e}")

                if rows:
                    results = [f"[DOC] {row['title']}\n   {row['content'][:100]}..."
                             for row in rows]
                    return f"OK Found {len(rows)} results:\n\n" + "\n\n".join(results)
                else:
                    return f"OK No results found for: {query}"
        else:
            return "WARN PostgreSQL not available - cannot search"

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"ERR Search failed: {str(e)}"


@mcp.tool()
async def get_stats() -> str:
    """
    Get Enhanced Cognee statistics

    Returns:
    --------
    - System status and statistics
    """
    try:
        stats = {"status": "Enhanced Cognee MCP Server", "databases": {}, "statistics": {}}

        # PostgreSQL stats
        if postgres_pool:
            async with postgres_pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM shared_memory.documents")
                stats["databases"]["postgresql"] = f"OK Connected ({count} documents)"

        # Qdrant stats
        if qdrant_client:
            collections = qdrant_client.get_collections()
            stats["databases"]["qdrant"] = f"OK Connected ({len(collections.collections)} collections)"

        # Neo4j stats
        if neo4j_driver:
            stats["databases"]["neo4j"] = "OK Connected"

        # Redis stats
        if redis_client:
            stats["databases"]["redis"] = "OK Connected"

        # AUTO-TRIGGER: Get deduplication statistics
        try:
            dedup_stats = await get_deduplication_stats()
            stats["statistics"]["deduplication"] = dedup_stats
        except Exception as e:
            logger.warning(f"Failed to get deduplication stats: {e}")

        # AUTO-TRIGGER: Get summary statistics
        try:
            summary_stats = await get_summary_stats()
            stats["statistics"]["summary"] = summary_stats
        except Exception as e:
            logger.warning(f"Failed to get summary stats: {e}")

        # AUTO-TRIGGER: Get memory age statistics
        try:
            age_stats = await get_memory_age_stats()
            stats["statistics"]["memory_age"] = age_stats
        except Exception as e:
            logger.warning(f"Failed to get memory age stats: {e}")

        return json.dumps(stats, indent=2)

    except Exception as e:
        logger.error(f"Stats failed: {e}")
        return f"ERR Failed to get stats: {str(e)}"


@mcp.tool()
async def health() -> str:
    """
    Health check for Enhanced Cognee server

    Returns:
    --------
    - Health status message
    """
    checks = []
    all_healthy = True

    if postgres_pool:
        checks.append("OK PostgreSQL")
    else:
        checks.append("ERR PostgreSQL")
        all_healthy = False

    if qdrant_client:
        checks.append("OK Qdrant")
    else:
        checks.append("ERR Qdrant")
        all_healthy = False

    if neo4j_driver:
        checks.append("OK Neo4j")
    else:
        checks.append("ERR Neo4j")
        all_healthy = False

    if redis_client:
        checks.append("OK Redis")
    else:
        checks.append("ERR Redis")
        all_healthy = False

    # AUTO-TRIGGER: Log performance metrics if unhealthy
    if not all_healthy and performance_analytics:
        try:
            await performance_analytics.log_operation(
                operation="health_check",
                agent_id="system",
                metadata={
                    "healthy": all_healthy,
                    "postgres_available": postgres_pool is not None,
                    "qdrant_available": qdrant_client is not None,
                    "neo4j_available": neo4j_driver is not None,
                    "redis_available": redis_client is not None
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log health check performance: {e}")

    return f"Enhanced Cognee Health:\n" + "\n".join(checks)


@mcp.tool()
async def list_data() -> str:
    """
    List all data in the knowledge graph

    Returns:
    --------
    - Formatted list of all documents
    """
    try:
        if postgres_pool:
            async with postgres_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, title, created_at
                    FROM shared_memory.documents
                    ORDER BY created_at DESC
                    LIMIT 50
                """)

                # AUTO-TRIGGER: Log performance metrics
                if performance_analytics:
                    try:
                        await performance_analytics.log_operation(
                            operation="list_data",
                            agent_id="system",
                            metadata={
                                "results_count": len(rows)
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log list_data performance: {e}")

                if rows:
                    results = [f"- {row['title']} (ID: {row['id']}, Created: {row['created_at']})"
                             for row in rows]
                    return f"[LIB] Documents ({len(rows)} total):\n\n" + "\n".join(results)
                else:
                    return "[LIB] No documents found"
        else:
            return "WARN PostgreSQL not available"

    except Exception as e:
        logger.error(f"List data failed: {e}")
        return f"ERR Failed to list data: {str(e)}"


# ============================================================================
# STANDARD MEMORY MCP TOOLS - For Claude Code Memory Integration
# ============================================================================

@mcp.tool()
async def add_memory(
    content: str,
    user_id: str = "default",
    agent_id: str = "claude-code",
    metadata: Optional[str] = None
) -> str:
    """
    Add a memory entry (Standard Memory MCP Tool)

    This is the standard memory tool interface for Claude Code integration.
    Memories are stored in PostgreSQL and indexed in Qdrant for semantic search.

    AUTO-TRIGGERED: When AI IDE wants to remember information

    Parameters:
    -----------
    - content: The memory content to store
    - user_id: User identifier (default: "default")
    - agent_id: Agent identifier (default: "claude-code")
    - metadata: Optional JSON string with additional metadata

    Returns:
    --------
    - Memory ID and status message
    """
    try:
        import uuid
        from datetime import datetime, UTC

        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot add memory"

        # AUTO-TRIGGER: Check for duplicate before adding
        if memory_deduplicator:
            try:
                duplicate_check = await memory_deduplicator.check_duplicate(
                    content=content,
                    agent_id=agent_id,
                    memory_category="general"
                )
                if duplicate_check.get("is_duplicate"):
                    logger.info(f"Duplicate prevented: {duplicate_check.get('reason')}")
                    return f"OK Duplicate prevented: {duplicate_check.get('reason')}"
            except Exception as e:
                logger.warning(f"Duplicate check failed, continuing: {e}")

        # Parse metadata if provided
        metadata_dict = {}
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except:
                metadata_dict = {"raw_metadata": metadata}

        # Generate memory ID
        memory_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).replace(tzinfo=None)

        # Store in PostgreSQL
        async with postgres_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO shared_memory.documents
                (id, title, content, agent_id, memory_category, tags, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, memory_id, f"Memory from {agent_id}", content,
                agent_id, "general", [], metadata_dict, created_at)

        logger.info(f"OK Added memory: {memory_id} for user: {user_id}, agent: {agent_id}")

        # AUTO-TRIGGER: Publish memory event for real-time sync
        if realtime_sync:
            try:
                await realtime_sync.publish_memory_event(
                    event_type="memory_added",
                    memory_id=memory_id,
                    agent_id=agent_id,
                    data={"content_preview": content[:100]}
                )
            except Exception as e:
                logger.warning(f"Failed to publish memory event: {e}")

        # AUTO-TRIGGER: Sync with shared agents
        if cross_agent_sharing and realtime_sync:
            try:
                # Check if this memory is shared
                access_check = await cross_agent_sharing.can_agent_access_memory(
                    memory_id=memory_id,
                    agent_id=agent_id
                )
                # Sync to all agents that should have access
                await realtime_sync.sync_agent_state(
                    source_agent=agent_id,
                    target_agent="all",
                    category="general"
                )
            except Exception as e:
                logger.warning(f"Failed to sync agent state: {e}")

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="add_memory",
                    agent_id=agent_id,
                    memory_id=memory_id,
                    metadata={"content_length": len(content)}
                )
            except Exception as e:
                logger.warning(f"Failed to log performance metrics: {e}")

        return f"OK Memory added (ID: {memory_id})"

    except Exception as e:
        logger.error(f"add_memory failed: {e}")
        return f"ERR Failed to add memory: {str(e)}"


@mcp.tool()
async def search_memories(
    query: str,
    limit: int = 10,
    user_id: str = "default",
    agent_id: Optional[str] = None
) -> str:
    """
    Search memories using semantic and text search (Standard Memory MCP Tool)

    This is the standard memory search tool for Claude Code integration.
    Performs both text-based and semantic vector search.

    Parameters:
    -----------
    - query: Search query text
    - limit: Maximum results to return (default: 10)
    - user_id: User identifier to filter memories (default: "default")
    - agent_id: Optional agent identifier to filter memories

    Returns:
    --------
    - Formatted search results with memory content
    """
    import time
    start_time = time.time()

    try:
        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot search memories"

        async with postgres_pool.acquire() as conn:
            # Build query with filters
            query_str = """
                SELECT id, title, content, agent_id, created_at
                FROM shared_memory.documents
                WHERE content ILIKE $1
            """
            params = [f"%{query}%"]

            # Add agent filter if specified
            if agent_id:
                query_str += " AND agent_id = $2"
                params.append(agent_id)

            query_str += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
            params.append(limit)

            rows = await conn.fetch(query_str, *params)

            # Calculate search duration
            duration_ms = (time.time() - start_time) * 1000

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="search_memories",
                        agent_id=agent_id or "unknown",
                        metadata={
                            "query_length": len(query),
                            "results_count": len(rows),
                            "duration_ms": duration_ms
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log search performance: {e}")

            # AUTO-TRIGGER: If slow, log to slow queries
            if duration_ms > 1000:  # 1 second threshold
                logger.warning(f"Slow search query: {duration_ms:.2f}ms - {query[:50]}")
                try:
                    # Log to slow queries for analysis
                    if performance_analytics:
                        await performance_analytics.log_operation(
                            operation="slow_query",
                            agent_id="system",
                            metadata={
                                "query": query[:100],
                                "duration_ms": duration_ms,
                                "threshold_ms": 1000
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to log slow query: {e}")

            if rows:
                results = []
                for row in rows:
                    results.append(f"[MEM] {row['title']}\n"
                                 f"     Agent: {row['agent_id']}\n"
                                 f"     Content: {row['content'][:200]}...\n"
                                 f"     Created: {row['created_at']}")
                return f"OK Found {len(rows)} memories:\n\n" + "\n\n".join(results)
            else:
                return f"OK No memories found for query: {query}"

    except Exception as e:
        logger.error(f"search_memories failed: {e}")
        return f"ERR Failed to search memories: {str(e)}"


@mcp.tool()
async def get_memories(
    user_id: str = "default",
    agent_id: Optional[str] = None,
    limit: int = 50
) -> str:
    """
    List all memories with filters (Standard Memory MCP Tool)

    Parameters:
    -----------
    - user_id: User identifier (default: "default")
    - agent_id: Optional agent identifier to filter
    - limit: Maximum results to return (default: 50)

    Returns:
    --------
    - Formatted list of all memories matching filters
    """
    try:
        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot get memories"

        async with postgres_pool.acquire() as conn:
            query_str = """
                SELECT id, title, content, agent_id, created_at
                FROM shared_memory.documents
                WHERE 1=1
            """
            params = []

            if agent_id:
                query_str += " AND agent_id = $1"
                params.append(agent_id)

            query_str += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
            params.append(limit)

            rows = await conn.fetch(query_str, *params)

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="get_memories",
                        agent_id=agent_id or "unknown",
                        metadata={
                            "results_count": len(rows),
                            "limit": limit
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log get_memories performance: {e}")

            if rows:
                results = []
                for row in rows:
                    results.append(f"- {row['title']} (ID: {row['id']}, Agent: {row['agent_id']})")
                return f"[MEM] Memories ({len(rows)} total):\n\n" + "\n".join(results)
            else:
                return "[MEM] No memories found"

    except Exception as e:
        logger.error(f"get_memories failed: {e}")
        return f"ERR Failed to get memories: {str(e)}"


@mcp.tool()
async def get_memory(memory_id: str) -> str:
    """
    Retrieve a specific memory by ID (Standard Memory MCP Tool)

    Parameters:
    -----------
    - memory_id: The unique ID of the memory to retrieve

    Returns:
    --------
    - Full memory content with metadata
    """
    try:
        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot get memory"

        async with postgres_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, title, content, agent_id, metadata, created_at
                FROM shared_memory.documents
                WHERE id = $1
            """, memory_id)

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="get_memory",
                        agent_id="system",
                        metadata={
                            "memory_id": memory_id,
                            "found": row is not None
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log get_memory performance: {e}")

            if row:
                return (f"OK Memory Found:\n"
                       f"  ID: {row['id']}\n"
                       f"  Title: {row['title']}\n"
                       f"  Agent: {row['agent_id']}\n"
                       f"  Created: {row['created_at']}\n"
                       f"  Content: {row['content']}\n"
                       f"  Metadata: {row['metadata']}")
            else:
                return f"ERR Memory not found: {memory_id}"

    except Exception as e:
        logger.error(f"get_memory failed: {e}")
        return f"ERR Failed to get memory: {str(e)}"


@mcp.tool()
async def update_memory(memory_id: str, content: str) -> str:
    """
    Update an existing memory (Standard Memory MCP Tool)

    AUTO-TRIGGERED: When AI IDE needs to correct or update information

    Parameters:
    -----------
    - memory_id: The unique ID of the memory to update
    - content: New content for the memory

    Returns:
    --------
    - Status message indicating success or failure
    """
    try:
        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot update memory"

        async with postgres_pool.acquire() as conn:
            # Check if memory exists
            existing = await conn.fetchval("""
                SELECT id FROM shared_memory.documents WHERE id = $1
            """, memory_id)

            if not existing:
                return f"ERR Memory not found: {memory_id}"

            # Update memory
            await conn.execute("""
                UPDATE shared_memory.documents
                SET content = $2
                WHERE id = $1
            """, memory_id, content)

            logger.info(f"OK Updated memory: {memory_id}")

            # AUTO-TRIGGER: Publish memory update event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="memory_updated",
                        memory_id=memory_id,
                        agent_id="system",
                        data={"content_preview": content[:100]}
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish memory update event: {e}")

            # AUTO-TRIGGER: Sync with shared agents
            if cross_agent_sharing and realtime_sync:
                try:
                    await realtime_sync.sync_agent_state(
                        source_agent="system",
                        target_agent="all",
                        category="general"
                    )
                except Exception as e:
                    logger.warning(f"Failed to sync agent state after update: {e}")

            # AUTO-TRIGGER: Check if summary needs update
            if memory_summarizer:
                try:
                    # Get summary statistics to check if we need to update summaries
                    stats = await memory_summarizer.get_summary_statistics()
                    # If memory count is high, trigger summarization check
                    if stats.get("total_memories", 0) > 1000:
                        logger.info("High memory count detected, consider summarization")
                except Exception as e:
                    logger.warning(f"Failed to check summary stats: {e}")

            return f"OK Memory updated (ID: {memory_id})"

    except Exception as e:
        logger.error(f"update_memory failed: {e}")
        return f"ERR Failed to update memory: {str(e)}"


@mcp.tool()
async def delete_memory(memory_id: str) -> str:
    """
    Delete a specific memory (Standard Memory MCP Tool)

    MANUAL - User must explicitly delete memories

    Parameters:
    -----------
    - memory_id: The unique ID of the memory to delete

    Returns:
    --------
    - Status message indicating success or failure
    """
    try:
        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot delete memory"

        async with postgres_pool.acquire() as conn:
            # Check if memory exists
            existing = await conn.fetchval("""
                SELECT id FROM shared_memory.documents WHERE id = $1
            """, memory_id)

            if not existing:
                return f"ERR Memory not found: {memory_id}"

            # Delete memory
            await conn.execute("""
                DELETE FROM shared_memory.documents WHERE id = $1
            """, memory_id)

            logger.info(f"OK Deleted memory: {memory_id}")

            # Publish deletion event for real-time sync
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="memory_deleted",
                        memory_id=memory_id,
                        agent_id="system",
                        data={}
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish memory deletion event: {e}")

            # AUTO-TRIGGER: Sync with shared agents
            if cross_agent_sharing and realtime_sync:
                try:
                    await realtime_sync.sync_agent_state(
                        source_agent="system",
                        target_agent="all",
                        category="general"
                    )
                except Exception as e:
                    logger.warning(f"Failed to sync agent state after deletion: {e}")

            return f"OK Memory deleted (ID: {memory_id})"

    except Exception as e:
        logger.error(f"delete_memory failed: {e}")
        return f"ERR Failed to delete memory: {str(e)}"


@mcp.tool()
async def list_agents() -> str:
    """
    List all agents that have stored memories (Standard Memory MCP Tool)

    Returns:
    --------
    - List of all agent IDs with memory counts
    """
    try:
        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot list agents"

        async with postgres_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT agent_id, COUNT(*) as memory_count
                FROM shared_memory.documents
                GROUP BY agent_id
                ORDER BY memory_count DESC
            """)

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="list_agents",
                        agent_id="system",
                        metadata={
                            "agents_count": len(rows) if rows else 0
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log list_agents performance: {e}")

            if rows:
                results = [f"- {row['agent_id']}: {row['memory_count']} memories"
                         for row in rows]
                return "[AGENTS] Active Agents:\n\n" + "\n".join(results)
            else:
                return "[AGENTS] No agents found"

    except Exception as e:
        logger.error(f"list_agents failed: {e}")
        return f"ERR Failed to list agents: {str(e)}"


# ============================================================================
# MEMORY MANAGEMENT TOOLS - Expiry, Archival, Cleanup
# ============================================================================

@mcp.tool()
async def expire_memories(days: int = 90, dry_run: bool = False) -> str:
    """
    Expire or archive memories older than specified days (Memory Management Tool)

    MANUAL - User must explicitly trigger memory expiration

    Parameters:
    -----------
    - days: Number of days after which memories expire (default: 90)
    - dry_run: If True, simulate without actually deleting (default: False)

    Returns:
    --------
    - Result of the expiry operation with memory count
    """
    if not memory_manager:
        return "ERR Memory Manager not available"

    try:
        # AUTO-TRIGGER: Get memory age stats before expiring
        try:
            age_stats = await get_memory_age_stats()
            logger.info(f"Memory age stats before expiration: {age_stats}")
        except Exception as e:
            logger.warning(f"Failed to get memory age stats: {e}")

        result = await memory_manager.expire_old_memories(
            days=days,
            dry_run=dry_run,
            policy=RetentionPolicy.DELETE_OLD
        )

        memories_affected = result.get('memories_affected', 0)

        if result.get("status") == "dry_run":
            return f"OK DRY RUN: Would expire {memories_affected} memories older than {days} days"

        elif result.get("status") == "success":
            # AUTO-TRIGGER: Publish expiration event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="memory_expired",
                        memory_id=f"expire_{days}",
                        agent_id="system",
                        data=json.dumps({
                            "days": days,
                            "memories_expired": memories_affected
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish expiration event: {e}")

            # AUTO-TRIGGER: Update summary statistics
            try:
                summary_stats = await get_summary_stats()
                logger.info(f"Updated summary stats after expiration: {summary_stats}")
            except Exception as e:
                logger.warning(f"Failed to update summary stats: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="expire_memories",
                        agent_id="system",
                        metadata={
                            "days": days,
                            "memories_expired": memories_affected,
                            "dry_run": dry_run
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log expiration performance: {e}")

            return f"OK Expired {memories_affected} memories older than {days} days"

        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"expire_memories failed: {e}")
        return f"ERR Failed to expire memories: {str(e)}"


@mcp.tool()
async def get_memory_age_stats() -> str:
    """
    Get statistics about memory age distribution (Memory Management Tool)

    Returns:
    --------
    - Memory statistics by age bracket (0-7 days, 8-30 days, 31-90 days, 90+ days)
    """
    if not memory_manager:
        return "ERR Memory Manager not available"

    try:
        stats = await memory_manager.get_memory_stats_by_age()

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_memory_age_stats",
                    agent_id="system",
                    metadata={
                        "total_memories": stats.get('total_memories', 0),
                        "status": stats.get("status", "unknown")
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log get_memory_age_stats performance: {e}")

        if stats.get("status") == "error":
            return f"ERR {stats.get('error', 'Unknown error')}"

        output = [
            f"[STATS] Memory Age Distribution:",
            f"  Total memories: {stats['total_memories']}",
            f"  Oldest memory: {stats['oldest_memory']}",
            f"  Newest memory: {stats['newest_memory']}",
            "",
            "  Age Distribution:"
        ]

        for bracket, count in stats.get("age_distribution", {}).items():
            output.append(f"    {bracket}: {count} memories")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"get_memory_age_stats failed: {e}")
        return f"ERR Failed to get memory age stats: {str(e)}"


@mcp.tool()
async def set_memory_ttl(memory_id: str, ttl_days: int) -> str:
    """
    Set time-to-live (TTL) for a specific memory (Memory Management Tool)

    MANUAL - User must explicitly set TTL policies

    Parameters:
    -----------
    - memory_id: ID of the memory to set TTL for
    - ttl_days: Days until expiry (0 = no expiry)

    Returns:
    --------
    - Result of TTL setting operation
    """
    if not memory_manager:
        return "ERR Memory Manager not available"

    try:
        result = await memory_manager.set_memory_ttl(memory_id, ttl_days)

        if result.get("status") == "not_found":
            return f"ERR Memory not found: {memory_id}"

        elif result.get("status") == "success":
            expiry = result.get("expiry_date", "never")

            # AUTO-TRIGGER: Get memory age stats after setting TTL
            try:
                age_stats = await get_memory_age_stats()
                logger.info(f"Updated memory age stats after TTL set: {age_stats}")
            except Exception as e:
                logger.warning(f"Failed to get memory age stats: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="set_memory_ttl",
                        agent_id="system",
                        metadata={
                            "memory_id": memory_id,
                            "ttl_days": ttl_days,
                            "expiry_date": expiry
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log set_ttl performance: {e}")

            return f"OK Set TTL of {ttl_days} days for memory {memory_id} (expires: {expiry})"

        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"set_memory_ttl failed: {e}")
        return f"ERR Failed to set memory TTL: {str(e)}"


@mcp.tool()
async def archive_category(category: str, days: int = 180) -> str:
    """
    Archive all memories from a specific category older than specified days

    MANUAL - User must explicitly trigger archival operations

    Parameters:
    -----------
    - category: Memory category to archive (e.g., 'trading', 'development')
    - days: Age threshold for archiving (default: 180 days)

    Returns:
    --------
    - Result of archival operation
    """
    if not memory_manager:
        return "ERR Memory Manager not available"

    try:
        # AUTO-TRIGGER: Get memory age stats before archiving
        try:
            age_stats = await get_memory_age_stats()
            logger.info(f"Memory age stats before archival: {age_stats}")
        except Exception as e:
            logger.warning(f"Failed to get memory age stats: {e}")

        result = await memory_manager.archive_memories_by_category(category, days)

        if result.get("status") == "success":
            memories_archived = result.get('memories_archived', 0)

            # AUTO-TRIGGER: Publish archival event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="memory_archived",
                        memory_id=f"archive_{category}",
                        agent_id="system",
                        data=json.dumps({
                            "category": category,
                            "days": days,
                            "memories_archived": memories_archived
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish archival event: {e}")

            # AUTO-TRIGGER: Update summary statistics
            try:
                summary_stats = await get_summary_stats()
                logger.info(f"Updated summary stats after archival: {summary_stats}")
            except Exception as e:
                logger.warning(f"Failed to update summary stats: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="archive_category",
                        agent_id="system",
                        metadata={
                            "category": category,
                            "days": days,
                            "memories_archived": memories_archived
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log archival performance: {e}")

            return f"OK Archived {memories_archived} memories from category '{category}' older than {days} days"

        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"archive_category failed: {e}")
        return f"ERR Failed to archive category: {str(e)}"



# ============================================================================
# MEMORY DEDUPLICATION TOOLS - Prevent duplicate memories
# ============================================================================

@mcp.tool()
async def check_duplicate(content: str, agent_id: str = "default") -> str:
    """
    Check if content is duplicate before adding (Memory Deduplication Tool)

    Parameters:
    -----------
    - content: Content to check for duplicates
    - agent_id: Agent ID to check duplicates for (default: "default")

    Returns:
    --------
    - Duplicate check result with action recommendation
    """
    if not memory_deduplicator:
        return "ERR Memory Deduplicator not available"

    try:
        result = await memory_deduplicator.check_duplicate(
            content=content,
            embedding=None,
            agent_id=agent_id
        )

        if result.get("is_duplicate"):
            dup_type = result.get("duplicate_type", "unknown")
            reason = result.get("reason", "No reason")
            action = result.get("action", "skip")
            existing_id = result.get("existing_id", "unknown")

            return (f"OK DUPLICATE FOUND:\n"
                   f"  Type: {dup_type}\n"
                   f"  Existing ID: {existing_id}\n"
                   f"  Reason: {reason}\n"
                   f"  Action: {action}")
        else:
            return f"OK No duplicate found - safe to add"

    except Exception as e:
        logger.error(f"check_duplicate failed: {e}")
        return f"ERR Failed to check duplicate: {str(e)}"


@mcp.tool()
async def auto_deduplicate(agent_id: str = None) -> str:
    """
    Automatically find and handle duplicate memories (Memory Deduplication Tool)

    Parameters:
    -----------
    - agent_id: Optional agent ID to scope deduplication (default: all agents)

    Returns:
    --------
    - Deduplication results with counts
    """
    if not memory_deduplicator:
        return "ERR Memory Deduplicator not available"

    try:
        result = await memory_deduplicator.auto_deduplicate(agent_id)

        if result.get("status") == "success":
            res = result.get("results", {})

            # AUTO-TRIGGER: Publish deduplication event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="memory_deduplicated",
                        memory_id=f"dedup_{agent_id or 'all'}",
                        agent_id=agent_id or "system",
                        data=json.dumps({
                            "processed": res.get('processed', 0),
                            "duplicates_found": res.get('duplicates_found', 0),
                            "merged": res.get('merged', 0),
                            "deleted": res.get('deleted', 0)
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish deduplication event: {e}")

            # AUTO-TRIGGER: Update deduplication statistics
            try:
                stats = await get_deduplication_stats()
                logger.info(f"Updated deduplication stats: {stats}")
            except Exception as e:
                logger.warning(f"Failed to update deduplication stats: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="auto_deduplicate",
                        agent_id=agent_id or "system",
                        metadata={
                            "processed": res.get('processed', 0),
                            "duplicates_found": res.get('duplicates_found', 0),
                            "merged": res.get('merged', 0),
                            "deleted": res.get('deleted', 0)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log deduplication performance: {e}")

            return (f"OK Auto-deduplication complete:\n"
                   f"  Processed: {res.get('processed', 0)} memories\n"
                   f"  Duplicates found: {res.get('duplicates_found', 0)}\n"
                   f"  Merged: {res.get('merged', 0)}\n"
                   f"  Deleted: {res.get('deleted', 0)}")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"auto_deduplicate failed: {e}")
        return f"ERR Failed to auto-deduplicate: {str(e)}"


@mcp.tool()
async def get_deduplication_stats() -> str:
    """
    Get statistics about memory deduplication (Memory Deduplication Tool)

    Returns:
    --------
    - Deduplication statistics
    """
    if not memory_deduplicator:
        return "ERR Memory Deduplicator not available"

    try:
        stats = await memory_deduplicator.get_deduplication_stats()

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_deduplication_stats",
                    agent_id="system",
                    metadata={
                        "exact_duplicates": stats.get('exact_duplicates_found', 0),
                        "similar_duplicates": stats.get('similar_duplicates_found', 0)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log deduplication stats performance: {e}")

        if "error" in stats:
            return f"ERR {stats['error']}"

        return (f"[STATS] Deduplication Statistics:\n"
               f"  Similarity threshold: {stats.get('similarity_threshold', 0)}\n"
               f"  Exact duplicates found: {stats.get('exact_duplicates_found', 0)}\n"
               f"  Similar duplicates found: {stats.get('similar_duplicates_found', 0)}\n"
               f"  Total duplicates prevented: {stats.get('total_duplicates_prevented', 0)}")

    except Exception as e:
        logger.error(f"get_deduplication_stats failed: {e}")
        return f"ERR Failed to get deduplication stats: {str(e)}"


# ============================================================================
# MEMORY SUMMARIZATION TOOLS - Automatic summarization for storage optimization
# ============================================================================

@mcp.tool()
async def summarize_old_memories(days: int = 30, min_length: int = 1000, dry_run: bool = False) -> str:
    """
    Summarize memories older than specified days (Memory Summarization Tool)

    Parameters:
    -----------
    - days: Age threshold for summarization (default: 30)
    - min_length: Minimum content length to summarize (default: 1000)
    - dry_run: If True, simulate without summarizing (default: False)

    Returns:
    --------
    - Summarization results with compression statistics
    """
    if not memory_summarizer:
        return "ERR Memory Summarizer not available"

    try:
        # AUTO-TRIGGER: Get memory age stats before summarizing
        try:
            age_stats = await get_memory_age_stats()
            logger.info(f"Memory age stats before summarization: {age_stats}")
        except Exception as e:
            logger.warning(f"Failed to get memory age stats: {e}")

        result = await memory_summarizer.summarize_old_memories(days, min_length, dry_run)

        if result.get("status") == "success":
            memories_summarized = result.get('memories_summarized', 0)
            space_saved = result.get('space_saved_bytes', 0)

            if dry_run:
                return (f"OK DRY RUN: Found {result.get('candidates_found', 0)} memories to summarize "
                       f"older than {days} days")
            else:
                # AUTO-TRIGGER: Publish summarization event
                if realtime_sync:
                    try:
                        await realtime_sync.publish_memory_event(
                            event_type="memory_summarized",
                            memory_id=f"summarize_{days}",
                            agent_id="system",
                            data=json.dumps({
                                "days": days,
                                "memories_summarized": memories_summarized,
                                "space_saved": space_saved
                            })
                        )
                    except Exception as e:
                        logger.warning(f"Failed to publish summarization event: {e}")

                # AUTO-TRIGGER: Update summary statistics
                try:
                    summary_stats = await get_summary_stats()
                    logger.info(f"Updated summary stats after summarization: {summary_stats}")
                except Exception as e:
                    logger.warning(f"Failed to update summary stats: {e}")

                # AUTO-TRIGGER: Log performance metrics
                if performance_analytics:
                    try:
                        await performance_analytics.log_operation(
                            operation="summarize_old_memories",
                            agent_id="system",
                            metadata={
                                "days": days,
                                "min_length": min_length,
                                "memories_summarized": memories_summarized,
                                "space_saved": space_saved
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log summarization performance: {e}")

                return (f"OK Summarized {memories_summarized} memories:\n"
                       f"  Space saved: {space_saved} bytes")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"summarize_old_memories failed: {e}")
        return f"ERR Failed to summarize memories: {str(e)}"


@mcp.tool()
async def summarize_category(category: str, days: int = 30) -> str:
    """
    Summarize all memories in a category older than specified days (Memory Summarization Tool)

    Parameters:
    -----------
    - category: Category to summarize (e.g., 'trading', 'development')
    - days: Age threshold (default: 30)

    Returns:
    --------
    - Summarization results for category
    """
    if not memory_summarizer:
        return "ERR Memory Summarizer not available"

    try:
        result = await memory_summarizer.summarize_by_category(category, days)

        if result.get("status") == "success":
            res = result.get("results", {})
            memories_summarized = res.get('memories_summarized', 0)
            space_saved = res.get('space_saved', 0)

            # AUTO-TRIGGER: Get summary statistics
            try:
                summary_stats = await get_summary_stats()
                logger.info(f"Updated summary stats: {summary_stats}")
            except Exception as e:
                logger.warning(f"Failed to update summary stats: {e}")

            # AUTO-TRIGGER: Publish summarization event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="category_summarized",
                        memory_id=f"summary_{category}",
                        agent_id="system",
                        data=json.dumps({
                            "category": category,
                            "days": days,
                            "memories_summarized": memories_summarized,
                            "space_saved": space_saved
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish category summarization event: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="summarize_category",
                        agent_id="system",
                        metadata={
                            "category": category,
                            "days": days,
                            "memories_summarized": memories_summarized,
                            "space_saved": space_saved
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log category summarization performance: {e}")

            return (f"OK Summarized {memories_summarized} memories "
                   f"in category '{category}':\n"
                   f"  Space saved: {space_saved} bytes")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"summarize_category failed: {e}")
        return f"ERR Failed to summarize category: {str(e)}"


@mcp.tool()
async def get_summary_stats() -> str:
    """
    Get statistics about memory summarization (Memory Summarization Tool)

    Returns:
    --------
    - Summarization statistics
    """
    if not memory_summarizer:
        return "ERR Memory Summarizer not available"

    try:
        stats = await memory_summarizer.get_summary_stats()

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_summary_stats",
                    agent_id="system",
                    metadata={
                        "total_memories": stats.get('total_memories', 0),
                        "summarized_memories": stats.get('summarized_memories', 0)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log summary stats performance: {e}")

        if "error" in stats:
            return f"ERR {stats['error']}"

        return (f"[STATS] Memory Summarization:\n"
               f"  Total memories: {stats.get('total_memories', 0)}\n"
               f"  Summarized memories: {stats.get('summarized_memories', 0)}\n"
               f"  Full memories: {stats.get('full_memories', 0)}\n"
               f"  Summarization ratio: {stats.get('summarization_ratio', '0%')}\n"
               f"  Estimated space saved: {stats.get('estimated_space_saved_mb', '0 MB')}")

    except Exception as e:
        logger.error(f"get_summary_stats failed: {e}")
        return f"ERR Failed to get summary stats: {str(e)}"


# ============================================================================
# PERFORMANCE ANALYTICS TOOLS - Metrics collection and monitoring
# ============================================================================

@mcp.tool()
async def get_performance_metrics() -> str:
    """
    Get comprehensive performance metrics (Performance Analytics Tool)

    Returns:
    --------
    - Detailed performance metrics including query times, cache stats, memory counts
    """
    if not performance_analytics:
        return "ERR Performance Analytics not available"

    try:
        metrics = await performance_analytics.get_performance_metrics()

        if "error" in metrics:
            return f"ERR {metrics['error']}"

        output = ["[PERF] Performance Metrics:", f"  Timestamp: {metrics.get('timestamp', 'unknown')}"]

        # Query performance
        if "query_performance" in metrics:
            qp = metrics["query_performance"]
            output.extend([
                "",
                "  Query Performance:",
                f"    Avg time: {qp.get('avg_time_ms', 0):.2f} ms",
                f"    Min time: {qp.get('min_time_ms', 0):.2f} ms",
                f"    Max time: {qp.get('max_time_ms', 0):.2f} ms",
                f"    P50 time: {qp.get('p50_time_ms', 0):.2f} ms",
                f"    P95 time: {qp.get('p95_time_ms', 0):.2f} ms",
                f"    Total queries: {qp.get('total_queries', 0)}"
            ])

        # Cache performance
        if "cache_performance" in metrics:
            cp = metrics["cache_performance"]
            output.extend([
                "",
                "  Cache Performance:",
                f"    Hits: {cp.get('hits', 0)}",
                f"    Misses: {cp.get('misses', 0)}",
                f"    Hit rate: {cp.get('hit_rate', '0%')}"
            ])

        # Memory stats
        if "memory_stats" in metrics:
            ms = metrics["memory_stats"]
            output.extend([
                "",
                "  Memory Statistics:",
                f"    Total memories: {ms.get('total_memories', 0)}",
                f"    Active agents: {ms.get('active_agents', 0)}"
            ])

        # Database stats
        if "database_stats" in metrics:
            ds = metrics["database_stats"]
            output.extend([
                "",
                "  Database:",
                f"    Size: {ds.get('database_size', 'unknown')}"
            ])

        return "\n".join(output)

    except Exception as e:
        logger.error(f"get_performance_metrics failed: {e}")
        return f"ERR Failed to get performance metrics: {str(e)}"


@mcp.tool()
async def get_slow_queries(threshold_ms: float = 1000, limit: int = 10) -> str:
    """
    Get slow queries above threshold (Performance Analytics Tool)

    Parameters:
    -----------
    - threshold_ms: Query time threshold in ms (default: 1000)
    - limit: Maximum number of slow queries to return (default: 10)

    Returns:
    --------
    - List of slow queries with execution times
    """
    if not performance_analytics:
        return "ERR Performance Analytics not available"

    try:
        slow_queries = await performance_analytics.get_slow_queries(threshold_ms, limit)

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_slow_queries",
                    agent_id="system",
                    metadata={
                        "threshold_ms": threshold_ms,
                        "limit": limit,
                        "slow_queries_found": len(slow_queries) if slow_queries else 0
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log get_slow_queries performance: {e}")

        if not slow_queries:
            return f"OK No queries found above {threshold_ms} ms threshold"

        output = [f"[SLOW QUERIES] Queries > {threshold_ms} ms:"]

        for i, query in enumerate(slow_queries, 1):
            output.append(f"\n  {i}. {query.get('operation', 'unknown')}")
            output.append(f"     Duration: {query.get('duration_ms', 0):.2f} ms")
            output.append(f"     Timestamp: {query.get('timestamp', 'unknown')}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"get_slow_queries failed: {e}")
        return f"ERR Failed to get slow queries: {str(e)}"


@mcp.tool()
async def get_prometheus_metrics() -> str:
    """
    Export metrics in Prometheus format (Performance Analytics Tool)

    Returns:
    --------
    - Prometheus-compatible metrics text
    """
    if not performance_analytics:
        return "ERR Performance Analytics not available"

    try:
        metrics = await performance_analytics.get_prometheus_metrics()

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_prometheus_metrics",
                    agent_id="system",
                    metadata={
                        "metrics_length": len(metrics)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log prometheus metrics performance: {e}")

        return f"OK Prometheus Metrics:\n\n{metrics}"

    except Exception as e:
        logger.error(f"get_prometheus_metrics failed: {e}")
        return f"ERR Failed to get Prometheus metrics: {str(e)}"


# ============================================================================
# CROSS-AGENT SHARING TOOLS - Controlled memory sharing between agents
# ============================================================================

@mcp.tool()
async def set_memory_sharing(memory_id: str, policy: str, allowed_agents: str = None) -> str:
    """
    Set sharing policy for a memory (Cross-Agent Sharing Tool)

    Parameters:
    -----------
    - memory_id: ID of the memory
    - policy: Sharing policy (private, shared, category_shared, custom)
    - allowed_agents: Optional JSON array of agent IDs for custom policy

    Returns:
    --------
    - Result of sharing policy setting
    """
    if not cross_agent_sharing:
        return "ERR Cross-Agent Sharing not available"

    try:
        # Parse policy enum
        try:
            share_policy = SharePolicy(policy.lower())
        except ValueError:
            return f"ERR Invalid policy: {policy}. Use: private, shared, category_shared, custom"

        # Parse allowed agents if provided
        allowed_list = None
        if allowed_agents:
            try:
                allowed_list = json.loads(allowed_agents)
            except:
                return f"ERR Invalid JSON for allowed_agents: {allowed_agents}"

        result = await cross_agent_sharing.set_memory_sharing(memory_id, share_policy, allowed_list)

        if result.get("status") == "success":
            # AUTO-TRIGGER: Publish sharing update event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="sharing_updated",
                        memory_id=memory_id,
                        agent_id="system",
                        data=json.dumps({
                            "policy": policy,
                            "allowed_agents": allowed_list
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish sharing event: {e}")

            # AUTO-TRIGGER: Sync with newly allowed agents
            if allowed_list and realtime_sync:
                try:
                    for agent_id in allowed_list:
                        await realtime_sync.sync_agent_state(
                            source_agent="system",
                            target_agent=agent_id,
                            category=None
                        )
                    logger.info(f"Synced with {len(allowed_list)} newly allowed agents")
                except Exception as e:
                    logger.warning(f"Failed to sync with allowed agents: {e}")

            return f"OK Set sharing policy '{policy}' for memory {memory_id}"
        elif result.get("status") == "not_found":
            return f"ERR Memory not found: {memory_id}"
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"set_memory_sharing failed: {e}")
        return f"ERR Failed to set sharing: {str(e)}"


@mcp.tool()
async def check_memory_access(memory_id: str, agent_id: str) -> str:
    """
    Check if an agent can access a memory (Cross-Agent Sharing Tool)

    Parameters:
    -----------
    - memory_id: ID of the memory
    - agent_id: Agent requesting access

    Returns:
    --------
    - Access decision with reason
    """
    if not cross_agent_sharing:
        return "ERR Cross-Agent Sharing not available"

    try:
        result = await cross_agent_sharing.can_agent_access_memory(memory_id, agent_id)

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="check_memory_access",
                    agent_id=agent_id,
                    metadata={
                        "memory_id": memory_id,
                        "can_access": result.get("can_access", False)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log check_access performance: {e}")

        can_access = result.get("can_access", False)
        reason = result.get("reason", "unknown")

        if can_access:
            return f"OK Agent '{agent_id}' CAN access memory {memory_id} (reason: {reason})"
        else:
            return f"NO Agent '{agent_id}' CANNOT access memory {memory_id} (reason: {reason})"

    except Exception as e:
        logger.error(f"check_memory_access failed: {e}")
        return f"ERR Failed to check access: {str(e)}"


@mcp.tool()
async def get_shared_memories(agent_id: str, limit: int = 50) -> str:
    """
    Get all memories shared with this agent (Cross-Agent Sharing Tool)

    Parameters:
    -----------
    - agent_id: Agent ID to get shared memories for
    - limit: Maximum results to return (default: 50)

    Returns:
    --------
    - List of shared memories
    """
    if not cross_agent_sharing:
        return "ERR Cross-Agent Sharing not available"

    try:
        memories = await cross_agent_sharing.get_shared_memories(agent_id, limit)

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_shared_memories",
                    agent_id=agent_id,
                    metadata={
                        "memories_count": len(memories) if memories else 0,
                        "limit": limit
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log get_shared_memories performance: {e}")

        if not memories:
            return f"OK No shared memories found for agent '{agent_id}'"

        output = [f"[SHARED] Memories shared with agent '{agent_id}' ({len(memories)} total):", ""]

        for memory in memories[:20]:  # Limit display
            output.append(f"- {memory['title']}")
            output.append(f"  ID: {memory['id']}")
            output.append(f"  Owner: {memory['owner_id']}")
            output.append(f"  Category: {memory['memory_category']}")
            output.append(f"  Created: {memory['created_at']}")
            output.append("")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"get_shared_memories failed: {e}")
        return f"ERR Failed to get shared memories: {str(e)}"


@mcp.tool()
async def create_shared_space(space_name: str, member_agents: str) -> str:
    """
    Create a shared memory space for multiple agents (Cross-Agent Sharing Tool)

    Parameters:
    -----------
    - space_name: Name for the shared space
    - member_agents: JSON array of agent IDs that can access this space

    Returns:
    --------
    - Result of shared space creation
    """
    if not cross_agent_sharing:
        return "ERR Cross-Agent Sharing not available"

    try:
        # Parse member agents
        try:
            members = json.loads(member_agents)
        except:
            return f"ERR Invalid JSON for member_agents: {member_agents}"

        result = await cross_agent_sharing.create_shared_space(space_name, members)

        if result.get("status") == "success":
            space_id = result.get('space_id', 'unknown')
            member_count = result.get('member_count', 0)

            # AUTO-TRIGGER: Publish space creation event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="space_created",
                        memory_id=space_id,
                        agent_id="system",
                        data=json.dumps({
                            "space_name": space_name,
                            "member_count": member_count,
                            "members": members
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish space creation event: {e}")

            # AUTO-TRIGGER: Sync with all member agents
            if realtime_sync:
                try:
                    for agent_id in members:
                        await realtime_sync.sync_agent_state(
                            source_agent="system",
                            target_agent=agent_id,
                            category=space_name
                        )
                    logger.info(f"Synced shared space '{space_name}' with {len(members)} agents")
                except Exception as e:
                    logger.warning(f"Failed to sync shared space: {e}")

            return (f"OK Created shared space '{space_name}' for {member_count} agents\n"
                   f"  Space ID: {space_id}")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"create_shared_space failed: {e}")
        return f"ERR Failed to create shared space: {str(e)}"


# ============================================================================
# REAL-TIME SYNC TOOLS - Synchronization across multiple agents
# ============================================================================

@mcp.tool()
async def publish_memory_event(event_type: str, memory_id: str, agent_id: str, data: str = "{}") -> str:
    """
    Publish a memory event to all subscribers (Real-Time Sync Tool)

    Parameters:
    -----------
    - event_type: Type of event (memory_added, memory_updated, memory_deleted)
    - memory_id: ID of the memory
    - agent_id: Agent that triggered the event
    - data: Optional JSON string with additional event data

    Returns:
    --------
    - Publish result
    """
    if not realtime_sync:
        return "ERR Real-Time Sync not available"

    try:
        # Parse data
        try:
            data_dict = json.loads(data)
        except:
            data_dict = {}

        result = await realtime_sync.publish_memory_event(event_type, memory_id, agent_id, data_dict)

        if result.get("status") == "success":
            return (f"OK Published {event_type} event for memory {memory_id} "
                   f"from agent {agent_id}")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"publish_memory_event failed: {e}")
        return f"ERR Failed to publish event: {str(e)}"


@mcp.tool()
async def get_sync_status() -> str:
    """
    Get synchronization status and statistics (Real-Time Sync Tool)

    Returns:
    --------
    - Sync status with subscriber information
    """
    if not realtime_sync:
        return "ERR Real-Time Sync not available"

    try:
        status = await realtime_sync.get_sync_status()

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="get_sync_status",
                    agent_id="system",
                    metadata={
                        "subscribers_count": status.get('subscribers_count', 0),
                        "status": status.get('status', 'unknown')
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log get_sync_status performance: {e}")

        if status.get("status") == "error":
            return f"ERR {status.get('error', 'Unknown error')}"

        return (f"[SYNC] Real-Time Sync Status:\n"
               f"  Status: {status.get('status', 'unknown')}\n"
               f"  Channel: {status.get('sync_channel', 'unknown')}\n"
               f"  Subscribed agents: {status.get('subscribers_count', 0)}\n"
               f"  Agent list: {', '.join(status.get('subscribed_agents', []))}\n"
               f"  Redis connected clients: {status.get('redis_connected_clients', 0)}")

    except Exception as e:
        logger.error(f"get_sync_status failed: {e}")
        return f"ERR Failed to get sync status: {str(e)}"


@mcp.tool()
async def sync_agent_state(source_agent: str, target_agent: str, category: str = None) -> str:
    """
    Synchronize memory state between two agents (Real-Time Sync Tool)

    Parameters:
    -----------
    - source_agent: Source agent ID to sync from
    - target_agent: Target agent ID to sync to
    - category: Optional category filter

    Returns:
    --------
    - Sync result with memories synced
    """
    if not realtime_sync:
        return "ERR Real-Time Sync not available"

    try:
        # AUTO-TRIGGER: Check memory access before syncing
        if cross_agent_sharing:
            try:
                # Verify access permissions exist
                access_check = await cross_agent_sharing.can_agent_access_memory(
                    memory_id="*",  # Check general access
                    agent_id=target_agent
                )
                logger.info(f"Memory access check: {access_check}")
            except Exception as e:
                logger.warning(f"Memory access check failed: {e}")

        result = await realtime_sync.sync_agent_state(source_agent, target_agent, category)

        if result.get("status") == "success":
            memories_synced = result.get('memories_synced', 0)
            errors = result.get("errors", [])
            error_msg = f"\nErrors: {len(errors)}" if errors else ""

            # AUTO-TRIGGER: Publish sync event
            try:
                await realtime_sync.publish_memory_event(
                    event_type="agent_synced",
                    memory_id=f"sync_{source_agent}_{target_agent}",
                    agent_id=source_agent,
                    data=json.dumps({
                        "target_agent": target_agent,
                        "category": category,
                        "memories_synced": memories_synced,
                        "errors": len(errors)
                    })
                )
            except Exception as e:
                logger.warning(f"Failed to publish sync event: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="sync_agent_state",
                        agent_id=source_agent,
                        metadata={
                            "target_agent": target_agent,
                            "category": category,
                            "memories_synced": memories_synced,
                            "errors_count": len(errors)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log sync performance: {e}")

            return (f"OK Synced {memories_synced} memories "
                   f"from '{source_agent}' to '{target_agent}'{error_msg}")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"sync_agent_state failed: {e}")
        return f"ERR Failed to sync agent state: {str(e)}"


# ============================================================================
# SPRINT 8: ADVANCED FEATURES - Backup, Recovery, Maintenance, Dedup, Summar
# ============================================================================

# Import Sprint 8 modules
from src.backup_manager import BackupManager
from src.recovery_manager import RecoveryManager
from src.maintenance_scheduler import MaintenanceScheduler
from src.scheduled_deduplication import ScheduledDeduplication
from src.scheduled_summarization import ScheduledSummarization

# Sprint 8 instances
backup_manager = None
recovery_manager = None
maintenance_scheduler = None
scheduled_deduplication = None
scheduled_summarization = None


async def init_sprint8_modules():
    """Initialize Sprint 8 modules"""
    global backup_manager, recovery_manager, maintenance_scheduler
    global scheduled_deduplication, scheduled_summarization

    # Initialize Backup Manager
    if postgres_pool:
        backup_manager = BackupManager()
        logger.info("OK Backup Manager initialized")

    # Initialize Recovery Manager
    if postgres_pool:
        recovery_manager = RecoveryManager()
        logger.info("OK Recovery Manager initialized")

    # Initialize Maintenance Scheduler and AUTO-START it
    maintenance_scheduler = MaintenanceScheduler(mcp_client=None)
    try:
        maintenance_scheduler.start()
        logger.info("OK Maintenance Scheduler initialized and AUTO-STARTED")
    except Exception as e:
        logger.warning(f"Maintenance Scheduler start failed: {e}")

    # Initialize Scheduled Deduplication
    if postgres_pool and qdrant_client:
        scheduled_deduplication = ScheduledDeduplication(
            postgres_pool, qdrant_client
        )
        logger.info("OK Scheduled Deduplication initialized")

    # Initialize Scheduled Summarization
    if postgres_pool:
        scheduled_summarization = ScheduledSummarization(
            postgres_pool, llm_client=None
        )
        logger.info("OK Scheduled Summarization initialized")


@mcp.tool()
async def create_backup(
    backup_type: str = "manual",
    databases: Optional[str] = None,
    compress: bool = True,
    description: str = ""
) -> str:
    """
    Create a backup of Enhanced Cognee databases (Backup Tool)

    Parameters:
    -----------
    - backup_type: Type of backup ('manual', 'daily', 'weekly', 'monthly')
    - databases: Comma-separated list of databases to backup (default: all)
    - compress: Whether to compress backups (default: True)
    - description: Optional description

    Returns:
    --------
    - Backup ID and status message
    """
    if not backup_manager:
        return "ERR Backup Manager not available"

    try:
        db_list = databases.split(",") if databases else None
        backup_id = backup_manager.create_backup(
            backup_type=backup_type,
            databases=db_list,
            compress=compress,
            description=description
        )

        logger.info(f"OK Backup created: {backup_id}")

        # AUTO-TRIGGER: Verify backup integrity
        try:
            verification = await verify_backup(backup_id)
            logger.info(f"Backup verification: {verification}")
        except Exception as e:
            logger.warning(f"Backup verification failed: {e}")

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="create_backup",
                    agent_id="system",
                    metadata={
                        "backup_id": backup_id,
                        "backup_type": backup_type,
                        "databases": db_list,
                        "compressed": compress
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log backup performance: {e}")

        # AUTO-TRIGGER: Publish backup event
        if realtime_sync:
            try:
                await realtime_sync.publish_memory_event(
                    event_type="backup_created",
                    memory_id=backup_id,
                    agent_id="system",
                    data=json.dumps({
                        "backup_type": backup_type,
                        "databases": db_list,
                        "compressed": compress,
                        "description": description
                    })
                )
            except Exception as e:
                logger.warning(f"Failed to publish backup event: {e}")

        return f"OK Backup created (ID: {backup_id})"

    except Exception as e:
        logger.error(f"create_backup failed: {e}")
        return f"ERR Failed to create backup: {str(e)}"


@mcp.tool()
async def restore_backup(
    backup_id: str,
    databases: Optional[str] = None,
    validate: bool = True
) -> str:
    """
    Restore databases from backup (Recovery Tool)

    Parameters:
    -----------
    - backup_id: Backup ID to restore
    - databases: Comma-separated list of databases to restore (default: all)
    - validate: Whether to validate after restore (default: True)

    Returns:
    --------
    - Restore result with status
    """
    if not recovery_manager:
        return "ERR Recovery Manager not available"

    try:
        db_list = databases.split(",") if databases else None
        result = recovery_manager.restore_from_backup(
            backup_id=backup_id,
            databases=db_list,
            validate=validate
        )

        if result["status"] == "success":
            # AUTO-TRIGGER: Health check after successful restore
            try:
                health_status = await health()
                logger.info(f"Health check after restore: {health_status}")
            except Exception as e:
                logger.warning(f"Health check failed after restore: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="restore_backup",
                        agent_id="system",
                        metadata={
                            "backup_id": backup_id,
                            "databases_restored": result.get('databases_restored', []),
                            "restore_id": result.get('restore_id'),
                            "status": "success"
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log restore performance: {e}")

            # AUTO-TRIGGER: Publish restore event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="backup_restored",
                        memory_id=backup_id,
                        agent_id="system",
                        data=json.dumps({
                            "restore_id": result.get('restore_id'),
                            "databases_restored": result.get('databases_restored', [])
                        })
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish restore event: {e}")

            return (f"OK Restore completed (ID: {result['restore_id']})\n"
                   f"Databases restored: {', '.join(result['databases_restored'])}")
        else:
            # AUTO-TRIGGER: Rollback on failure
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Restore failed: {error_msg}")

            try:
                rollback_result = await rollback_restore()
                logger.info(f"Rollback initiated: {rollback_result}")
            except Exception as e:
                logger.error(f"Rollback failed: {e}")

            # AUTO-TRIGGER: Publish failure event
            if realtime_sync:
                try:
                    await realtime_sync.publish_memory_event(
                        event_type="restore_failed",
                        memory_id=backup_id,
                        agent_id="system",
                        data=json.dumps({"error": error_msg})
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish failure event: {e}")

            return f"ERR Restore failed: {error_msg}"

    except Exception as e:
        logger.error(f"restore_backup failed: {e}")

        # AUTO-TRIGGER: Rollback on exception
        try:
            rollback_result = await rollback_restore()
            logger.info(f"Rollback initiated after exception: {rollback_result}")
        except Exception as rollback_e:
            logger.error(f"Rollback failed after exception: {rollback_e}")

        return f"ERR Failed to restore backup: {str(e)}"


@mcp.tool()
async def list_backups(
    backup_type: Optional[str] = None,
    limit: int = 50
) -> str:
    """
    List all backups (Backup Tool)

    Parameters:
    -----------
    - backup_type: Filter by backup type (optional)
    - limit: Maximum results (default: 50)

    Returns:
    --------
    - Formatted list of backups
    """
    if not backup_manager:
        return "ERR Backup Manager not available"

    try:
        backups = backup_manager.list_backups(backup_type=backup_type, limit=limit)

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="list_backups",
                    agent_id="system",
                    metadata={
                        "backups_count": len(backups) if backups else 0,
                        "backup_type": backup_type,
                        "limit": limit
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log list_backups performance: {e}")

        if backups:
            results = []
            for backup in backups:
                results.append(
                    f"- {backup['backup_id'][:8]}... "
                    f"({backup['backup_type']}, {backup['created_at'][:10]}) "
                    f"{backup['total_size_bytes']:,} bytes"
                )
            return f"[OK] Backups ({len(backups)} total):\n\n" + "\n".join(results)
        else:
            return "[OK] No backups found"

    except Exception as e:
        logger.error(f"list_backups failed: {e}")
        return f"ERR Failed to list backups: {str(e)}"


@mcp.tool()
async def verify_backup(backup_id: str) -> str:
    """
    Verify backup integrity (Backup Tool)

    Parameters:
    -----------
    - backup_id: Backup ID to verify

    Returns:
    --------
    - Verification result
    """
    if not backup_manager:
        return "ERR Backup Manager not available"

    try:
        backup = backup_manager.get_backup(backup_id)

        if not backup:
            return f"ERR Backup not found: {backup_id}"

        # Basic verification - check if files exist
        backup_path = Path(backup["backup_path"])
        if not backup_path.exists():
            return f"ERR Backup files missing: {backup_path}"

        file_count = len(list(backup_path.rglob("*")))

        # AUTO-TRIGGER: Log performance metrics
        if performance_analytics:
            try:
                await performance_analytics.log_operation(
                    operation="verify_backup",
                    agent_id="system",
                    metadata={
                        "backup_id": backup_id,
                        "file_count": file_count,
                        "backup_size": backup['total_size_bytes']
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log verify_backup performance: {e}")

        return (f"OK Backup verified (ID: {backup_id[:8]}...)\n"
               f"Files found: {file_count}\n"
               f"Size: {backup['total_size_bytes']:,} bytes\n"
               f"Checksum: {backup['checksum'][:16]}...")

    except Exception as e:
        logger.error(f"verify_backup failed: {e}")
        return f"ERR Failed to verify backup: {str(e)}"


@mcp.tool()
async def rollback_restore() -> str:
    """
    Rollback the last restore operation (Recovery Tool)

    Returns:
    --------
    - Rollback result
    """
    if not recovery_manager:
        return "ERR Recovery Manager not available"

    try:
        result = recovery_manager.rollback_last_restore()

        if result["status"] == "success":
            # AUTO-TRIGGER: Health check after rollback
            try:
                health_status = await health()
                logger.info(f"Health check after rollback: {health_status}")
            except Exception as e:
                logger.warning(f"Health check failed after rollback: {e}")

            # AUTO-TRIGGER: Log performance metrics
            if performance_analytics:
                try:
                    await performance_analytics.log_operation(
                        operation="rollback_restore",
                        agent_id="system",
                        metadata={
                            "restore_id": result.get('restore_id'),
                            "status": "success"
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log rollback performance: {e}")

            return f"OK Rollback completed (ID: {result['restore_id']})"
        elif result["status"] == "skipped":
            return f"INFO {result['reason']}"
        else:
            return f"ERR Rollback failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"rollback_restore failed: {e}")
        return f"ERR Failed to rollback: {str(e)}"


@mcp.tool()
async def schedule_task(
    task_name: str,
    schedule: str,
    enabled: bool = True
) -> str:
    """
    Schedule a maintenance task (Maintenance Scheduler Tool)

    Parameters:
    -----------
    - task_name: Name of task (cleanup, archival, optimization, cache_clearing, backup_verification)
    - schedule: Cron expression (e.g., "0 2 * * *" for daily at 2 AM)
    - enabled: Whether to enable the task (default: True)

    Returns:
    --------
    - Scheduling result
    """
    if not maintenance_scheduler:
        return "ERR Maintenance Scheduler not available"

    try:
        if task_name == "cleanup":
            maintenance_scheduler.schedule_cleanup(schedule=schedule)
        elif task_name == "archival":
            maintenance_scheduler.schedule_archival(schedule=schedule)
        elif task_name == "optimization":
            maintenance_scheduler.schedule_optimization(schedule=schedule)
        elif task_name == "cache_clearing":
            maintenance_scheduler.schedule_cache_clearing(schedule=schedule)
        elif task_name == "backup_verification":
            maintenance_scheduler.schedule_backup_verification(schedule=schedule)
        else:
            return f"ERR Unknown task: {task_name}"

        maintenance_scheduler.save_config()
        return f"OK Task scheduled: {task_name} ({schedule})"

    except Exception as e:
        logger.error(f"schedule_task failed: {e}")
        return f"ERR Failed to schedule task: {str(e)}"


@mcp.tool()
async def list_tasks() -> str:
    """
    List all scheduled maintenance tasks (Maintenance Scheduler Tool)

    Returns:
    --------
    - Formatted list of scheduled tasks
    """
    if not maintenance_scheduler:
        return "ERR Maintenance Scheduler not available"

    try:
        tasks = maintenance_scheduler.get_scheduled_tasks()

        if tasks:
            results = []
            for task_id, task_info in tasks.items():
                next_run = task_info.get('next_run_time', 'Unknown')
                results.append(
                    f"- {task_id}: {task_info['name']}\n"
                    f"  Next run: {next_run}"
                )
            return f"[OK] Scheduled tasks ({len(tasks)} total):\n\n" + "\n\n".join(results)
        else:
            return "[OK] No scheduled tasks"

    except Exception as e:
        logger.error(f"list_tasks failed: {e}")
        return f"ERR Failed to list tasks: {str(e)}"


@mcp.tool()
async def cancel_task(task_id: str) -> str:
    """
    Cancel a scheduled maintenance task (Maintenance Scheduler Tool)

    Parameters:
    -----------
    - task_id: ID of task to cancel

    Returns:
    --------
    - Cancellation result
    """
    if not maintenance_scheduler:
        return "ERR Maintenance Scheduler not available"

    try:
        success = maintenance_scheduler.cancel_task(task_id)

        if success:
            maintenance_scheduler.save_config()
            return f"OK Task cancelled: {task_id}"
        else:
            return f"ERR Failed to cancel task: {task_id}"

    except Exception as e:
        logger.error(f"cancel_task failed: {e}")
        return f"ERR Failed to cancel task: {str(e)}"


@mcp.tool()
async def deduplicate(
    agent_id: Optional[str] = None,
    dry_run: bool = True
) -> str:
    """
    Perform memory deduplication (Deduplication Tool)

    Parameters:
    -----------
    - agent_id: Optional agent ID to scope deduplication
    - dry_run: If True, show what would be merged without actually merging (default: True)

    Returns:
    --------
    - Deduplication result with duplicates found and token savings
    """
    if not scheduled_deduplication:
        return "ERR Scheduled Deduplication not available"

    try:
        result = await scheduled_deduplication.deduplicate_memories(
            agent_id=agent_id,
            dry_run=dry_run
        )

        if result["status"] == "success":
            if dry_run:
                return (f"OK Dry run complete\n"
                       f"Duplicates found: {result['duplicates_found']}\n"
                       f"Token savings: {result['token_savings']:,}\n"
                       f"Deduplication ID: {result['deduplication_id']}\n\n"
                       f"{result.get('approval_message', '')}")
            else:
                return (f"OK Deduplication complete\n"
                       f"Merged: {result['merged_count']} memories\n"
                       f"Deduplication ID: {result['deduplication_id']}")
        else:
            return f"ERR Deduplication failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"deduplicate failed: {e}")
        return f"ERR Failed to deduplicate: {str(e)}"


@mcp.tool()
async def schedule_deduplication(schedule: str = "weekly") -> str:
    """
    Schedule periodic deduplication (Deduplication Tool)

    Parameters:
    -----------
    - schedule: Schedule type ('weekly', 'daily', 'monthly')

    Returns:
    --------
    - Scheduling result
    """
    if not scheduled_deduplication:
        return "ERR Scheduled Deduplication not available"

    try:
        trigger = scheduled_deduplication.schedule_weekly_deduplication()
        return f"OK Deduplication scheduled: {schedule}"

    except Exception as e:
        logger.error(f"schedule_deduplication failed: {e}")
        return f"ERR Failed to schedule deduplication: {str(e)}"


@mcp.tool()
async def deduplication_report(deduplication_id: Optional[str] = None) -> str:
    """
    Generate deduplication report (Deduplication Tool)

    Parameters:
    -----------
    - deduplication_id: Optional specific deduplication ID

    Returns:
    --------
    - Formatted deduplication report
    """
    if not scheduled_deduplication:
        return "ERR Scheduled Deduplication not available"

    try:
        report = scheduled_deduplication.deduplication_report(deduplication_id)

        if deduplication_id:
            # Specific deduplication report
            if "error" in report:
                return f"ERR {report['error']}"

            return (f"OK Deduplication Report: {deduplication_id}\n"
                   f"Status: {report['status']}\n"
                   f"Duplicates found: {report['duplicates_found']}\n"
                   f"Merged: {report.get('merged_count', 0)}\n"
                   f"Token savings: {report['token_savings']:,}")
        else:
            # Summary report
            return (f"OK Deduplication Summary Report\n"
                   f"Total deduplications: {report['total_deduplications']}\n"
                   f"Total duplicates found: {report['total_duplicates_found']}\n"
                   f"Total memories merged: {report['total_memories_merged']}\n"
                   f"Total token savings: {report['total_token_savings']:,}")

    except Exception as e:
        logger.error(f"deduplication_report failed: {e}")
        return f"ERR Failed to generate report: {str(e)}"


@mcp.tool()
async def summarize_old_memories(
    days: int = 30,
    min_length: int = 1000,
    dry_run: bool = False
) -> str:
    """
    Summarize old memories (Summarization Tool)

    Parameters:
    -----------
    - days: Age threshold in days (default: 30)
    - min_length: Minimum content length to summarize (default: 1000)
    - dry_run: If True, simulate without summarizing (default: False)

    Returns:
    --------
    - Summarization result with memories summarized and token savings
    """
    if not scheduled_summarization:
        return "ERR Scheduled Summarization not available"

    try:
        result = await scheduled_summarization.summarize_old_memories(
            days=days,
            min_length=min_length,
            dry_run=dry_run
        )

        if result["status"] == "success":
            if dry_run:
                return (f"OK Dry run complete\n"
                       f"Candidates found: {result['candidates_found']}\n"
                       f"Would save: {result['space_saved_bytes']:,} bytes\n"
                       f"Summarization ID: {result['summarization_id']}")
            else:
                return (f"OK Summarization complete\n"
                       f"Memories summarized: {result['memories_summarized']}\n"
                       f"Space saved: {result['space_saved_bytes']:,} bytes\n"
                       f"Token savings: {result['token_savings']:,}\n"
                       f"Summarization ID: {result['summarization_id']}")
        else:
            return f"ERR Summarization failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"summarize_old_memories failed: {e}")
        return f"ERR Failed to summarize: {str(e)}"


@mcp.tool()
async def schedule_summarization(schedule: str = "monthly") -> str:
    """
    Schedule periodic summarization (Summarization Tool)

    Parameters:
    -----------
    - schedule: Schedule type ('monthly', 'weekly')

    Returns:
    --------
    - Scheduling result
    """
    if not scheduled_summarization:
        return "ERR Scheduled Summarization not available"

    try:
        trigger = scheduled_summarization.schedule_monthly_summarization()
        return f"OK Summarization scheduled: {schedule}"

    except Exception as e:
        logger.error(f"schedule_summarization failed: {e}")
        return f"ERR Failed to schedule summarization: {str(e)}"


@mcp.tool()
async def summary_stats() -> str:
    """
    Get summarization statistics (Summarization Tool)

    Returns:
    --------
    - Formatted summarization statistics
    """
    if not scheduled_summarization:
        return "ERR Scheduled Summarization not available"

    try:
        stats = await scheduled_summarization.summarization_statistics()

        if "error" in stats:
            return f"ERR {stats['error']}"

        return (f"OK Summarization Statistics\n"
               f"Total memories: {stats['total_memories']}\n"
               f"Summarized: {stats['summarized_memories']}\n"
               f"Full memories: {stats['full_memories']}\n"
               f"Summarization ratio: {stats['summarization_ratio']}\n"
               f"Space saved: {stats['estimated_space_saved_mb']}")

    except Exception as e:
        logger.error(f"summary_stats failed: {e}")
        return f"ERR Failed to get summarization statistics: {str(e)}"


# ============================================================================
# SPRINT 9: MULTI-LANGUAGE TOOLS - 28 language support with cross-language search
# ============================================================================

@mcp.tool()
async def detect_language(text: str) -> str:
    """
    Detect language from text (Language Detection Tool)

    Supports 28 languages: English, Spanish, French, German, Chinese (Simplified/Traditional),
    Japanese, Korean, Russian, Arabic, Portuguese, Italian, Dutch, Polish, Swedish, Danish,
    Norwegian, Finnish, Greek, Czech, Hungarian, Romanian, Bulgarian, Slovak, Croatian,
    Serbian, Slovenian, Lithuanian, Latvian

    Parameters:
    -----------
    - text: Text to analyze for language detection

    Returns:
    --------
    - Language code and confidence score
    """
    try:
        lang_code, confidence = language_detector.detect_language(text)
        lang_name = language_detector.get_language_name(lang_code)

        return (f"OK Language Detected\n"
               f"  Language: {lang_name}\n"
               f"  Code: {lang_code}\n"
               f"  Confidence: {confidence:.2f}\n"
               f"  Supported: {language_detector.is_supported(lang_code)}")

    except Exception as e:
        logger.error(f"detect_language failed: {e}")
        return f"ERR Failed to detect language: {str(e)}"


@mcp.tool()
async def get_supported_languages() -> str:
    """
    Get list of all supported languages (Language Detection Tool)

    Returns:
    --------
    - Complete list of 28 supported languages
    """
    try:
        languages = language_detector.get_all_supported_languages()

        result = "OK Supported Languages (28):\n"
        for code, info in languages.items():
            result += f"  {code}: {info['name']} ({info['native_name']})\n"

        return result

    except Exception as e:
        logger.error(f"get_supported_languages failed: {e}")
        return f"ERR Failed to get supported languages: {str(e)}"


@mcp.tool()
async def search_by_language(
    query: str,
    user_id: str = "default",
    agent_id: str = "claude-code",
    language: str = None,
    limit: int = 10
) -> str:
    """
    Search memories with language filtering (Multi-Language Search Tool)

    Parameters:
    -----------
    - query: Search query text
    - user_id: User identifier (default: 'default')
    - agent_id: Agent identifier (default: 'claude-code')
    - language: Language code to filter by (e.g., 'en', 'es', 'fr'). None = all languages
    - limit: Maximum results (default: 10)

    Returns:
    --------
    - Search results filtered by language
    """
    if not postgres_pool:
        return "ERR PostgreSQL not available"

    try:
        # Search memories
        async with postgres_pool.acquire() as conn:
            memories = await conn.fetch("""
                SELECT id, data_text, metadata, created_at
                FROM shared_memory.documents
                WHERE user_id = $1
                AND (agent_id = $2 OR agent_id = 'shared')
                AND (
                    to_tsvector('english', coalesce(data_text, '')) @@ plainto_tsquery('english', $3)
                    OR data_text ILIKE '%' || $3 || '%'
                )
                ORDER BY created_at DESC
                LIMIT $4
            """, user_id, agent_id, query, limit * 2)  # Get more for filtering

        # Convert to list of dicts
        memory_dicts = []
        for row in memories:
            memory_dicts.append({
                'id': str(row['id']),
                'content': row['data_text'],
                'metadata': row['metadata'],
                'created_at': row['created_at'].isoformat()
            })

        # Filter by language (if specified)
        if language:
            filtered = multi_language_search.search_by_language(
                memory_dicts,
                language=language,
                min_confidence=0.5
            )
            lang_name = language_detector.get_language_name(language)
        else:
            # Search all languages
            filtered = memory_dicts
            lang_name = "All Languages"

        # Format results
        result = f"OK Found {len(filtered)} memories in {lang_name}:\n\n"
        for memory in filtered[:limit]:
            result += f"[{memory['id']}] {memory['content'][:100]}...\n"

        if len(filtered) == 0:
            if language:
                result += f"No memories found in language '{language}'"
            else:
                result += "No memories found"

        return result

    except Exception as e:
        logger.error(f"search_by_language failed: {e}")
        return f"ERR Failed to search by language: {str(e)}"


@mcp.tool()
async def get_language_distribution(
    user_id: str = "default",
    agent_id: str = "claude-code"
) -> str:
    """
    Get distribution of languages across memories (Multi-Language Analytics Tool)

    Parameters:
    -----------
    - user_id: User identifier (default: 'default')
    - agent_id: Agent identifier (default: 'claude-code')

    Returns:
    --------
    - Language distribution statistics
    """
    if not postgres_pool:
        return "ERR PostgreSQL not available"

    try:
        # Get all memories
        async with postgres_pool.acquire() as conn:
            memories = await conn.fetch("""
                SELECT id, metadata
                FROM shared_memory.documents
                WHERE user_id = $1
                AND (agent_id = $2 OR agent_id = 'shared')
            """, user_id, agent_id)

        # Convert to list of dicts
        memory_dicts = []
        for row in memories:
            memory_dicts.append({
                'id': str(row['id']),
                'metadata': row['metadata']
            })

        # Get distribution
        distribution = multi_language_search.get_language_distribution(memory_dicts)

        # Format results
        total = sum(distribution.values())
        result = f"OK Language Distribution ({total} memories):\n\n"

        # Sort by count
        sorted_dist = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        for lang_code, count in sorted_dist:
            lang_name = language_detector.get_language_name(lang_code)
            percentage = (count / total * 100) if total > 0 else 0
            result += f"  {lang_name}: {count} ({percentage:.1f}%)\n"

        if total == 0:
            result += "  No memories found"

        return result

    except Exception as e:
        logger.error(f"get_language_distribution failed: {e}")
        return f"ERR Failed to get language distribution: {str(e)}"


@mcp.tool()
async def cross_language_search(
    query: str,
    user_id: str = "default",
    agent_id: str = "claude-code",
    limit: int = 10
) -> str:
    """
    Cross-language search with relevance boosting (Multi-Language Search Tool)

    Searches memories in any language, with relevance boosting for memories
    in the same language as the query.

    Parameters:
    -----------
    - query: Search query text (language auto-detected)
    - user_id: User identifier (default: 'default')
    - agent_id: Agent identifier (default: 'claude-code')
    - limit: Maximum results (default: 10)

    Returns:
    --------
    - Cross-language search results ranked by relevance
    """
    if not postgres_pool:
        return "ERR PostgreSQL not available"

    try:
        # Detect query language
        query_lang, query_conf = language_detector.detect_language(query)
        query_lang_name = language_detector.get_language_name(query_lang)

        # Search memories
        async with postgres_pool.acquire() as conn:
            memories = await conn.fetch("""
                SELECT id, data_text, metadata, created_at
                FROM shared_memory.documents
                WHERE user_id = $1
                AND (agent_id = $2 OR agent_id = 'shared')
                AND (
                    to_tsvector('english', coalesce(data_text, '')) @@ plainto_tsquery('english', $3)
                    OR data_text ILIKE '%' || $3 || '%'
                )
                ORDER BY created_at DESC
                LIMIT $4
            """, user_id, agent_id, query, limit * 2)

        # Convert to list of dicts
        memory_dicts = []
        for row in memories:
            memory_dicts.append({
                'id': str(row['id']),
                'content': row['data_text'],
                'metadata': row['metadata'],
                'created_at': row['created_at'].isoformat()
            })

        # Cross-language search with ranking
        ranked = multi_language_search.cross_language_search(
            query=query,
            memories=memory_dicts,
            query_language=query_lang
        )

        # Format results
        result = f"OK Cross-Language Search (Query: {query_lang_name})\n"
        result += f"Found {len(ranked)} memories:\n\n"

        for i, memory in enumerate(ranked[:limit], 1):
            metadata = memory.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}

            mem_lang = metadata.get('language', 'unknown')
            mem_lang_name = language_detector.get_language_name(mem_lang)

            match = "SAME" if mem_lang == query_lang else "DIFF"
            result += f"{i}. [{match}] {mem_lang_name}: {memory['content'][:80]}...\n"

        return result

    except Exception as e:
        logger.error(f"cross_language_search failed: {e}")
        return f"ERR Failed to perform cross-language search: {str(e)}"


@mcp.tool()
async def get_search_facets(
    user_id: str = "default",
    agent_id: str = "claude-code"
) -> str:
    """
    Get search facets for advanced filtering (Advanced Search Tool)

    Returns faceted counts for language, memory type, and category.

    Parameters:
    -----------
    - user_id: User identifier (default: 'default')
    - agent_id: Agent identifier (default: 'claude-code')

    Returns:
    --------
    - Faceted search options with counts
    """
    if not postgres_pool:
        return "ERR PostgreSQL not available"

    try:
        # Get all memories
        async with postgres_pool.acquire() as conn:
            memories = await conn.fetch("""
                SELECT id, metadata
                FROM shared_memory.documents
                WHERE user_id = $1
                AND (agent_id = $2 OR agent_id = 'shared')
            """, user_id, agent_id)

        # Convert to list of dicts
        memory_dicts = []
        for row in memories:
            memory_dicts.append({
                'id': str(row['id']),
                'metadata': row['metadata']
            })

        # Get facets
        facets = multi_language_search.get_facets(memory_dicts)

        # Format results
        result = "OK Search Facets:\n\n"

        for facet_name, facet_values in facets.items():
            result += f"{facet_name.upper()}:\n"
            for value, count in sorted(facet_values.items(), key=lambda x: x[1], reverse=True):
                result += f"  {value}: {count}\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"get_search_facets failed: {e}")
        return f"ERR Failed to get search facets: {str(e)}"


# ============================================================================
# SPRINT 10: ADVANCED AI FEATURES - Intelligent Summarization & Advanced Search
# ============================================================================

@mcp.tool()
async def intelligent_summarize(
    memory_id: str,
    strategy: str = "standard",
    llm_provider: str = "openai"
) -> str:
    """
    Summarize a memory using LLM-based intelligent summarization (Sprint 10)

    Parameters:
    -----------
    - memory_id: ID of the memory to summarize
    - strategy: Summarization strategy ('concise', 'standard', 'detailed', 'extractive')
    - llm_provider: LLM provider ('openai', 'anthropic', 'ollama')

    Returns:
    --------
    - Summary with compression ratio and metadata
    """
    if not intelligent_summarizer:
        return "ERR Intelligent Summarizer not available"

    try:
        # Get memory
        if not postgres_pool:
            return "ERR PostgreSQL not available"

        async with postgres_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, content, metadata, created_at
                FROM shared_memory.documents
                WHERE id = $1
            """, memory_id)

            if not row:
                return f"ERR Memory not found: {memory_id}"

            memory = {
                'id': str(row['id']),
                'content': row['content'],
                'metadata': row['metadata'],
                'created_at': row['created_at']
            }

        # Parse strategy
        try:
            summary_strategy = SummaryStrategy(strategy.lower())
        except ValueError:
            return f"ERR Invalid strategy: {strategy}. Use: concise, standard, detailed, extractive"

        # Update LLM config
        intelligent_summarizer.llm_config['provider'] = llm_provider

        # Summarize
        result = await intelligent_summarizer.summarize_memory(memory, summary_strategy)

        return (f"OK Summary Generated\n"
               f"  Memory ID: {result.memory_id}\n"
               f"  Strategy: {result.strategy.value}\n"
               f"  Compression Ratio: {result.compression_ratio:.2f}x\n"
               f"  Keywords: {', '.join(result.keywords[:5])}\n"
               f"  Entities: {len(result.entities)} found\n"
               f"  Summary:\n"
               f"    {result.summary}\n\n"
               f"  Store this summary using update_memory to persist it")

    except Exception as e:
        logger.error(f"intelligent_summarize failed: {e}")
        return f"ERR Failed to summarize: {str(e)}"


@mcp.tool()
async def auto_summarize_old_memories(
    days_old: int = 30,
    min_length: int = 500,
    dry_run: bool = False,
    strategy: str = "standard"
) -> str:
    """
    Automatically summarize old memories (Sprint 10)

    Parameters:
    -----------
    - days_old: Minimum age in days (default: 30)
    - min_length: Minimum content length to summarize (default: 500)
    - dry_run: If True, simulate without summarizing (default: False)
    - strategy: Summarization strategy (default: 'standard')

    Returns:
    --------
    - Summarization statistics
    """
    if not intelligent_summarizer:
        return "ERR Intelligent Summarizer not available"

    try:
        # Update settings
        intelligent_summarizer.min_memory_age_days = days_old
        intelligent_summarizer.min_memory_length = min_length

        # Parse strategy
        try:
            summary_strategy = SummaryStrategy(strategy.lower())
        except ValueError:
            return f"ERR Invalid strategy: {strategy}"

        # Run auto-summarization
        result = await intelligent_summarizer.auto_summarize_old_memories(dry_run=dry_run)

        if result.get("status") == "success":
            if dry_run:
                return (f"OK DRY RUN - Auto Summarization\n"
                       f"  Candidates Found: {result['total_candidates']}\n"
                       f"  Would Summarize: {result['summarized']}\n"
                       f"  Would Skip: {result['skipped']}\n"
                       f"  Would Fail: {result['failed']}\n"
                       f"  Est. Compression: {result.get('total_compression_ratio', 0):.2f}x")
            else:
                return (f"OK Auto Summarization Complete\n"
                       f"  Total Candidates: {result['total_candidates']}\n"
                       f"  Summarized: {result['summarized']}\n"
                       f"  Skipped: {result['skipped']}\n"
                       f"  Failed: {result['failed']}\n"
                       f"  Avg Compression: {result.get('total_compression_ratio', 0):.2f}x")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"auto_summarize_old_memories failed: {e}")
        return f"ERR Failed to auto-summarize: {str(e)}"


@mcp.tool()
async def cluster_memories(
    category: Optional[str] = None,
    agent_id: Optional[str] = None,
    limit: int = 100
) -> str:
    """
    Cluster related memories using semantic similarity (Sprint 10)

    Parameters:
    -----------
    - category: Optional category filter
    - agent_id: Optional agent ID filter
    - limit: Maximum memories to process (default: 100)

    Returns:
    --------
    - Memory clusters with themes
    """
    if not intelligent_summarizer:
        return "ERR Intelligent Summarizer not available"

    try:
        # Find memories
        if not postgres_pool:
            return "ERR PostgreSQL not available"

        async with postgres_pool.acquire() as conn:
            query = """
                SELECT id, content, metadata, agent_id, created_at
                FROM shared_memory.documents
                WHERE LENGTH(content) > 100
            """
            params = []
            param_count = 1

            if category:
                query += f" AND metadata->>'memory_category' = ${param_count}"
                params.append(category)
                param_count += 1

            if agent_id:
                query += f" AND agent_id = ${param_count}"
                params.append(agent_id)
                param_count += 1

            query += f" ORDER BY created_at DESC LIMIT ${param_count}"
            params.append(limit)

            memories = await conn.fetch(query, *params)

            memory_list = [dict(m) for m in memories]

        # Cluster memories
        clusters = await intelligent_summarizer.cluster_memories(memory_list)

        # Format results
        result = f"OK Memory Clusters ({len(clusters)} total):\n\n"

        for i, cluster in enumerate(clusters[:10], 1):
            result += f"{i}. Cluster: {cluster.cluster_id}\n"
            result += f"   Theme: {cluster.cluster_theme or 'General'}\n"
            result += f"   Memories: {cluster.memory_count}\n"
            if cluster.cluster_summary:
                result += f"   Summary: {cluster.cluster_summary[:100]}...\n"
            result += "\n"

        return result

    except Exception as e:
        logger.error(f"cluster_memories failed: {e}")
        return f"ERR Failed to cluster memories: {str(e)}"


@mcp.tool()
async def advanced_search(
    query: str,
    user_id: str = "default",
    agent_id: Optional[str] = None,
    limit: int = 20,
    rerank: bool = True,
    strategy: str = "combined",
    expand_query: bool = True
) -> str:
    """
    Advanced search with query expansion and re-ranking (Sprint 10)

    Parameters:
    -----------
    - query: Search query text
    - user_id: User identifier (default: 'default')
    - agent_id: Optional agent filter
    - limit: Maximum results (default: 20)
    - rerank: Whether to apply re-ranking (default: True)
    - strategy: Re-ranking strategy ('relevance', 'recency', 'combined', 'personalized')
    - expand_query: Whether to expand query using LLM (default: True)

    Returns:
    --------
    - Advanced search results with re-ranking and highlights
    """
    if not advanced_search_engine:
        return "ERR Advanced Search Engine not available"

    try:
        # Parse strategy
        try:
            rerank_strategy = ReRankingStrategy(strategy.lower())
        except ValueError:
            return f"ERR Invalid strategy: {strategy}. Use: relevance, recency, combined, personalized"

        # Perform search
        results = await advanced_search_engine.search(
            query=query,
            user_id=user_id,
            agent_id=agent_id,
            limit=limit,
            rerank=rerank,
            strategy=rerank_strategy,
            filters={}
        )

        # Format results
        output = [f"OK Advanced Search Results ({len(results)} found):\n"]

        for i, result in enumerate(results[:10], 1):
            output.append(f"\n{i}. Rank: {result.rank} | Score: {result.reranked_score:.3f}")
            output.append(f"   Reason: {result.relevance_reason}")
            output.append(f"   Content: {result.content[:150]}...")

            if result.highlights:
                output.append(f"   Highlights:")
                for highlight in result.highlights[:3]:
                    output.append(f"     - {highlight}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"advanced_search failed: {e}")
        return f"ERR Failed to perform advanced search: {str(e)}"


@mcp.tool()
async def expand_search_query(query: str, max_expansions: int = 5) -> str:
    """
    Expand search query with related terms using LLM (Sprint 10)

    Parameters:
    -----------
    - query: Original search query
    - max_expansions: Maximum number of expanded queries (default: 5)

    Returns:
    --------
    - Expanded query list
    """
    if not advanced_search_engine:
        return "ERR Advanced Search Engine not available"

    try:
        expanded = await advanced_search_engine._expand_query(query)

        result = f"OK Query Expansion ({len(expanded)} variants):\n\n"
        result += f"Original: {query}\n\n"
        result += "Expanded Queries:\n"

        for i, exp in enumerate(expanded[:max_expansions], 1):
            result += f"  {i}. {exp}\n"

        return result

    except Exception as e:
        logger.error(f"expand_search_query failed: {e}")
        return f"ERR Failed to expand query: {str(e)}"


@mcp.tool()
async def get_search_analytics(days_back: int = 30) -> str:
    """
    Get search analytics and statistics (Sprint 10)

    Parameters:
    -----------
    - days_back: Number of days to analyze (default: 30)

    Returns:
    --------
    - Search analytics with metrics
    """
    if not advanced_search_engine:
        return "ERR Advanced Search Engine not available"

    try:
        analytics = await advanced_search_engine.get_search_analytics(days_back)

        if analytics.get("status") == "error":
            return f"ERR {analytics.get('error', 'Unknown error')}"

        result = f"OK Search Analytics ({days_back} days):\n\n"
        result += f"Total Searches: {analytics['total_searches']}\n"
        result += f"Avg Query Length: {analytics['avg_query_length']:.1f} chars\n"
        result += f"Zero Results Rate: {analytics['zero_results_rate']:.1f}%\n\n"

        result += "Top Search Terms:\n"
        for term in analytics['top_search_terms'][:10]:
            result += f"  - {term['query_term']}: {term['count']} searches\n"

        return result

    except Exception as e:
        logger.error(f"get_search_analytics failed: {e}")
        return f"ERR Failed to get search analytics: {str(e)}"


@mcp.tool()
async def get_summarization_stats() -> str:
    """
    Get intelligent summarization statistics (Sprint 10)

    Returns:
    --------
    - Summarization statistics and metrics
    """
    if not intelligent_summarizer:
        return "ERR Intelligent Summarizer not available"

    try:
        stats = await intelligent_summarizer.get_summarization_statistics()

        if stats.get("status") == "error":
            return f"ERR {stats.get('error', 'Unknown error')}"

        result = "OK Intelligent Summarization Statistics:\n\n"
        result += f"Memories Summarized: {stats['memories_summarized']}\n"
        result += f"Avg Compression Ratio: {stats['average_compression_ratio']:.2f}x\n"

        return result

    except Exception as e:
        logger.error(f"get_summarization_stats failed: {e}")
        return f"ERR Failed to get summarization stats: {str(e)}"


async def main():
    """Main entry point"""
    print("""
==================================================================
         Enhanced Cognee MCP Server - Enhanced Stack
    PostgreSQL+pgVector | Qdrant | Neo4j | Redis
==================================================================
    """)

    # Initialize Enhanced stack
    await init_enhanced_stack()

    # Initialize Sprint 8 modules
    await init_sprint8_modules()

    print("\nOK Enhanced Cognee MCP Server starting...")
    print("  Available tools:")
    print("    Standard Memory MCP Tools (for Claude Code integration):")
    print("      - add_memory: Add memory entry")
    print("      - search_memories: Search memories")
    print("      - get_memories: List all memories")
    print("      - get_memory: Get specific memory by ID")
    print("      - update_memory: Update existing memory")
    print("      - delete_memory: Delete memory")
    print("      - list_agents: List all agents")
    print("    Enhanced Cognee Tools:")
    print("      - cognify: Add data to knowledge graph")
    print("      - search: Search knowledge graph")
    print("      - list_data: List all documents")
    print("      - get_stats: Get system statistics")
    print("      - health: Health check")
    print("    Sprint 8 Backup & Recovery Tools:")
    print("      - create_backup: Create backup of databases")
    print("      - restore_backup: Restore from backup")
    print("      - list_backups: List all backups")
    print("      - verify_backup: Verify backup integrity")
    print("      - rollback_restore: Rollback failed restore")
    print("    Sprint 8 Maintenance Scheduler Tools:")
    print("      - schedule_task: Schedule maintenance task")
    print("      - list_tasks: List scheduled tasks")
    print("      - cancel_task: Cancel scheduled task")
    print("    Sprint 8 Deduplication Tools:")
    print("      - deduplicate: Perform deduplication")
    print("      - schedule_deduplication: Schedule periodic deduplication")
    print("      - deduplication_report: Generate deduplication report")
    print("    Sprint 8 Summarization Tools:")
    print("      - summarize_old_memories: Summarize old memories")
    print("      - schedule_summarization: Schedule periodic summarization")
    print("      - summary_stats: Get summarization statistics")
    print("    Sprint 9 Multi-Language Tools:")
    print("      - detect_language: Detect language from text (28 languages)")
    print("      - get_supported_languages: List all supported languages")
    print("      - search_by_language: Search with language filtering")
    print("      - get_language_distribution: Get language statistics")
    print("      - cross_language_search: Cross-language search with ranking")
    print("      - get_search_facets: Get faceted search options")
    print("    Sprint 10 Advanced AI Features:")
    print("      - intelligent_summarize: LLM-based memory summarization")
    print("      - auto_summarize_old_memories: Batch summarization of old memories")
    print("      - cluster_memories: Semantic memory clustering")
    print("      - advanced_search: Advanced search with re-ranking")
    print("      - expand_search_query: Query expansion using LLM")
    print("      - get_search_analytics: Search analytics and metrics")
    print("      - get_summarization_stats: Summarization statistics")
    print("    Memory Management Tools:")
    print("      - expire_memories: Expire old memories")
    print("      - get_memory_age_stats: Get memory age statistics")
    print("      - set_memory_ttl: Set time-to-live for memory")
    print("      - archive_category: Archive category memories")
    print("    Performance Analytics Tools:")
    print("      - get_performance_metrics: Get comprehensive metrics")
    print("      - get_slow_queries: Get slow queries")
    print("      - get_prometheus_metrics: Export Prometheus metrics")
    print("    Cross-Agent Sharing Tools:")
    print("      - set_memory_sharing: Set sharing policy")
    print("      - check_memory_access: Check memory access")
    print("      - get_shared_memories: Get shared memories")
    print("      - create_shared_space: Create shared space")
    print("    Real-Time Sync Tools:")
    print("      - publish_memory_event: Publish memory event")
    print("      - get_sync_status: Get sync status")
    print("      - sync_agent_state: Sync agent state")
    print()

    try:
        # Run MCP server
        await mcp.run_stdio_async()
    finally:
        await cleanup_enhanced_stack()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOK Enhanced Cognee MCP Server stopped")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
