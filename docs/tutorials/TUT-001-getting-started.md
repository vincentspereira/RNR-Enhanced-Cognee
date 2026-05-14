# Tutorial 01: Getting Started with Enhanced Cognee

**Audience:** New users
**Time required:** 20 minutes
**Prerequisites:** Docker installed; see RB-001 for full setup

---

## What Is Enhanced Cognee?

Enhanced Cognee is an enterprise-grade memory server for AI agents. It gives a
language model (such as Claude) a persistent, searchable store of memories that
survives across sessions. Each memory is a piece of text -- a note, a decision, a
fact, a code snippet -- stored with metadata that makes it retrievable later.

Under the hood, four specialized databases power different aspects of memory:

- PostgreSQL stores the text and metadata with full SQL query support
- Qdrant stores vector embeddings for semantic (meaning-based) search
- Neo4j stores relationships between memory entities as a knowledge graph
- Redis caches hot memories for fast repeated access

You do not interact with these databases directly. The Enhanced Cognee MCP server
exposes all operations as simple tool calls.

---

## What Is an MCP Tool?

MCP (Model Context Protocol) is the interface between Claude and external servers.
When you call an MCP tool, you name the tool and pass parameters, and the server
returns a plain text response. All Enhanced Cognee tools return ASCII-only strings
so they work on any operating system.

---

## Step 1: Start the Databases and Server

If you have not already completed RB-001, do that first. Then:

    enhanced-cognee docker up
    enhanced-cognee start

Leave the server running in a terminal window.

---

## Step 2: Check That the Server Is Healthy

    Tool: health

Expected response:

    Enhanced Cognee Health:
    [OK] PostgreSQL
    [OK] Qdrant
    [OK] Neo4j
    [OK] Redis

If any line shows [FAIL], follow RB-002 before continuing.

---

## Step 3: Store Your First Memory

    Tool: add_memory
    Parameters:
      content: "The project uses PostgreSQL on port 25432 for primary storage."
      agent_id: "my-first-agent"

The server returns a memory ID:

    [OK] Memory stored: mem_a1b2c3d4-...

Copy the memory ID. You will use it in the next step.

---

## Step 4: Retrieve the Memory by ID

    Tool: get_memory
    Parameters:
      memory_id: "mem_a1b2c3d4-..."

Response:

    ID:        mem_a1b2c3d4-...
    Content:   The project uses PostgreSQL on port 25432 for primary storage.
    Agent:     my-first-agent
    Created:   2026-02-13T14:22:01Z
    Confidence: 1.0 (high)

---

## Step 5: Search Memories by Meaning

You do not need the ID to find a memory. Use search_memories with a natural
language phrase:

    Tool: search_memories
    Parameters:
      query: "which database handles relational storage"
      limit: 5

The server returns semantically similar memories even if the exact words differ:

    [1] mem_a1b2c3d4-...
        The project uses PostgreSQL on port 25432 for primary storage.
        Score: 0.92

---

## Step 6: View the Server Statistics

    Tool: get_stats

Response (abbreviated):

    {
      "databases": {
        "postgresql": "[OK] Connected (1 documents)",
        "qdrant":     "[OK] Connected (1 collections)",
        "neo4j":      "[OK] Connected",
        "redis":      "[OK] Connected"
      }
    }

---

## What to Read Next

- TUT-002: Memory Lifecycle Management -- setting expiry and archiving old memories
- TUT-003: Memory Versioning and Provenance -- tracking how memories change over time
- RB-003: Backup and Restore -- protecting your memory data
