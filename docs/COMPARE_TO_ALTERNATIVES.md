# Enhanced Cognee vs Alternatives

A clear-eyed comparison so first-time visitors can decide in under 30 seconds whether
Enhanced Cognee fits their use case.

## TL;DR

| If you need... | Use |
|---|---|
| Production-grade, multi-database memory layer with 122 MCP tools | **Enhanced Cognee** |
| Lightweight Cognee with single-DB setup, no enterprise features | [Cognee](https://github.com/topoteretes/cognee) (upstream) |
| Hosted memory-as-a-service with no ops burden | [Mem0](https://github.com/mem0ai/mem0) |
| Stateful agent platform with built-in workflows | [Letta (formerly MemGPT)](https://github.com/letta-ai/letta) |
| In-process Python memory for prototyping | [LangChain Memory](https://python.langchain.com/) |

## Detailed Comparison

| Feature | Enhanced Cognee | Cognee (upstream) | Mem0 | Letta | LangChain Memory |
|---|---|---|---|---|---|
| **Setup** | Docker Compose | Docker / pip | Hosted (SaaS) | Docker / pip | pip install |
| **Self-hostable** | Yes | Yes | Open-source variant | Yes | N/A |
| **MCP tools** | **122** | 0 (REST API only) | 0 | 0 | 0 |
| **Databases** | 4 (Postgres + Qdrant + Neo4j + Redis) | 1 (pick one) | Their cloud | LanceDB | Whatever you bring |
| **Knowledge graph** | Yes (Neo4j) | Yes (NetworkX/Neo4j) | No | No | No |
| **Real-time sync** | Yes (Redis pub-sub) | No | Yes | No | No |
| **Multi-language** | Yes (28 langs, auto-detect) | Yes | English-only | English-only | English-only |
| **GDPR tools** | Yes (consent, export, erasure) | No | Yes | No | No |
| **Audit log** | Yes | No | Yes (paid) | No | No |
| **Undo / redo** | Yes (3 MCP tools, 24h log) | No | No | No | No |
| **Deduplication** | Yes (auto + manual + scheduled) | Basic | Yes | No | No |
| **Summarization** | Yes (scheduled aging) | Yes | Yes | Yes | Yes (basic) |
| **Encryption at rest** | Yes (per-memory) | No | Yes (paid) | No | No |
| **Webhooks** | Yes | No | Yes | No | No |
| **Cost (self-hosted, 1 user)** | ~5 EUR/month VPS | ~5 EUR/month VPS | Free tier limited | ~5 EUR/month VPS | Free (in-process) |
| **Cost (managed)** | N/A | N/A | $19+/month | $25+/month | N/A |
| **Open source license** | Apache-2.0 | Apache-2.0 | Apache-2.0 + paid tiers | Apache-2.0 | MIT |
| **Production grade** | Yes (1727+ tests, 65%+ coverage) | Yes | Yes | Beta | No (research-ish) |
| **Python SDK** | Yes (`enhanced-cognee-client` on PyPI) | Yes | Yes | Yes | Built-in |

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
2. **Enterprise stack** (Postgres + Qdrant + Neo4j + Redis bundled) vs single-DB
3. **Real-time sync** via Redis pub-sub for multi-instance deployments
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
