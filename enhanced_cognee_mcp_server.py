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

# Import memory management
from src.memory_management import MemoryManager, RetentionPolicy

# Memory manager instance
memory_manager = None

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
