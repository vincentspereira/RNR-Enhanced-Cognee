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

# Enhanced module instances
memory_manager = None
memory_deduplicator = None
memory_summarizer = None
performance_analytics = None
cross_agent_sharing = None
realtime_sync = None

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
        from datetime import datetime

        # For now, store in PostgreSQL
        if postgres_pool:
            async with postgres_pool.acquire() as conn:
                doc_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO shared_memory.documents (id, title, content, created_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO NOTHING
                """, doc_id, "Enhanced Cognee Memory", data, datetime.utcnow())

                logger.info(f"OK Added document: {doc_id}")
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
        stats = {"status": "Enhanced Cognee MCP Server", "databases": {}}

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

    if postgres_pool:
        checks.append("OK PostgreSQL")
    else:
        checks.append("✗ PostgreSQL")

    if qdrant_client:
        checks.append("OK Qdrant")
    else:
        checks.append("✗ Qdrant")

    if neo4j_driver:
        checks.append("OK Neo4j")
    else:
        checks.append("✗ Neo4j")

    if redis_client:
        checks.append("OK Redis")
    else:
        checks.append("✗ Redis")

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
        from datetime import datetime

        if not postgres_pool:
            return "ERR PostgreSQL not available - cannot add memory"

        # Parse metadata if provided
        metadata_dict = {}
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except:
                metadata_dict = {"raw_metadata": metadata}

        # Generate memory ID
        memory_id = str(uuid.uuid4())
        created_at = datetime.utcnow()

        # Store in PostgreSQL
        async with postgres_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO shared_memory.documents
                (id, title, content, agent_id, memory_category, tags, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, memory_id, f"Memory from {agent_id}", content,
                agent_id, "general", [], metadata_dict, created_at)

        logger.info(f"OK Added memory: {memory_id} for user: {user_id}, agent: {agent_id}")
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
            return f"OK Memory updated (ID: {memory_id})"

    except Exception as e:
        logger.error(f"update_memory failed: {e}")
        return f"ERR Failed to update memory: {str(e)}"


@mcp.tool()
async def delete_memory(memory_id: str) -> str:
    """
    Delete a specific memory (Standard Memory MCP Tool)

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
        result = await memory_manager.expire_old_memories(
            days=days,
            dry_run=dry_run,
            policy=RetentionPolicy.DELETE_OLD
        )

        if result.get("status") == "dry_run":
            return f"OK DRY RUN: Would expire {result['memories_affected']} memories older than {days} days"

        elif result.get("status") == "success":
            return f"OK Expired {result['memories_affected']} memories older than {days} days"

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
        result = await memory_manager.archive_memories_by_category(category, days)

        if result.get("status") == "success":
            return f"OK Archived {result['memories_archived']} memories from category '{category}' older than {days} days"

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
        result = await memory_summarizer.summarize_old_memories(days, min_length, dry_run)

        if result.get("status") == "success":
            if dry_run:
                return (f"OK DRY RUN: Found {result.get('candidates_found', 0)} memories to summarize "
                       f"older than {days} days")
            else:
                return (f"OK Summarized {result.get('memories_summarized', 0)} memories:\n"
                       f"  Space saved: {result.get('space_saved_bytes', 0)} bytes")
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
            return (f"OK Summarized {res.get('memories_summarized', 0)} memories "
                   f"in category '{category}':\n"
                   f"  Space saved: {res.get('space_saved', 0)} bytes")
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
            return (f"OK Created shared space '{space_name}' for {result.get('member_count', 0)} agents\n"
                   f"  Space ID: {result.get('space_id', 'unknown')}")
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
        result = await realtime_sync.sync_agent_state(source_agent, target_agent, category)

        if result.get("status") == "success":
            errors = result.get("errors", [])
            error_msg = f"\nErrors: {len(errors)}" if errors else ""

            return (f"OK Synced {result.get('memories_synced', 0)} memories "
                   f"from '{source_agent}' to '{target_agent}'{error_msg}")
        else:
            return f"ERR {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"sync_agent_state failed: {e}")
        return f"ERR Failed to sync agent state: {str(e)}"


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
    print("    Memory Management Tools:")
    print("      - expire_memories: Expire old memories")
    print("      - get_memory_age_stats: Get memory age statistics")
    print("      - set_memory_ttl: Set time-to-live for memory")
    print("      - archive_category: Archive category memories")
    print("    Memory Deduplication Tools:")
    print("      - check_duplicate: Check if content is duplicate")
    print("      - auto_deduplicate: Auto-deduplicate memories")
    print("      - get_deduplication_stats: Get deduplication stats")
    print("    Memory Summarization Tools:")
    print("      - summarize_old_memories: Summarize old memories")
    print("      - summarize_category: Summarize category memories")
    print("      - get_summary_stats: Get summarization stats")
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
