# Enhanced Cognee Rust Client

Official Rust client for the [Enhanced Cognee](https://github.com/vincentspereira/Enhanced-Cognee) MCP HTTP server.

## Install

```toml
[dependencies]
enhanced-cognee-client = "1.0"
tokio = { version = "1", features = ["macros", "rt-multi-thread"] }
```

## Quick start

```rust
use enhanced_cognee_client::{Client, MemoryEntry, SearchQuery};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Client::builder()
        .base_url("http://localhost:8000")
        .api_key(std::env::var("ENHANCED_API_KEY").ok())  // optional
        .tenant_id(Some("acme".into()))                    // optional
        .build()?;

    let id = cli.add_memory(&MemoryEntry {
        content: "We use OAuth 2.0 for external services".into(),
        agent_id: "code-reviewer".into(),
        memory_category: "engineering".into(),
        ..Default::default()
    }).await?;

    println!("Stored memory: {}", id);

    let resp = cli.search_memory(&SearchQuery {
        query: "authentication strategy".into(),
        limit: Some(5),
        ..Default::default()
    }).await?;
    println!("Found {} results", resp.count);

    Ok(())
}
```

## API

| Method | HTTP endpoint | Description |
| --- | --- | --- |
| `add_memory(&entry)` | POST `/memory/add` | Store a memory entry |
| `search_memory(&query)` | POST `/memory/search` | Vector + text search |
| `add_knowledge_relation(&relation)` | POST `/knowledge/add_relation` | Add a graph edge |
| `get_stats()` | GET `/stats` | Memory store statistics |
| `get_health()` | GET `/health` | Stack health snapshot |

All methods are `async` and use `tokio` + `reqwest` (rustls-tls for no-openssl builds).

## Auth + multi-tenancy

- `api_key` is sent as `X-API-Key` header
- `tenant_id` is sent as `X-Tenant-ID` header

Both default from env vars (`ENHANCED_API_KEY`, `ENHANCED_TENANT_ID`).

## Error handling

```rust
use enhanced_cognee_client::Error;

match cli.add_memory(&entry).await {
    Err(Error::Http { status, body }) => {
        eprintln!("HTTP {}: {}", status, body);
    }
    Err(e) => eprintln!("other: {}", e),
    Ok(id) => println!("ok: {}", id),
}
```

## License

Apache-2.0. See [LICENSE](../../LICENSE).
