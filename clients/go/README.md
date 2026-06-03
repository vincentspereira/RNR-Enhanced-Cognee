# Enhanced Cognee Go Client

Official Go client for the [Enhanced Cognee](https://github.com/vincentspereira/Enhanced-Cognee) MCP HTTP server.

## Install

```bash
go get github.com/vincentspereira/Enhanced-Cognee/clients/go
```

## Quick start

```go
package main

import (
    "context"
    "log"
    "os"

    enhancedcognee "github.com/vincentspereira/Enhanced-Cognee/clients/go"
)

func main() {
    cli, err := enhancedcognee.NewClient(enhancedcognee.Options{
        BaseURL:  "http://localhost:8080",
        APIKey:   os.Getenv("ENHANCED_API_KEY"),  // optional
        TenantID: "acme",                          // optional
    })
    if err != nil {
        log.Fatal(err)
    }

    id, err := cli.AddMemory(context.Background(), &enhancedcognee.MemoryEntry{
        Content:        "We use OAuth 2.0 for external services",
        AgentID:        "code-reviewer",
        MemoryCategory: "engineering",
    })
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Memory id: %s", id)

    resp, err := cli.SearchMemory(context.Background(), &enhancedcognee.SearchQuery{
        Query: "authentication strategy",
        Limit: 5,
    })
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Found %d results", resp.Count)
}
```

## API

| Method | HTTP endpoint | Description |
| --- | --- | --- |
| `AddMemory(ctx, entry)` | POST `/memory/add` | Store a memory entry |
| `SearchMemory(ctx, query)` | POST `/memory/search` | Vector + text search |
| `AddKnowledgeRelation(ctx, relation)` | POST `/knowledge/add_relation` | Add a graph edge |
| `GetStats(ctx)` | GET `/stats` | Memory store statistics |
| `GetHealth(ctx)` | GET `/health` | Stack health snapshot |

All methods take a `context.Context` as first arg so callers can apply per-request timeouts and cancellation.

## Auth + multi-tenancy

- `APIKey` is sent as `X-API-Key` header
- `TenantID` is sent as `X-Tenant-ID` header

Both can be passed in `Options` or via env vars (`ENHANCED_API_KEY`, `ENHANCED_TENANT_ID`).

## Error handling

```go
if err != nil {
    if enhancedcognee.IsHTTPError(err) {
        var httpErr *enhancedcognee.Error
        errors.As(err, &httpErr)
        log.Printf("HTTP %d: %s", httpErr.Status, httpErr.Body)
    }
}
```

## License

Apache-2.0. See [LICENSE](../../LICENSE).
