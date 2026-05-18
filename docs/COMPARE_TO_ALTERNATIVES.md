# Enhanced Cognee vs Alternatives

A clear-eyed comparison so first-time visitors can decide in under 30 seconds whether
Enhanced Cognee fits their use case.

## TL;DR

| If you need... | Use |
|---|---|
| Production-grade, multi-database memory layer with 122 MCP tools | **Enhanced Cognee** |
| Lightweight Cognee with single-DB setup, no enterprise features | [Cognee](https://github.com/topoteretes/cognee) (upstream) |
| Hosted memory-as-a-service with no ops burden | [Mem0](https://github.com/mem0ai/mem0) |
| Long-term memory for chat agents with temporal knowledge graphs | [Zep](https://github.com/getzep/zep) (Apache-2.0, Go + Python SDKs) |
| Stateful agent platform with built-in workflows | [Letta (formerly MemGPT)](https://github.com/letta-ai/letta) |
| Document-corpus retrieval with memory | [LlamaIndex](https://github.com/run-llama/llama_index) |
| In-process Python memory for prototyping | [LangChain Memory](https://python.langchain.com/) |
| Pure semantic search over a vector corpus (no graph, no agents) | [Qdrant](https://github.com/qdrant/qdrant), [Weaviate](https://github.com/weaviate/weaviate), [Chroma](https://github.com/chroma-core/chroma) |

## Detailed Comparison

| Feature | Enhanced Cognee | Cognee (upstream) | Mem0 | Zep | Letta | LangChain Memory |
|---|---|---|---|---|---|---|
| **Setup** | Docker Compose + pip/uv (one-command installer) | Docker / pip | Hosted (SaaS) | Docker | Docker / pip | pip install |
| **Self-hostable** | Yes | Yes | Open-source variant | Yes (Apache-2.0) | Yes | N/A |
| **MCP tools** | **122** | 0 (REST API only) | 0 | 0 | 0 | 0 |
| **Databases** | 4 (Postgres + Qdrant + Neo4j + Valkey) | 1 (pick one) | Their cloud | Postgres + custom store | LanceDB | Whatever you bring |
| **Knowledge graph** | Yes (Neo4j) | Yes (NetworkX/Neo4j) | No | Yes (temporal graph) | No | No |
| **Real-time sync** | Yes (Valkey pub-sub, Redis-compatible) | No | Yes | Yes | No | No |
| **Multi-language** | Yes (28 langs, auto-detect) | Yes | English-only | English-only | English-only | English-only |
| **GDPR tools** | Yes (consent, export, erasure) | No | Yes | Partial | No | No |
| **Audit log** | Yes | No | Yes (paid) | Yes | No | No |
| **Undo / redo** | Yes (3 MCP tools, 24h log) | No | No | No | No | No |
| **Deduplication** | Yes (auto + manual + scheduled) | Basic | Yes | Yes | No | No |
| **Summarization** | Yes (scheduled aging) | Yes | Yes | Yes (auto + temporal) | Yes | Yes (basic) |
| **Encryption at rest** | Yes (per-memory) | No | Yes (paid) | No (DB-level only) | No | No |
| **Webhooks** | Yes | No | Yes | Yes | No | No |
| **Cost (self-hosted, 1 user)** | ~5 EUR/month VPS | ~5 EUR/month VPS | Free tier limited | ~5 EUR/month VPS | ~5 EUR/month VPS | Free (in-process) |
| **Cost (managed)** | N/A | N/A | $19+/month | $25+/month (Zep Cloud) | $25+/month | N/A |
| **Open source license** | Apache-2.0 | Apache-2.0 | Apache-2.0 + paid tiers | Apache-2.0 | Apache-2.0 | MIT |
| **Production grade** | Yes (4158 tests, 95% coverage) | Yes | Yes | Yes | Beta | No (research-ish) |
| **Python SDK** | Yes (`enhanced-cognee-client` on PyPI) | Yes | Yes | Yes (`zep-python`) | Yes | Built-in |

**Zep note:** Zep added a strong "temporal knowledge graph" memory feature in
2024 (Graphiti) which is conceptually similar to Enhanced Cognee's Neo4j layer.
The trade-off: Zep is great for chat-message memory; Enhanced Cognee is broader
(tool-call memory, code memory, multi-agent memory, MCP-native).

**LlamaIndex note:** Not included in the table because it's primarily a
retrieval framework, not a memory layer. If you need RAG over a static corpus,
use LlamaIndex; if you need agent memory that grows over time, use Enhanced
Cognee (or one of the others above).

## When Enhanced Cognee is the right choice

- You want **all 4 storage tiers** (relational + vector + graph + cache) without
  cobbling them together yourself.
- You need **MCP tool access** from Claude Code, Cursor, Copilot, or any other
  MCP-compatible IDE — without writing a custom server.
- You're running an **agent fleet** (trading bot, SDLC agent, analysis agent) and
  need per-agent memory segregation, cross-agent sharing, and audit trails.
- You care about **GDPR compliance** (the right to erasure, consent records,
  tenant isolation) out of the box.
- You want **self-hostable, free-software** infrastructure without vendor lock-in.

## When Enhanced Cognee is NOT the right choice

- You want a **single Python import** and an in-process dict — use LangChain Memory.
- You don't want to run Docker at all — use Mem0's hosted SaaS.
- You need **just** semantic search over a static document corpus — use Qdrant directly.
- You need **stateful agents with built-in workflow orchestration** — try Letta.
- Your use case is **research / experimentation** where production-grade is overkill.

## What Enhanced Cognee adds over upstream Cognee

The upstream `topoteretes/cognee` is the foundation. Enhanced Cognee adds:

1. **122 MCP tools** vs upstream's REST-only API
2. **Enterprise stack** (Postgres + Qdrant + Neo4j + Valkey bundled) vs single-DB
3. **Real-time sync** via Valkey pub-sub (Redis protocol-compatible) for multi-instance deployments
4. **Multi-language support** (28 languages with auto-detection)
5. **Built-in GDPR tools** (consent, export, erasure, tenant verification)
6. **Audit logging** of every tool call
7. **Undo/redo** with 24h rolling log
8. **Auto-summarization + deduplication scheduling** (cron-style policies)
9. **Encryption at rest** (per-memory)
10. **Webhook + notification channels** (Slack, Discord, email)
11. **Importance scoring** + re-ranking for search results
12. **Knowledge graph compaction** for long-running deployments
13. **122 vs 0** ready-to-use MCP tools

See [COGNEE_VS_ENHANCED_MCP_COMPARISON.md](../COGNEE_VS_ENHANCED_MCP_COMPARISON.md)
for a full feature-by-feature mapping (including the 21M / 45A / 56S trigger
classification of every tool).

## Cost over time (self-hosted, 1 user)

| Month | Enhanced Cognee | Mem0 (Pro) | Letta (Cloud) |
|---|---|---|---|
| Month 1 | ~5 EUR (VPS) | $19 | $25 |
| Month 12 | ~60 EUR/year | $228/year | $300/year |
| Month 24 | ~120 EUR/year | $456/year | $600/year |

For a single developer running Claude Code with personal memory, Enhanced Cognee
self-hosted is the most cost-effective option after month 3.

## Migration paths

| From | To Enhanced Cognee | Notes |
|---|---|---|
| Cognee (upstream) | Direct migration | All data formats compatible; add the 4-DB stack |
| Mem0 | Use `cognify(data=...)` for each memory | Manual but straightforward |
| LangChain Memory | Iterate + add_memory() | One-time script; preserve agent_id |
| In-house solution | Use `mcp_memory_tools.add_memory()` in bulk | Match your schema to Enhanced Cognee's |
