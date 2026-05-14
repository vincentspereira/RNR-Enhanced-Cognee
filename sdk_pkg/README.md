# Enhanced Cognee Client

Async Python client for the [Enhanced Cognee MCP server](https://github.com/vincentspereira/Enhanced-Cognee) - a production-grade knowledge-graph memory layer with 119 MCP tools.

## Install

```bash
pip install enhanced-cognee-client
```

## Quick start

```python
import asyncio
from enhanced_cognee_client import EnhancedCogneeClient

async def main():
    async with EnhancedCogneeClient(host="localhost", port=37777) as client:
        # Store a memory
        result = await client.add_memory(
            content="Enhanced Cognee has 119 MCP tools",
            user_id="default",
            agent_id="my-agent",
        )
        print(result)

        # Search memories
        hits = await client.search_memories(query="MCP tools", limit=5)
        print(hits)

        # Check health
        status = await client.health()
        print(status)

asyncio.run(main())
```

## Key features

- Async-first (httpx under the hood)
- Never raises on network errors - returns error dicts instead
- Full type annotations, PEP 561 `py.typed` marker
- 16 public methods covering all major memory, GDPR, and lifecycle operations
- Compatible with Python 3.10+

## License

Apache-2.0
