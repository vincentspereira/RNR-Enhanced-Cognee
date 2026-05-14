# ADR-008: Python SDK as a Thin HTTP Client Over MCP REST

**Status:** Accepted
**Date:** 2026-05-14
**Deciders:** Enhanced Cognee maintainers

---

## Context

Enhanced Cognee exposes 105 tools through the MCP server. External Python
applications that want to call these tools have two options today:

1. Run the MCP protocol handshake directly, negotiating capabilities and issuing
   JSON-RPC 2.0 requests over stdin/stdout or a socket.
2. Use the REST endpoints that the MCP server exposes alongside the MCP transport.

The MCP protocol handshake is documented but non-trivial: callers must implement
capability negotiation, tool listing, and proper JSON-RPC framing. For application
developers who simply want to store and retrieve memories, this complexity is a
barrier. A Python SDK would lower that barrier.

The SDK must be:
- Usable by any Python application without requiring the MCP protocol library
- Async-first (most callers are already async using asyncio or ASGI frameworks)
- Maintainable without generated code that drifts out of sync with the server
- Thin: business logic stays in the MCP server, not the SDK

---

## Decision

Publish a Python package named enhanced-cognee-client that wraps the MCP server's
REST endpoints using httpx (async HTTP client). The SDK does not implement the MCP
protocol. It is a conventional HTTP client library.

The SDK structure:

    enhanced_cognee_client/
        client.py          # CogneeClient: main entry point
        memory.py          # MemoryAPI: add_memory, search_memories, get_memory, etc.
        search.py          # SearchAPI: search, advanced_search, cross_language_search
        graph.py           # GraphAPI: extract_graph_v2, get_graph, get_nodes
        admin.py           # AdminAPI: health, get_stats, get_prometheus_metrics
        exceptions.py      # CogneeError, RateLimitError, AuthError
        _transport.py      # Internal: httpx session, retry logic, error mapping

The main client object:

    import asyncio
    from enhanced_cognee_client import CogneeClient

    async def example():
        async with CogneeClient(base_url="http://localhost:8000") as client:
            memory_id = await client.memory.add_memory(
                content="The capital of France is Paris.",
                agent_id="geography-agent"
            )
            results = await client.memory.search_memories(
                query="capital of France",
                limit=5
            )
            print(results)

    asyncio.run(example())

Each of the 105 MCP tools is exposed as an async method with typed parameters.
Method names are identical to tool names (snake_case). Parameter names and types
are derived directly from the MCP server's tool definitions, not from a separate
schema file.

The SDK does not vendor or generate code from an OpenAPI spec. Tool signatures are
kept in sync through a test suite that calls each SDK method against a live MCP
server and asserts the expected response shape. If the server changes a tool
signature, the test fails and the SDK maintainer updates the method by hand.

Error handling:

- HTTP 422 (validation error) is raised as CogneeError with the server's message.
- HTTP 429 (rate limit) is raised as RateLimitError with retry-after metadata.
- HTTP 503 (server unavailable) triggers up to 3 retries with exponential backoff.
- All other HTTP errors are raised as CogneeError.

Authentication: the SDK passes an API key as a Bearer token in the Authorization
header if ENHANCED_COGNEE_API_KEY is set in the environment or passed to
CogneeClient. If no key is configured, the header is omitted (suitable for local
development with no auth).

---

## Consequences

**Positive**
- Application developers use familiar Python idioms (async with, await) without
  learning the MCP protocol.
- All 105 tools are callable with a single pip install enhanced-cognee-client.
- httpx is a well-maintained, production-grade HTTP client with connection pooling,
  timeout control, and retry support built in.
- The SDK has no dependency on the MCP server's source code; it talks to it over
  HTTP like any other client.
- Thin clients are easy to read and debug: each method is a small function that
  calls one endpoint.

**Negative**
- The SDK depends on the MCP server being reachable over HTTP. It cannot be used
  in the same process as the server without a running HTTP listener.
- There is no generated client: when a tool signature changes, the corresponding
  SDK method must be updated manually. The test suite catches drift, but the fix is
  still manual work.
- Synchronous callers must wrap async methods using asyncio.run() or an event loop
  adapter. A synchronous wrapper API is not provided in v1.
- If the MCP REST endpoints are not stable (versioned), any server upgrade may
  silently break the SDK. The server must version its REST API or maintain
  backward compatibility.

---

## Alternatives Considered

**Direct MCP protocol client**
Implement the full JSON-RPC 2.0 + MCP capability negotiation in the SDK. Rejected
because the handshake adds significant complexity for callers who only want to call
tool methods. The MCP protocol is designed for agent-to-server communication, not
for direct application use.

**Generated OpenAPI client (openapi-generator or datamodel-code-generator)**
Generate a Python client from the server's OpenAPI spec. Rejected because the
generated code is large, hard to read, and drifts out of sync when the server
changes unless the generation step is automated and always run before release. The
hand-written thin client is smaller, more readable, and easier to maintain.

**gRPC client with protocol buffers**
Define .proto files for all 105 tools and generate a gRPC client. Rejected because
it requires maintaining .proto definitions in addition to the MCP tool definitions,
doubles the schema surface, and adds protoc as a build dependency. HTTP + JSON is
simpler for this use case.

**Embedding the MCP server as a library**
Import the MCP server module directly and call tool functions in-process without
HTTP. Rejected because it creates a tight coupling between the SDK and the server
version, makes testing harder (the server's database connections are initialized on
import), and prevents the SDK from being used against a remote server.
