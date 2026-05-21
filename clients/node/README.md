# Enhanced Cognee Node.js Client

Official Node.js / TypeScript client for the [Enhanced Cognee](https://github.com/vincentspereira/Enhanced-Cognee) MCP HTTP server.

## Install

```bash
npm install @enhanced-cognee/client
```

## Quick start

```typescript
import { EnhancedCogneeClient } from "@enhanced-cognee/client";

const cli = new EnhancedCogneeClient({
  baseUrl: "http://localhost:8000",  // optional, defaults to ENHANCED_COGNEE_URL
  apiKey: process.env.ENHANCED_API_KEY,  // optional, only if server has auth enabled
  tenantId: "acme",  // optional, for multi-tenant deployments
});

// Add a memory
const { id } = await cli.addMemory({
  content: "We use OAuth 2.0 for external services",
  agentId: "code-reviewer",
  memoryCategory: "engineering",
});

// Search memories
const { results, count } = await cli.searchMemory({
  query: "authentication strategy",
  limit: 5,
});

// Get memory stats
const stats = await cli.getStats();

// Health check
const health = await cli.getHealth();
```

## API

| Method | HTTP endpoint | Description |
| --- | --- | --- |
| `addMemory(entry)` | POST `/memory/add` | Store a memory entry |
| `searchMemory(query)` | POST `/memory/search` | Vector + text search |
| `addKnowledgeRelation(relation)` | POST `/knowledge/add_relation` | Add a graph edge |
| `getStats()` | GET `/stats` | Memory store statistics |
| `getHealth()` | GET `/health` | Stack health snapshot |

All methods accept camelCase TypeScript-idiomatic input and the client automatically converts to the snake_case JSON the server expects.

## Auth + multi-tenancy

- `apiKey` is sent as `X-API-Key` header (used when the MCP server has `ENHANCED_API_KEY` set; see `src/mcp_security.py`)
- `tenantId` is sent as `X-Tenant-ID` header (used when the MCP server has multi-tenant routing enabled; see `src/multi_tenant.py`)

Both can be passed in the constructor or via env vars (`ENHANCED_API_KEY`, `ENHANCED_TENANT_ID`).

## Error handling

```typescript
import { EnhancedCogneeError } from "@enhanced-cognee/client";

try {
  await cli.addMemory({ content: "", agentId: "x", memoryCategory: "y" });
} catch (err) {
  if (err instanceof EnhancedCogneeError) {
    console.error(`HTTP ${err.status}: ${err.body}`);
  }
}
```

## License

Apache-2.0. See [LICENSE](../../LICENSE).
