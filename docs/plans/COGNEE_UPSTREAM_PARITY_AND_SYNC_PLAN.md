# Cognee Upstream Parity and Automated Sync Plan

**Document Status:** DRAFT - AWAITING USER APPROVAL
**Author:** Claude (Anthropic) for Vincent S. Pereira
**Date:** 2026-05-13
**Plan Version:** 1.0
**Target Repositories:**

- Upstream: [topoteretes/cognee](https://github.com/topoteretes/cognee) (Original)
- Local: `C:\Users\vince\Projects\AI Agents\RNR Enhanced Cognee` (Enhanced)

---

## 0. How to Read This Plan

This plan answers seven things, in order:

1. Where RNR Enhanced Cognee stands today vs Original Cognee (the gap)
2. What is the same in both
3. What is different
4. What is unique to each
5. What we must port FROM Original TO Enhanced (with priorities)
6. What in Enhanced needs upgrading / hardening
7. How to keep Enhanced in sync going forward, automatically and safely

Each section ends with concrete deliverables. No work is performed until you (Vincent) approve this plan in writing.

---

## 1. Executive Summary

### 1.1 Headline Findings

| Metric                    | Original Cognee                 | RNR Enhanced Cognee                     | Gap                                 |
| ------------------------- | ------------------------------- | ----------------------------------- | ----------------------------------- |
| Current stable version    | `v1.0.9`                        | `v0.5.1`                            | ~14 minor + 1 major releases behind |
| Latest dev release        | `v1.1.0.dev0` (2026-05-12)      | n/a                                 | n/a                                 |
| MCP server tools          | ~12 (focused)                   | ~58 (broad)                         | Enhanced wins in breadth            |
| Primary memory stack      | LanceDB + Kuzu/Ladybug + SQLite | PostgreSQL + Qdrant + Neo4j + Redis | Enhanced wins in scale              |
| Cloud/SaaS support        | Yes (`cognee.serve()`)          | No                                  | Enhanced lacks this                 |
| API endpoints (`api/v1/`) | 26 routers                      | 17 routers                          | Enhanced is missing 9+              |
| Recent feature velocity   | ~6 releases / 2 months          | Frozen at 0.5.1                     | Significant drift risk              |

### 1.2 What This Plan Will Deliver

- A **prioritized backlog** of features to port from Original to Enhanced (P0/P1/P2/P3)
- A **hardening pass** for every feature unique to Enhanced
- An **automated upstream-sync pipeline** (GitHub Actions + Python) that:
  - Detects new Original releases
  - Generates a comparison diff
  - Files a PR with porting candidates
  - Runs the Enhanced test suite to catch regressions
- A **risk register** with rollback paths for every change class
- **Approval gates** so nothing destructive happens without your sign-off

### 1.3 Scope of Work (Total Estimate)

| Phase                            | Effort         | Calendar Time | Risk   |
| -------------------------------- | -------------- | ------------- | ------ |
| Phase 0: Pre-flight              | 1 day          | 1 day         | Low    |
| Phase 1: Critical parity (P0)    | 8-10 days      | 2 weeks       | Medium |
| Phase 2: High-value ports (P1)   | 6-8 days       | 1.5 weeks     | Medium |
| Phase 3: Nice-to-have ports (P2) | 4-6 days       | 1 week        | Low    |
| Phase 4: Enhanced hardening      | 5-7 days       | 1.5 weeks     | Medium |
| Phase 5: Automation pipeline     | 3-4 days       | 1 week        | Low    |
| Phase 6: Documentation & rollout | 2 days         | 0.5 week      | Low    |
| **TOTAL**                        | **29-37 days** | **~8 weeks**  | -      |

Note: Estimates assume one developer (or one Claude session per task) and exclude QA cycles for stakeholders.

---

## 2. Methodology

### 2.1 How I Compared the Two Repositories

I used four signals, in order:

1. **Version metadata** - `pyproject.toml`, `cognee/version.py`, GitHub `/releases` API
2. **Directory structure** - tree of `cognee/`, `cognee-mcp/`, `cognee-frontend/`, `examples/`, `evals/`, `distributed/`, `deployment/`, `notebooks/` in both repos
3. **MCP tool surface** - `@mcp.tool()` decorators in `cognee-mcp/src/server.py` (Original) vs `bin/enhanced_cognee_mcp_server.py` (Enhanced)
4. **Release notes** - last 10 Original releases (`v1.0.2` through `v1.1.0.dev0`)

### 2.2 Sources Verified

| Source                | Where                                               | Used For              |
| --------------------- | --------------------------------------------------- | --------------------- |
| Original GitHub repo  | `topoteretes/cognee`                                | Structure + content   |
| Original release feed | `gh api /repos/topoteretes/cognee/releases`         | Recent feature deltas |
| Local Enhanced repo   | `C:\Users\vince\Projects\AI Agents\RNR Enhanced Cognee` | Current state         |
| Local cognee fork     | `enhanced-cognee/cognee/`                           | Frozen base (v0.5.1)  |
| Enhanced MCP server   | `bin/enhanced_cognee_mcp_server.py` (4088 lines)    | Tool inventory        |
| Original MCP server   | `cognee-mcp/src/server.py` (current)                | Tool inventory        |
| Enhanced custom src   | `src/*.py` (46 modules)                             | Unique features       |

### 2.3 What I Did Not Inspect (Disclosed Gaps)

- Original `cognee-frontend/` source (Next.js app) - inventoried at top level only
- `evals/` benchmarks - Original has expanded these in v1.0.4+
- Detailed runtime behavior - this plan is structural, not behavioural

These gaps will be closed during Phase 0 pre-flight (Section 9.1).

---

## 3. Version & Gap Analysis

### 3.1 Version Drift

- **RNR Enhanced Cognee** (`pyproject.toml` at repo root): `version = "0.5.1"`
- **Original Cognee** (`pyproject.toml` on `master`): `version = "1.0.1"`
- **Latest stable release** on GitHub: `v1.0.9` (2026-05-08)
- **Latest dev release**: `v1.1.0.dev0` (2026-05-12)

### 3.2 Release Cadence of Original

| Release       | Date       | Headline                                                                  |
| ------------- | ---------- | ------------------------------------------------------------------------- |
| `v1.1.0.dev0` | 2026-05-12 | Memory export/import, advanced search filters, preview pane               |
| `v1.0.9`      | 2026-05-08 | Bulk actions, one-click export, JSON exports                              |
| `v1.0.8`      | 2026-05-06 | Memory snapshots, scheduled backups (UI) - **mandatory schema migration** |
| `v1.0.7`      | 2026-05-05 | Sync engine, search relevance, bulk actions, file upload resume           |
| `v1.0.6`      | 2026-05-05 | Export options, context preview in composer, bulk actions                 |
| `v1.0.5`      | 2026-05-03 | CLI `--dry-run`, tag-based grouping, webhook retry/backoff                |
| `v1.0.4`      | 2026-05-03 | **Replaced Kuzu with Ladybug**, frequency weights, MCP hardening          |
| `v1.0.4.dev0` | 2026-04-25 | **GraphSkills + Agentic integration**, config key rename (breaking)       |
| `v1.0.3`      | 2026-04-24 | Search ranking, deduplication, session trimming                           |
| `v1.0.2`      | 2026-04-22 | Sync resilience, quick-capture shortcut, attachment preview               |

**Key implication:** Original is shipping ~3 releases/week. Without automation, Enhanced will drift further every month.

### 3.3 What "Behind" Concretely Means

| Class                  | Items                                                                                                                                                                  | Severity                                            |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| API endpoints missing  | `forget`, `improve`, `recall`, `remember`, `serve`, `session`, `activity`, `api_keys`, `llm` routers                                                                   | **High** - core surface area gap                    |
| Modules missing        | `agent_memory/`, modern `pipelines/layers/`, `cloud/` operations                                                                                                       | **High**                                            |
| Tasks missing          | `translation/`, `cleanup/`, modern `codingagents/`                                                                                                                     | Medium                                              |
| Infrastructure missing | `databases/hybrid/`, `databases/unified/`, `databases/dataset_database_handler/`, `infrastructure/session/`, `loaders/` system                                         | **High**                                            |
| Retrievers missing     | `temporal_retriever`, `jaccard_retrieval`, `lexical_retriever`, `natural_language_retriever`, `summaries_retriever`, decomposition retriever, `coding_rules_retriever` | Medium                                              |
| Search types missing   | `FEELING_LUCKY` (auto-select), `CYPHER`, `TEMPORAL`, `GRAPH_COMPLETION_COT`                                                                                            | Medium                                              |
| Graph backend          | Original switched Kuzu -> Ladybug in v1.0.4                                                                                                                            | Medium (Enhanced uses Neo4j so impact is contained) |
| Cloud connectivity     | `cognee.serve()` + `--serve-url` MCP arg                                                                                                                               | Low (Enhanced is self-hosted-first)                 |
| Coding agent rules     | `cognee/tasks/codingagents/` rule associations                                                                                                                         | Medium (useful for Claude/Cursor)                   |
| Session memory         | `infrastructure/session/feedback_detection.py` + session-aware MCP tools                                                                                               | Medium                                              |
| MCP transport security | Original has TransportSecuritySettings + CORS + DNS-rebinding protection                                                                                               | **High** (security)                                 |
| MCP transport options  | Original supports `stdio`, `sse`, `http` with arguments                                                                                                                | Medium                                              |

---

## 4. Similarities (Common Ground)

Both repositories share the following:

### 4.1 Core Concepts

- **Knowledge-graph-first memory model**: text -> chunks -> entities -> graph + embeddings
- **Pipeline-based ingestion**: classify -> chunk -> extract graph -> summarise -> persist
- **MCP server interface**: both expose tools via `FastMCP`
- **Multi-database approach**: relational + vector + graph
- **Async-first Python**: SQLAlchemy 2.x async, `asyncio`, `aiohttp`

### 4.2 Identical / Near-Identical Files

(Verified by directory structure, not byte-level)

- `cognee/base_config.py`, `cognee/version.py`, `cognee/root_dir.py`
- `cognee/api/DTO.py`, `cognee/api/client.py`
- `cognee/cli/` structure
- `cognee/exceptions/`
- `cognee/shared/` (utilities)
- `cognee/infrastructure/llm/` (LLM gateway, tokenizers)
- `cognee/modules/users/` (FastAPI Users-based auth)
- `cognee/modules/chunking/` (Chunker, CsvChunker, TextChunker)
- `cognee/modules/observability/` (tracing)
- `cognee/modules/ontology/` (RDF resolver)
- `cognee/eval_framework/` (benchmarking)
- `cognee/modules/data/` (Dataset model, methods)
- `cognee/infrastructure/databases/vector/` (LanceDB, ChromaDB, Qdrant, pgvector adapters)

### 4.3 Shared APIs

- `cognify()` - data -> knowledge graph
- `search()` - knowledge graph query
- `add()` - ingest data
- `delete()` - delete data
- `prune()` - reset everything

### 4.4 Shared MCP Tools

| Tool        | Original | Enhanced                            |
| ----------- | -------- | ----------------------------------- |
| `cognify`   | Yes      | Yes                                 |
| `search`    | Yes      | Yes                                 |
| `list_data` | Yes      | Yes                                 |
| `delete`    | Yes      | Yes (as `delete_memory`)            |
| `prune`     | Yes      | No (uses `forget_memory` semantics) |

---

## 5. Differences (Where They Diverge)

### 5.1 Architectural Philosophy

| Dimension           | Original                                                         | Enhanced                                                              |
| ------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------- |
| Target deployment   | Library + SaaS cloud                                             | Enterprise self-hosted stack                                          |
| Default stack       | LanceDB + Kuzu/Ladybug + SQLite                                  | PostgreSQL + Qdrant + Neo4j + Redis                                   |
| MCP tool philosophy | Few high-level verbs (`remember`, `recall`, `forget`, `improve`) | Many specialised verbs (one per operation)                            |
| Multi-tenancy       | Per-user via fastapi-users                                       | Per-user + multi-tenant module (`src/multi_tenant/`)                  |
| Security model      | App-level authentication                                         | App-level + MCP-level validation (`src/security_mcp.py`)              |
| Categorisation      | Tags & datasets                                                  | Dynamic categories (config-driven via `.enhanced-cognee-config.json`) |
| Backup/restore      | Snapshot UI (v1.0.8+)                                            | Full backup manager + verifier + rollback                             |
| Monitoring          | Sentry + Langfuse (optional)                                     | Prometheus metrics + custom analytics                                 |
| Cloud connectivity  | First-class (`cognee.serve()`)                                   | None                                                                  |
| Distributed compute | `modal` integration in `distributed/`                            | Same `distributed/` folder (frozen at 0.5.1 state)                    |

### 5.2 MCP Server Differences

| Capability                         | Original (`cognee-mcp/src/server.py`)       | Enhanced (`bin/enhanced_cognee_mcp_server.py`) |
| ---------------------------------- | ------------------------------------------- | ---------------------------------------------- |
| Transport: stdio                   | Yes                                         | Yes                                            |
| Transport: SSE                     | Yes                                         | No                                             |
| Transport: streamable HTTP         | Yes                                         | No                                             |
| Transport security (DNS rebinding) | Yes                                         | No                                             |
| CORS middleware                    | Yes                                         | No                                             |
| Cloud mode (`--serve-url`)         | Yes                                         | No                                             |
| API mode (`--api-url`)             | Yes                                         | No                                             |
| Session-aware memory ops           | Yes (`remember`/`recall` with `session_id`) | No                                             |
| Custom graph models via file path  | Yes                                         | No                                             |
| Background-task error tracking     | Yes (`_task_errors`)                        | Partial                                        |
| Health endpoint                    | `/health` HTTP route                        | `health()` MCP tool                            |
| Lines of code                      | ~700 (focused)                              | 4088 (broad)                                   |
| Test coverage                      | Has explicit tests                          | Mixed                                          |

### 5.3 Search Type Differences

| Search Type                          | Original                              | Enhanced                                                            |
| ------------------------------------ | ------------------------------------- | ------------------------------------------------------------------- |
| `GRAPH_COMPLETION`                   | Yes                                   | Partial (delegates to PG ILIKE)                                     |
| `GRAPH_COMPLETION_COT`               | Yes (chain-of-thought)                | No                                                                  |
| `GRAPH_COMPLETION_DECOMPOSITION`     | Yes                                   | No                                                                  |
| `GRAPH_COMPLETION_CONTEXT_EXTENSION` | Yes                                   | No                                                                  |
| `GRAPH_SUMMARY_COMPLETION`           | Yes                                   | No                                                                  |
| `RAG_COMPLETION`                     | Yes                                   | No                                                                  |
| `CHUNKS`                             | Yes                                   | No (returns docs only)                                              |
| `SUMMARIES`                          | Yes (hierarchical)                    | Yes (different impl)                                                |
| `CODE`                               | Yes (with code-aware)                 | No                                                                  |
| `CYPHER`                             | Yes                                   | No                                                                  |
| `TEMPORAL`                           | Yes (v1.0.4+)                         | No                                                                  |
| `FEELING_LUCKY`                      | Yes (auto-select)                     | No                                                                  |
| `INSIGHTS`                           | Yes (legacy)                          | No                                                                  |
| Vector similarity                    | Via lancedb/qdrant adapters           | Qdrant only                                                         |
| Lexical / BM25                       | Yes (`lexical_retriever.py`)          | No                                                                  |
| Jaccard                              | Yes (`jaccard_retrival.py`)           | No                                                                  |
| Natural language router              | Yes (`natural_language_retriever.py`) | No                                                                  |
| Query expansion                      | No                                    | Yes (`expand_search_query`) - Enhanced-only                         |
| Multi-language search                | No                                    | Yes (`search_by_language`, `cross_language_search`) - Enhanced-only |
| Search reranking                     | No                                    | Yes (`advanced_search` with strategies) - Enhanced-only             |

### 5.4 Stack & Configuration Differences

| Setting              | Original     | Enhanced                                           |
| -------------------- | ------------ | -------------------------------------------------- |
| PostgreSQL port      | 5432         | 25432                                              |
| Qdrant port          | 6333         | 26333                                              |
| Neo4j port           | 7687         | 27687                                              |
| Redis port           | 6379         | 26379                                              |
| Default graph DB     | Kuzu/Ladybug | Neo4j                                              |
| Default vector DB    | LanceDB      | Qdrant                                             |
| Default relational   | SQLite       | PostgreSQL + pgvector                              |
| ASCII-only output    | No           | **Yes (mandatory)**                                |
| Hardcoded categories | Tags only    | Dynamic via config (**must never be ATS/OMA/SMC**) |

---

## 6. Unique Features

### 6.1 Unique to Original Cognee (Not in Enhanced)

These are features Original has shipped that Enhanced does not yet have.

#### 6.1.1 API Endpoints (`cognee/api/v1/`)

- `activity/` - activity tracking router
- `api_keys/` - API key CRUD
- `forget/` - structured forget endpoint with `graph_only` option
- `improve/` - graph enrichment + session bridging
- `llm/` - LLM provider configuration router
- `recall/` - smart recall with `query_router.py` (auto-routes search type)
- `remember/` - permanent + session memory storage
- `serve/` - cloud connectivity (`cloud_client.py`, `device_auth.py`, `credentials.py`)
- `session/` - session management for conversational memory

#### 6.1.2 Modules

- `cognee/modules/agent_memory/` - decorator + runtime + models for agent memory injection
- `cognee/modules/cloud/` - cloud sync exceptions + operations
- `cognee/modules/sync/methods/` + `models/SyncOperation.py` - persistent sync operation tracking
- `cognee/modules/memify/memify.py` - memory enrichment pipeline
- `cognee/modules/pipelines/layers/` - pipeline execution mode (background vs blocking)
- `cognee/modules/pipelines/queues/` - pipeline queue management
- `cognee/modules/pipelines/exceptions/` - typed pipeline exceptions
- `cognee/modules/data/processing/` - data processing operations
- `cognee/modules/data/deletion/` - structured deletion logic
- `cognee/modules/data/methods/get_last_added_data.py` - recent-data lookups

#### 6.1.3 Tasks

- `cognee/tasks/cleanup/cleanup_unused_data.py` - data hygiene
- `cognee/tasks/translation/` - multi-language translation (Azure, Google, LLM providers) [Note: Enhanced has its own multi-language stack in `src/`]
- `cognee/tasks/codingagents/coding_rule_associations.py` - associates session interactions to coding rules (used by IDE agents)
- `cognee/tasks/entity_completion/entity_extractors/` - regex + LLM entity extractors
- `cognee/tasks/graph/cascade_extract/` - cascade graph extraction with prompts
- `cognee/tasks/graph/extract_graph_from_data_v2.py` - newer graph extraction
- `cognee/tasks/memify/apply_feedback_weights.py` - feedback-driven weighting
- `cognee/tasks/memify/cognify_session.py` - session -> permanent graph bridge
- `cognee/tasks/memify/extract_feedback_qas.py` - QA pair extraction
- `cognee/tasks/memify/extract_user_sessions.py` - user session extraction
- `cognee/tasks/memify/sync_graph_to_session.py` - reverse-sync graph to session
- `cognee/tasks/temporal_graph/enrich_events.py` - temporal enrichment
- `cognee/tasks/temporal_graph/add_entities_to_event.py` - event entity linking

#### 6.1.4 Infrastructure

- `cognee/infrastructure/databases/hybrid/neptune_analytics/` - AWS Neptune Analytics hybrid adapter
- `cognee/infrastructure/databases/hybrid/postgres/` - PostgreSQL hybrid (graph + vector in one DB)
- `cognee/infrastructure/databases/unified/` - unified store engine + capabilities API
- `cognee/infrastructure/databases/dataset_database_handler/` - dynamic per-dataset DB routing
- `cognee/infrastructure/databases/cache/` - Redis + filesystem cache layer
- `cognee/infrastructure/loaders/` - **full loader system** (audio, csv, image, text, PDF, docling, unstructured, beautifulsoup)
- `cognee/infrastructure/session/feedback_detection.py` - inferred user feedback from session
- `cognee/infrastructure/llm/structured_output_framework/baml/` - BAML structured outputs
- `cognee/infrastructure/llm/extraction/extract_event_entities.py` - event-aware entity extraction

#### 6.1.5 Retrievers (`cognee/modules/retrieval/`)

- `temporal_retriever.py` - time-aware retrieval
- `jaccard_retrival.py` - Jaccard similarity
- `lexical_retriever.py` - BM25-style lexical search
- `natural_language_retriever.py` - NL -> Cypher router
- `summaries_retriever.py` - summary hierarchy retrieval
- `coding_rules_retriever.py` - retrieve coding rules
- `graph_completion_decomposition_retriever.py` - decomposes complex queries
- `graph_completion_cot_retriever.py` - chain-of-thought
- `graph_completion_context_extension_retriever.py` - context expansion
- `graph_summary_completion_retriever.py` - summary-driven completion
- `register_retriever.py` + `registered_community_retrievers.py` - plugin registry for retrievers
- `utils/access_tracking.py` - retrieval-time access logs
- `utils/query_decomposition.py` - query splitting
- `utils/query_state.py` - per-query mutable state
- `utils/stop_words.py` - stop-word filtering

#### 6.1.6 Pipelines & Custom Pipelines

- `cognee/modules/run_custom_pipeline/run_custom_pipeline.py` - user-defined pipelines
- `cognee/memify_pipelines/` - top-level memify pipelines
- Pipeline executor modes (background / blocking) via `pipeline_execution_mode.py`

#### 6.1.7 MCP Server Features

- **Transport options**: stdio (default), SSE, streamable HTTP
- **Transport security**: DNS rebinding protection, configurable allowed hosts
- **CORS middleware**: for SSE/HTTP transports
- **Cloud connectivity**: `--serve-url`, `--serve-api-key`, `COGNEE_SERVICE_URL`, `COGNEE_API_KEY`
- **API mode**: `--api-url`, `--api-token` to delegate to a remote FastAPI server
- **Health endpoint**: `/health` HTTP route in addition to `health` tool
- **Background-task error tracking**: stores per-dataset errors so `cognify_status` can report them
- **Custom graph models**: pass `graph_model_file` and `graph_model_name` to `cognify`
- **`save_interaction` tool**: stores user-agent interactions and generates coding rule associations
- **`remember` tool** (modern, session-aware)
- **`recall` tool** (auto-routing, session-first)
- **`forget_memory` tool** (dataset-scoped or everything)
- **`improve` tool** (4-stage pipeline: feedback weights -> session-to-graph -> triplet enrichment -> graph-to-session)
- **`cognify_status` tool** with background error reporting

#### 6.1.8 Recent Release Features (v1.0.2 - v1.1.0.dev0)

- **GraphSkills** - agents can discover and invoke graph-based skills (v1.0.4.dev0)
- **Memory export/import** - JSON/CSV with one-click download (v1.0.5+)
- **Memory snapshots** - on-demand point-in-time snapshots (v1.0.8)
- **Scheduled backups (UI)** - automatic backups configurable from web UI (v1.0.8)
- **Bulk actions** - select multiple memories to tag/delete/export (v1.0.7+)
- **Advanced search filters** - date range, source, tags (v1.1.0.dev0)
- **Memory preview pane** - context + metadata without leaving list view (v1.1.0.dev0)
- **CLI `--dry-run` flag** - validate exports before running (v1.0.5)
- **Tag-based grouping** - view + export grouped by tags (v1.0.5)
- **Webhook retry/backoff** - transient error resilience (v1.0.5)
- **Quick-capture keyboard shortcut** - global capture modal (v1.0.2)
- **Attachment preview** - inline image/document rendering (v1.0.2)
- **Ladybug graph database** - replaces Kuzu (v1.0.4)
- **Frequency weights** - Kuzu/Ladybug adapter + session API support (v1.0.4)
- **`run_in_background` for add router** (v1.0.4)
- **`graph_only` option for forget endpoint** (v1.0.4)
- **Markdown-wrapped JSON in infer-schema endpoint** (v1.0.4)

### 6.2 Unique to RNR Enhanced Cognee (Not in Original)

These are features Enhanced has built on top that Original does not have.

#### 6.2.1 Enterprise Memory Stack

- **PostgreSQL + pgvector** (port 25432) as primary store
- **Qdrant** (port 26333) for high-performance vectors
- **Neo4j** (port 27687) for graph
- **Redis** (port 26379) for cache + pub-sub
- **Docker compose** orchestration (`docker/docker-compose-enhanced-cognee.yml`)

#### 6.2.2 Custom MCP Tools (~58, all in `bin/enhanced_cognee_mcp_server.py`)

**Standard memory verbs:**

- `add_memory`, `search_memories`, `get_memories`, `get_memory`, `update_memory`, `delete_memory`, `list_agents`

**Lifecycle & retention:**

- `expire_memories`, `get_memory_age_stats`, `set_memory_ttl`, `archive_category`

**Deduplication:**

- `check_duplicate`, `auto_deduplicate`, `get_deduplication_stats`, `deduplicate`, `schedule_deduplication`, `deduplication_report`

**Summarization:**

- `summarize_category`, `summarize_old_memories`, `schedule_summarization`, `summary_stats`, `intelligent_summarize`, `auto_summarize_old_memories`, `cluster_memories`, `get_summary_stats`, `get_summarization_stats`

**Performance & analytics:**

- `get_performance_metrics`, `get_slow_queries`, `get_prometheus_metrics`

**Cross-agent sharing:**

- `set_memory_sharing`, `check_memory_access`, `get_shared_memories`, `create_shared_space`

**Real-time sync:**

- `publish_memory_event`, `get_sync_status`, `sync_agent_state`

**Backup & recovery:**

- `create_backup`, `restore_backup`, `list_backups`, `verify_backup`, `rollback_restore`

**Task scheduling:**

- `schedule_task`, `list_tasks`, `cancel_task`

**Multi-language:**

- `detect_language`, `get_supported_languages`, `search_by_language`, `get_language_distribution`, `cross_language_search`

**Advanced search:**

- `advanced_search`, `expand_search_query`, `get_search_facets`, `get_search_analytics`

#### 6.2.3 Custom Python Modules (`src/`)

| Module                                                             | Purpose                               | Originality                                                         |
| ------------------------------------------------------------------ | ------------------------------------- | ------------------------------------------------------------------- |
| `memory_management.py`                                             | Retention policies, lifecycle         | Enhanced-only                                                       |
| `memory_deduplication.py`                                          | Similarity-based dedup                | Enhanced-only                                                       |
| `memory_summarization.py`                                          | LLM-driven summarization              | Enhanced-only                                                       |
| `intelligent_summarization.py`                                     | Strategy-based summarization          | Enhanced-only                                                       |
| `advanced_search_reranking.py`                                     | Cross-encoder rerank                  | Enhanced-only                                                       |
| `multi_language_search.py`                                         | Polyglot search                       | Enhanced-only                                                       |
| `language_detector.py`                                             | Lang detect                           | Enhanced-only (Original has `tasks/translation/detect_language.py`) |
| `performance_analytics.py`                                         | Query/op metrics                      | Enhanced-only                                                       |
| `cross_agent_sharing.py`                                           | Memory ACL between agents             | Enhanced-only                                                       |
| `realtime_sync.py` + `realtime_websocket_server.py`                | Pub-sub events                        | Enhanced-only                                                       |
| `backup_manager.py` + `backup_verifier.py` + `recovery_manager.py` | Backup stack                          | Enhanced-only                                                       |
| `audit_logger.py`                                                  | Audit trail                           | Enhanced-only                                                       |
| `auto_configuration.py`                                            | Self-configuring stack                | Enhanced-only                                                       |
| `transaction_manager.py`                                           | DB transactions                       | Enhanced-only                                                       |
| `undo_manager.py`                                                  | Undo log                              | Enhanced-only                                                       |
| `approval_workflow.py`                                             | Multi-step approvals                  | Enhanced-only                                                       |
| `session_manager.py`                                               | Session lifecycle                     | Enhanced-only (Original has its own in `infrastructure/session/`)   |
| `progressive_disclosure.py`                                        | Result paging                         | Enhanced-only                                                       |
| `structured_memory.py`                                             | Schema'd memory                       | Enhanced-only                                                       |
| `lite_mode/`                                                       | Single-process lite stack             | Enhanced-only                                                       |
| `multi_tenant/`                                                    | Per-tenant isolation                  | Enhanced-only                                                       |
| `security/`, `security_mcp.py`                                     | Input validation, authz, confirmation | Enhanced-only                                                       |
| `coordination/`                                                    | Agent coordination                    | Enhanced-only                                                       |
| `ecosystem/`                                                       | Third-party integration               | Enhanced-only                                                       |
| `claude_api_integration.py`                                        | Direct Claude API                     | Enhanced-only                                                       |
| `mcp_memory_tools.py`                                              | MCP-side helpers                      | Enhanced-only                                                       |
| `mcp_response_formatter.py`                                        | Consistent response shapes            | Enhanced-only                                                       |
| `logging_config.py`                                                | Structured logging                    | Enhanced-only                                                       |
| `scheduler.py`, `scheduled_*.py`, `maintenance_scheduler.py`       | Background job scheduling             | Enhanced-only                                                       |
| `document_processor.py`                                            | Document pipeline                     | Enhanced-only (overlaps with Original's loaders/)                   |
| `performance_optimizer.py`                                         | Query optimization hints              | Enhanced-only                                                       |
| `agent_memory_integration.py`                                      | Agent memory bridge                   | Enhanced-only (overlaps with Original's `modules/agent_memory/`)    |

#### 6.2.4 Operational Tooling

- Comprehensive `docs/` with 80+ markdown files (audits, sprint reports, guides)
- `dashboard/` directory
- `cognee-frontend/` (fork of Original's, possibly drifted)
- Cross-IDE installation guides
- Disaster recovery, monitoring setup, security hardening checklists
- Sprint-by-sprint completion reports

#### 6.2.5 Constraints Enforced by Enhanced

- **ASCII-only output** mandatory (Windows console safety)
- **Dynamic categories** mandatory (no hardcoded ATS/OMA/SMC)
- Default-on Enhanced port range (25xxx/26xxx/27xxx) to avoid clash

---

## 7. Porting Plan: Original -> Enhanced

### 7.1 Prioritisation Rubric

| Priority            | Criterion                                                                                                       |
| ------------------- | --------------------------------------------------------------------------------------------------------------- |
| **P0 - Critical**   | Security, data integrity, or a foundational module the rest of the codebase will depend on. Must merge first.   |
| **P1 - High value** | Features Enhanced users will notice within a sprint (search quality, cloud, sessions, loaders).                 |
| **P2 - Useful**     | Quality-of-life features (UI bulk actions, export improvements, scheduled backups).                             |
| **P3 - Optional**   | Original-only features that conflict with Enhanced architecture (e.g., Ladybug vs Neo4j swap). Defer or reject. |

### 7.2 P0 - Critical (Phase 1, ~10 days)

#### 7.2.1 MCP Transport Security

**What**: Port `_configure_transport_security`, `_get_cors_origins`, `run_sse_with_cors`, `run_http_with_cors` from Original's `cognee-mcp/src/server.py`.

**Why**: Enhanced's MCP server runs stdio-only with no DNS-rebinding protection. If it ever runs over HTTP/SSE (it should, per Original's pattern), it is vulnerable.

**Where**:

- Touch: `bin/enhanced_cognee_mcp_server.py`
- Add: argparse for `--transport`, `--host`, `--port`, `--path`, `--log-level`
- Add: env vars `MCP_DISABLE_DNS_REBINDING_PROTECTION`, `MCP_ALLOWED_HOSTS`, `MCP_CORS_ALLOW_ORIGINS`

**Acceptance criteria**:

- Server starts in `stdio` mode (backwards-compatible default)
- Server can also start in `sse` or `http` mode
- DNS-rebinding protection ON by default for non-loopback hosts
- Existing 58 MCP tools continue to work

**Risk**: Low. Pure additive change.

#### 7.2.2 Loader System

**What**: Port `cognee/infrastructure/loaders/` (LoaderEngine, LoaderInterface, supported_loaders, plus core + external loaders).

**Why**: Enhanced currently has only ad-hoc document processing in `src/document_processor.py`. A pluggable loader system is needed for PDF (pypdf, advanced_pdf), DOCX (unstructured), HTML (BeautifulSoup), audio, image, CSV ingestion.

**Where**:

- Bring into: `cognee/infrastructure/loaders/`
- Wire into: `src/document_processor.py` (which becomes a thin wrapper)
- Update: `add_memory` MCP tool to route through LoaderEngine when input is a file path

**Acceptance criteria**:

- All Original loader unit tests pass against Enhanced fork
- A `.pdf` and `.docx` file ingest cleanly via `add_memory`
- ASCII-only output preserved in all loader stdout

**Risk**: Medium. Heavy dependency surface (unstructured, docling, beautifulsoup4).

#### 7.2.3 Agent Memory Module

**What**: Port `cognee/modules/agent_memory/` (decorator + runtime + models).

**Why**: This is Original's clean integration pattern for agents. Enhanced's `src/agent_memory_integration.py` solves the same problem but does not match Original's interface, which means LangChain/LlamaIndex/Mastra integrations from upstream won't plug in cleanly.

**Where**:

- Bring into: `cognee/modules/agent_memory/`
- Update: `src/agent_memory_integration.py` to delegate to it

**Acceptance criteria**:

- `@with_agent_memory` decorator works on a sample async function
- Existing `agent_memory_integration` callers keep working

**Risk**: Medium. Interface design must be backward-compatible with existing Enhanced callers.

#### 7.2.4 Pipeline Execution Mode (Background / Blocking)

**What**: Port `cognee/modules/pipelines/layers/pipeline_execution_mode.py` and the queues + exceptions submodules.

**Why**: Enables `run_in_background=True` for long-running cognify operations, matching Original v1.0.4+ behavior.

**Where**:

- Bring into: `cognee/modules/pipelines/`
- Wire into: `cognify` MCP tool

**Acceptance criteria**:

- `cognify(data=..., run_in_background=True)` returns immediately with a `pipeline_run_id`
- `cognify_status(dataset_name)` MCP tool reports progress + errors

**Risk**: Medium.

#### 7.2.5 ASCII-Compatibility Pass on Ported Code

**What**: Every newly ported file must be scrubbed of Unicode symbols before merge. Add a CI check.

**Why**: Per `CLAUDE.md`, all output must use ASCII to avoid Windows `cp1252` `UnicodeEncodeError`.

**Where**:

- Add: `scripts/check_ascii_output.py` that scans for emoji/non-ASCII in source files (excludes test fixtures, README.md, docstrings inside `"""`)
- Wire into: pre-commit hook and CI

**Acceptance criteria**:

- CI fails any PR that introduces emoji in production code paths

**Risk**: Low.

### 7.3 P1 - High Value (Phase 2, ~8 days)

#### 7.3.1 Modern Retrievers

**What**: Port `cognee/modules/retrieval/` (all retrievers except those Enhanced already does better).

**Concretely port**:

- `temporal_retriever.py`
- `lexical_retriever.py` (BM25-style)
- `natural_language_retriever.py`
- `summaries_retriever.py`
- `graph_completion_decomposition_retriever.py`
- `graph_completion_cot_retriever.py`
- `coding_rules_retriever.py`
- `register_retriever.py` + `registered_community_retrievers.py` (plugin system)
- `utils/access_tracking.py`, `utils/query_decomposition.py`, `utils/query_state.py`, `utils/stop_words.py`

**Why**: Brings Enhanced's `search` and `advanced_search` MCP tools to feature parity. Enables `FEELING_LUCKY` auto-routing.

**Where**:

- Bring into: `cognee/modules/retrieval/`
- Wire into: `bin/enhanced_cognee_mcp_server.py` `advanced_search` tool with strategy selection

**Acceptance criteria**:

- `advanced_search(strategy="temporal", ...)` works
- `advanced_search(strategy="lexical", ...)` works
- `FEELING_LUCKY` strategy added that auto-selects

**Risk**: Medium.

#### 7.3.2 Session-Aware Memory Ops

**What**: Port `cognee/infrastructure/session/`, `cognee/modules/session/`, `cognee/api/v1/session/`, `cognee/api/v1/remember/`, `cognee/api/v1/recall/`, `cognee/api/v1/forget/`, `cognee/api/v1/improve/`.

**Why**: Conversational AI applications need session-scoped memory. The 4-stage `improve` pipeline (feedback weights -> session-to-graph -> triplet enrichment -> graph-to-session) is unique IP worth absorbing.

**Where**:

- Bring into: `cognee/api/v1/{session,remember,recall,forget,improve}/`
- Bring into: `cognee/infrastructure/session/`
- Add MCP tools: `remember`, `recall`, `forget_memory`, `improve` (mirroring Original)

**Acceptance criteria**:

- `remember(data="...", session_id="...")` stores to session cache
- `recall(query="...", session_id="...")` searches session first, then permanent
- `improve(session_ids="abc,def")` runs the 4-stage pipeline

**Risk**: Medium-High. Requires careful overlap reconciliation with Enhanced's `src/session_manager.py`.

#### 7.3.3 Memify Pipelines

**What**: Port `cognee/tasks/memify/` (apply_feedback_weights, cognify_session, extract_feedback_qas, extract_subgraph, extract_subgraph_chunks, extract_user_sessions, feedback_weights_constants, get_triplet_datapoints, sync_graph_to_session) and `cognee/memify_pipelines/`.

**Why**: Core of Original's `improve` endpoint and feedback loops.

**Where**:

- Bring into: `cognee/tasks/memify/` and `cognee/memify_pipelines/`
- Replace local `cognee/tasks/feedback/` (legacy, removed upstream)

**Acceptance criteria**:

- Local `tasks/feedback/` archived to `.archive/`
- Memify pipeline runs end-to-end with sample session data

**Risk**: Medium.

#### 7.3.4 Coding Agents (Rule Associations)

**What**: Port `cognee/tasks/codingagents/coding_rule_associations.py` and `coding_rules_retriever.py`.

**Why**: Enables Claude Code / Cursor / Windsurf to record interaction patterns and surface them as rules. Closes a gap in agent integration.

**Where**:

- Bring into: `cognee/tasks/codingagents/`
- Wire `save_interaction` MCP tool to use it (mirroring Original)

**Acceptance criteria**:

- New MCP tool `save_interaction(data="user: X\nassistant: Y")` works
- `recall(query="rules about Z")` returns associated rules

**Risk**: Low.

#### 7.3.5 Cloud Connectivity (Optional Toggle)

**What**: Port `cognee/api/v1/serve/` and `cognee/modules/cloud/`.

**Why**: While Enhanced is self-hosted-first, supporting an optional "serve-url" mode lets users bridge to Cognee Cloud or to a remote Enhanced instance.

**Where**:

- Bring into: `cognee/api/v1/serve/`
- Add MCP server args `--serve-url`, `--serve-api-key`
- **Toggle**: default OFF. Enable only if `COGNEE_SERVICE_URL` env var is set.

**Acceptance criteria**:

- Without `--serve-url`, behavior is unchanged
- With `--serve-url=https://example.com`, `add_memory` calls flow to the remote

**Risk**: Low (additive, opt-in).

### 7.4 P2 - Useful (Phase 3, ~6 days)

#### 7.4.1 Loaders Continued (External)

Port `cognee/infrastructure/loaders/external/`:

- `docling_loader.py`
- `unstructured_loader.py`
- `advanced_pdf_loader.py`

These are heavy dependencies. Wrap in optional install groups (e.g., `pip install RNR-Enhanced-Cognee[docling]`).

#### 7.4.2 Translation Tasks

**What**: Port `cognee/tasks/translation/` (Azure, Google, LLM providers).

**Why**: Enhanced has its own multi-language search in `src/multi_language_search.py` but lacks translation. Original's providers are pluggable.

**Where**:

- Bring into: `cognee/tasks/translation/`
- Wire into: `src/multi_language_search.py` for query/document translation

**Risk**: Low.

#### 7.4.3 Custom Pipelines

**What**: Port `cognee/modules/run_custom_pipeline/run_custom_pipeline.py`.

**Why**: Enables users to define their own ingestion pipelines.

**Where**:

- Bring into: `cognee/modules/run_custom_pipeline/`
- Add MCP tool `run_custom_pipeline(pipeline_file: str, data: str)`

**Risk**: Medium (security implications - executes user-supplied code; gate behind authorization).

#### 7.4.4 Cleanup Tasks

**What**: Port `cognee/tasks/cleanup/cleanup_unused_data.py`.

**Why**: Removes orphaned chunks/entities after deletions. Complements Enhanced's `expire_memories`.

**Where**: `cognee/tasks/cleanup/`. Optionally schedule via `schedule_task` MCP tool.

**Risk**: Low.

#### 7.4.5 Entity Extractors (Regex)

**What**: Port `cognee/tasks/entity_completion/entity_extractors/`.

**Why**: Faster than LLM extraction for known patterns (emails, URLs, dates).

**Where**: `cognee/tasks/entity_completion/`.

**Risk**: Low.

#### 7.4.6 v2 Graph Extraction & Cascade

**What**: Port `cognee/tasks/graph/extract_graph_from_data_v2.py` and `cognee/tasks/graph/cascade_extract/`.

**Why**: Better quality knowledge-graph extraction per release notes.

**Where**: `cognee/tasks/graph/`. Feature-flag with env var `COGNEE_GRAPH_EXTRACTOR_VERSION=v1|v2`. Default v1 for backwards-compat; flip to v2 after Phase 4 hardening.

**Risk**: Medium.

### 7.5 P3 - Defer or Reject

| Feature                                  | Decision             | Reason                                                                    |
| ---------------------------------------- | -------------------- | ------------------------------------------------------------------------- |
| Kuzu -> Ladybug swap                     | **Reject**           | Enhanced uses Neo4j; Original's Kuzu swap is irrelevant. Keep Neo4j.      |
| LanceDB / local vector                   | **Reject**           | Enhanced uses Qdrant. Keep Qdrant.                                        |
| Cognee Cloud auto-enrolment              | **Defer**            | Out of scope for self-hosted-first. Keep optional toggle (Section 7.3.5). |
| Frontend (cognee-frontend) major upgrade | **Defer**            | Frontend already exists locally; assess separately in Phase 4.            |
| `evals/` expansion                       | **Defer to Phase 4** | Not parity-blocking.                                                      |

### 7.6 Per-Port Checklist (Applies to Every Item)

For each item above, the developer (or Claude) must:

1. Read the Original file(s) in full
2. Identify dependencies on other Original modules and confirm they exist locally (or add them first)
3. Run `scripts/check_ascii_output.py` on the new file
4. Replace any hardcoded "ats", "oma", "smc" with dynamic category lookup
5. Replace Unicode symbols with ASCII (`OK`, `WARN`, `ERR`, `[DOC]`, `[MEM]`)
6. Write or port unit tests
7. Run `pytest tests/` and confirm no regressions
8. Run the MCP server end-to-end smoke test
9. Update `CHANGELOG.md` and the relevant doc in `docs/`
10. Open a PR with one feature per PR (no bundling unrelated ports)

---

## 8. Hardening Plan for Enhanced-Unique Features

### 8.1 Audit Findings (Things to Fix Regardless of Upstream Sync)

#### 8.1.1 Hardcoded Categories in `src/agents/`

**Finding**: `src/agents/` contains directories `ats`, `oma`, `smc`, and a literal `{ats,oma,smc}` directory (likely a shell-glob mistake). This directly violates `CLAUDE.md`'s "no hardcoded categories" rule.

**Fix (P0)**:

- Audit every file in `src/agents/{ats,oma,smc}/`
- Move generic logic to `src/agents/_base/`
- Replace category-specific subclasses with a registry pattern reading from `.enhanced-cognee-config.json`
- Archive the literal `{ats,oma,smc}` directory to `.archive/`
- Add a CI check that fails any new `class ATSAgent`, `OMAAgent`, `SMCAgent` definition

#### 8.1.2 Cognee Fork Modernisation

**Finding**: `cognee/` is frozen at v0.5.1. Many ports (Section 7) require modules that don't exist in v0.5.1.

**Fix (P0)**:

- Either:
  - **Option A**: Rebase Enhanced onto Original's v1.0.9 stable. High effort, high reward.
  - **Option B**: Cherry-pick required modules per Section 7. Low effort, but accumulates debt.
- **Recommended**: Option B for Phase 1-3, then Option A in Phase 4.

#### 8.1.3 MCP Server Refactor

**Finding**: `bin/enhanced_cognee_mcp_server.py` is 4088 lines in a single file. Hard to test, slow to import, error-prone to modify.

**Fix (P1)**:

- Split into `src/mcp/` package: `tools/`, `init/`, `transport/`, `auth/`
- Each MCP tool becomes its own file (one tool per file)
- Top-level `server.py` only wires tools together

**Risk of split**: Possible import-time regressions. Mitigate with end-to-end MCP smoke test.

#### 8.1.4 Test Coverage Gaps

**Finding**: Multiple `test_run_*.log` files at repo root suggest manual ad-hoc test runs. No clear coverage report.

**Fix (P1)**:

- Standardise on `pytest --cov` with HTML output to `htmlcov/`
- Set a coverage floor (start at 60%, target 80% by Phase 6)
- Add `pre-commit` hook to run smoke tests
- Delete ad-hoc `test_run_*.log` files from repo root; archive them under `.archive/`

#### 8.1.5 Documentation Sprawl

**Finding**: `docs/` has 80+ files including sprint reports, audits, "phase 2 complete" docs. Useful but hard to navigate.

**Fix (P2)**:

- Promote `docs/README.md` to a true index
- Move sprint reports to `docs/reports/sprints/` (already done, mostly)
- Move "audit complete" docs to `docs/archive/`
- Keep a single "What's the current state?" doc up to date: `docs/STATE.md`

### 8.2 Per-Feature Hardening Pass

For each of the 58 MCP tools and 46 `src/*.py` modules, perform the following audit (work batched in Phase 4):

| Check                  | Description                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------- |
| **ASCII compliance**   | No Unicode symbols in output                                                                |
| **Dynamic categories** | No hardcoded `"ats"`/`"oma"`/`"smc"`/`"trading"`/`"dev"` in code; load from config          |
| **Type hints**         | Every public function has return + parameter type hints                                     |
| **Docstrings**         | One-line docstring on every public function                                                 |
| **Error handling**     | Distinguishable error types; no bare `except:`                                              |
| **Logging**            | Use `src/logging_config.py:get_logger`, not `print`                                         |
| **Tests**              | At least one happy-path + one error-path test per public function                           |
| **Security**           | Inputs validated per `src/security_mcp.py` (UUID, days, limit, agent_id, category, content) |
| **Transactions**       | Multi-step DB ops wrapped in `src/transaction_manager.py`                                   |
| **Idempotency**        | Tools that can be retried (e.g., `auto_deduplicate`) are idempotent                         |
| **Resource cleanup**   | Connections released in `finally:`                                                          |

### 8.3 Specific Enhancement Opportunities (Per Module)

These are improvements I would make to existing Enhanced modules. Each is independent and small enough for a single PR.

| Module                             | Improvement                                                              |
| ---------------------------------- | ------------------------------------------------------------------------ |
| `src/memory_management.py`         | Add per-category retention policies (currently global)                   |
| `src/memory_deduplication.py`      | Add async batch mode; current impl loops one-by-one                      |
| `src/memory_summarization.py`      | Add caching layer on summary results (Redis)                             |
| `src/intelligent_summarization.py` | Persist `SummaryStrategy` choice per agent in config                     |
| `src/advanced_search_reranking.py` | Add cross-encoder model selection via config                             |
| `src/multi_language_search.py`     | Wire Original's `tasks/translation/` (P2 port) for query translation     |
| `src/language_detector.py`         | Replace with Original's `langdetect`-based detector (faster, lower deps) |
| `src/performance_analytics.py`     | Expose Prometheus histograms, not just counters                          |
| `src/cross_agent_sharing.py`       | Add explicit grant expiration                                            |
| `src/realtime_sync.py`             | Add at-least-once delivery guarantee with Redis Streams                  |
| `src/backup_manager.py`            | Add cross-database consistency check before backup                       |
| `src/backup_verifier.py`           | Add automatic restore-test on backup creation                            |
| `src/recovery_manager.py`          | Add point-in-time recovery for PostgreSQL                                |
| `src/audit_logger.py`              | Move from file to PostgreSQL table for queryability                      |
| `src/auto_configuration.py`        | Detect Docker vs bare-metal and adjust ports                             |
| `src/transaction_manager.py`       | Add savepoint / nested transaction support                               |
| `src/undo_manager.py`              | Cap undo log size (currently unbounded)                                  |
| `src/approval_workflow.py`         | Add timeout for pending approvals                                        |
| `src/session_manager.py`           | Align interface with ported `cognee/infrastructure/session/`             |
| `src/progressive_disclosure.py`    | Add cursor-based pagination                                              |
| `src/structured_memory.py`         | Add JSON-schema validation                                               |
| `src/lite_mode/`                   | Add `--lite` MCP server flag that skips Qdrant/Neo4j                     |
| `src/multi_tenant/`                | Add tenant quotas                                                        |
| `src/security/`                    | Add rate limiting per agent                                              |
| `src/coordination/`                | Add deadlock detection for multi-agent locks                             |

---

## 9. Automated Upstream Sync Pipeline

### 9.1 Goals

1. **Detect** new Original releases within 24 hours
2. **Compare** the new release against Enhanced's last-synced version
3. **Generate** a structured report of what changed in upstream
4. **Propose** a porting PR (or skip if no impact)
5. **Test** the proposed PR against Enhanced's full test suite
6. **Notify** Vincent for approval before merge
7. **Roll back** safely if a merge breaks Enhanced

Nothing merges automatically. Vincent is the human gate.

### 9.2 Architecture Overview

```
GitHub Actions (Enhanced repo)
   |
   |  schedule: every 6 hours
   v
[detect-upstream-release.yml]
   |
   |  fetches https://api.github.com/repos/topoteretes/cognee/releases/latest
   |  compares against .upstream-sync/last_seen_release.txt
   v
   if new release detected:
     |
     v
[compare-upstream.yml]   <- spawned by detect job
   |
   |  - clones upstream cognee at new tag
   |  - runs scripts/upstream_diff.py
   |  - outputs: docs/automation/upstream-diffs/<tag>.md
   |  - outputs: machine-readable plan: .upstream-sync/<tag>.json
   v
[propose-port-pr.yml]    <- spawned by compare job
   |
   |  - creates branch: upstream-sync/<tag>
   |  - applies "safe" ports (no breaking, no schema migration)
   |  - opens PR titled "[Upstream Sync] cognee <tag>"
   |  - assigns Vincent as reviewer
   |  - posts the diff report as PR comment
   v
[validate-port.yml]      <- runs on PR
   |
   |  - installs Enhanced
   |  - starts Postgres + Qdrant + Neo4j + Redis (docker)
   |  - runs full pytest
   |  - runs MCP smoke tests
   |  - reports coverage delta
   v
   Vincent reviews -> approves or requests changes
```

### 9.3 Components

#### 9.3.1 `scripts/upstream_diff.py`

A new Python script that:

```
Input:
  --upstream-tag v1.1.0.dev0
  --baseline-tag v1.0.1     (last synced)
  --upstream-clone /tmp/cognee-upstream
  --local-root .

Output:
  - upstream-diffs/<tag>.md (human-readable)
  - .upstream-sync/<tag>.json (machine-readable)

Logic:
  1. Run `git log baseline..upstream` to get commits between tags
  2. For each commit, classify by path:
     - cognee/api/ -> "api change"
     - cognee/infrastructure/databases/ -> "stack change"
     - cognee/modules/ -> "module change"
     - cognee/tasks/ -> "task change"
     - cognee-mcp/ -> "mcp change"
     - cognee-frontend/ -> "frontend change"
     - tests/ -> "test change"
     - pyproject.toml -> "dependency change"
     - alembic/ -> "schema change"  <-- always flagged HIGH RISK
  3. For each changed file, classify as:
     - "new file" - candidate for direct port
     - "modified file" - candidate for diff-merge
     - "deleted file" - candidate for removal (if Enhanced still has it)
  4. Produce porting plan:
     [{
       "file": "cognee/api/v1/recall/recall.py",
       "action": "new",
       "risk": "low",
       "auto_port": true,
       "blockers": []
     }, ...]
```

#### 9.3.2 `scripts/auto_port.py`

```
Input:
  --plan .upstream-sync/<tag>.json
  --apply

Logic:
  For each item where auto_port=true and risk=low:
    1. Copy file from upstream clone to Enhanced repo
    2. Run scripts/check_ascii_output.py on it
    3. Run scripts/check_no_hardcoded_categories.py on it
    4. If either check fails, mark item as "needs_manual_review"
    5. Commit with message "port: <file> from cognee <tag>"

  For each item where auto_port=false:
    1. Skip and record in PR description as "manual review required"
```

#### 9.3.3 `scripts/check_ascii_output.py`

Already proposed in Section 7.2.5. Reused here.

#### 9.3.4 `scripts/check_no_hardcoded_categories.py`

```
Scans for patterns:
  - re.search(r'["\'](?:ats|oma|smc|trading|dev|analysis)["\']', content)
  - Class definitions: ATSAgent, OMAAgent, SMCAgent, TradingAgent
  - Enum members: MemoryCategory.ATS, MemoryCategory.OMA, ...

Exits non-zero if any found in production code (excluding tests, archives, docs).
```

#### 9.3.5 GitHub Actions Workflows

`.github/workflows/upstream-sync-detect.yml`:

```yaml
name: Upstream Sync - Detect
on:
  schedule:
    - cron: "0 */6 * * *"
  workflow_dispatch:

jobs:
  detect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check upstream
        run: python scripts/upstream_check.py
      - name: Trigger compare if needed
        if: env.NEW_RELEASE == 'true'
        uses: peter-evans/repository-dispatch@v3
        with:
          event-type: upstream-compare
          client-payload: '{"tag": "${{ env.TAG }}"}'
```

`.github/workflows/upstream-sync-compare.yml`:

```yaml
name: Upstream Sync - Compare
on:
  repository_dispatch:
    types: [upstream-compare]
  workflow_dispatch:
    inputs:
      tag: { required: true }

jobs:
  compare:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: git clone --branch ${{ github.event.client_payload.tag }} https://github.com/topoteretes/cognee /tmp/upstream
      - run: python scripts/upstream_diff.py --upstream-tag ${{ ... }} ...
      - name: Create PR
        uses: peter-evans/create-pull-request@v6
        with:
          title: "[Upstream Sync] cognee ${{ ... }}"
          body-path: docs/automation/upstream-diffs/${{ ... }}.md
          reviewers: vincentspereira
          labels: upstream-sync, needs-review
```

`.github/workflows/upstream-sync-validate.yml`:

```yaml
name: Upstream Sync - Validate
on:
  pull_request:
    branches: [main]
    paths-ignore: ["docs/**", "*.md"]
    types: [opened, synchronize]
    # Only run on upstream-sync branches
jobs:
  validate:
    if: startsWith(github.head_ref, 'upstream-sync/')
    runs-on: ubuntu-latest
    services:
      postgres: { image: pgvector/pgvector:pg16, ports: ["25432:5432"], env: { ... } }
      qdrant: { image: qdrant/qdrant, ports: ["26333:6333"] }
      neo4j: { image: neo4j, ports: ["27687:7687"] }
      redis: { image: redis, ports: ["26379:6379"] }
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev]"
      - run: pytest --cov=src --cov=cognee --cov-report=xml
      - run: python scripts/mcp_smoke_test.py
      - run: python scripts/check_ascii_output.py
      - run: python scripts/check_no_hardcoded_categories.py
      - uses: codecov/codecov-action@v4
```

### 9.4 Frequency, Thresholds & Notification

| Trigger                                     | Action                                                 |
| ------------------------------------------- | ------------------------------------------------------ |
| New release detected                        | Open PR (assigned to Vincent)                          |
| Pre-release (`*.dev*`)                      | Open PR with `do-not-merge` label - informational only |
| Mandatory schema migration in release notes | Flag PR with `breaking-change` label, never auto-apply |
| `alembic/` change in diff                   | Flag PR with `schema-change` label, never auto-apply   |
| Validate workflow fails                     | Mark PR as draft, post error summary as comment        |
| No new release for 14 days                  | No action                                              |

### 9.5 Safety Guarantees

1. **Vincent is the only merger.** No automated merge under any condition.
2. **Schema migrations require Vincent's explicit confirmation.** Auto-port skips anything under `alembic/`.
3. **Breaking changes are auto-detected** by searching release notes for "breaking" / "migration" / "schema" / "removed" / "deprecated".
4. **Rollback path**: every upstream-sync PR is a single branch; reverting it is `git revert` + `git push`. Enhanced's main branch is never directly touched.
5. **Local pre-flight**: before automation goes live, run the sync manually for v1.0.2 -> v1.0.3 and confirm output is sensible.

### 9.6 Initial Backfill

Before automation runs:

- Set `.upstream-sync/last_seen_release.txt` to `v0.5.1` (Enhanced's baseline)
- Manually run `python scripts/upstream_diff.py --baseline-tag v0.5.1 --upstream-tag v1.0.9` and review the output
- Apply Phase 1-3 ports (Sections 7.2 - 7.4) **manually**
- Set `.upstream-sync/last_seen_release.txt` to `v1.0.9`
- Enable automation for `v1.0.10+`

This means the automation handles only forward-going releases. The big initial catch-up is human-driven.

---

## 10. Risk Register & Mitigation

| Risk                                                             | Likelihood | Impact | Mitigation                                                                      |
| ---------------------------------------------------------------- | ---------- | ------ | ------------------------------------------------------------------------------- |
| Mandatory schema migration in Original (v1.0.8 had one)          | High       | High   | Auto-port skips `alembic/`; Vincent reviews manually with rollback script ready |
| Original swaps a default backend (Kuzu -> Ladybug)               | Medium     | Medium | Enhanced is decoupled from default backend; impact contained                    |
| Port introduces Unicode that breaks Windows console              | Medium     | Medium | CI gate via `scripts/check_ascii_output.py`                                     |
| Port reintroduces hardcoded categories                           | Medium     | High   | CI gate via `scripts/check_no_hardcoded_categories.py`                          |
| 4088-line MCP file becomes unmergeable                           | High       | Medium | Phase 4 split into `src/mcp/tools/*.py`                                         |
| Frontend (`cognee-frontend/`) drifts irrecoverably from upstream | Medium     | Low    | Defer; assess in Phase 4                                                        |
| Upstream removes a feature Enhanced still uses                   | Low        | Medium | Auto-port flags as "deleted" for review; keep local version if needed           |
| Cognee Cloud SDK changes shape                                   | Low        | Low    | Cloud is optional in Enhanced; gate behind env var                              |
| Test suite latency >30 min in CI                                 | Medium     | Low    | Parallelise pytest, cache dependencies                                          |
| Dependency conflicts (e.g., pydantic 2.x bumps)                  | High       | Medium | Pin in `pyproject.toml`; resolve per-upgrade                                    |
| GitHub Actions rate limits                                       | Low        | Low    | Use `GITHUB_TOKEN`, avoid 1-min cron                                            |
| Vincent unavailable to review for >7 days                        | Medium     | Low    | PRs queue safely; Slack/email notification optional                             |

---

## 11. Approval Gates

This plan has six approval gates. Each requires Vincent's explicit "approved" before Claude (or the automation) proceeds to the next.

| Gate   | What's Approved                                                           | Output                                           |
| ------ | ------------------------------------------------------------------------- | ------------------------------------------------ |
| **G0** | This plan itself                                                          | Plan saved to `docs/plans/`, this section signed |
| **G1** | Phase 1 (P0 ports) scope, file list, and acceptance criteria              | A `TASKS-PHASE-1.md` file with checkbox list     |
| **G2** | Phase 2 (P1 ports)                                                        | `TASKS-PHASE-2.md`                               |
| **G3** | Phase 3 (P2 ports)                                                        | `TASKS-PHASE-3.md`                               |
| **G4** | Phase 4 (hardening) full audit list                                       | `TASKS-PHASE-4.md`                               |
| **G5** | Phase 5 (automation pipeline) - **especially** the GitHub Actions configs | Workflows files merged behind a feature flag     |
| **G6** | Phase 6 - sunset legacy code in `.archive/`                               | Final cleanup PR                                 |

No work starts on Phase N until Gate N-1 is approved.

---

## 12. Concrete Phase-by-Phase Execution

### 12.1 Phase 0: Pre-flight (1 day, no destructive changes)

- Inventory the `cognee-frontend/` and assess drift from upstream
- Inventory `evals/` and assess drift
- Set up `.upstream-sync/` directory with `last_seen_release.txt = "v0.5.1"`
- Verify Enhanced test suite runs green on a fresh clone
- Verify Docker stack starts cleanly
- Confirm port assignments (25xxx/26xxx/27xxx) don't conflict with Vincent's other projects
- **Deliverable**: `docs/plans/PHASE-0-REPORT.md`

### 12.2 Phase 1: P0 Ports (10 days)

In order:

1. ASCII + category CI checks (2 days)
2. MCP transport security (1 day)
3. Loader system (3 days)
4. Agent memory module (2 days)
5. Pipeline execution mode (2 days)

**Deliverable per item**: PR + tests + doc update.

### 12.3 Phase 2: P1 Ports (8 days)

1. Modern retrievers (3 days)
2. Session-aware memory ops (3 days)
3. Memify pipelines (1 day)
4. Coding agents (0.5 day)
5. Cloud connectivity toggle (0.5 day)

### 12.4 Phase 3: P2 Ports (6 days)

1. External loaders (2 days)
2. Translation tasks (1 day)
3. Custom pipelines (1 day)
4. Cleanup tasks (0.5 day)
5. Regex entity extractors (0.5 day)
6. v2 graph extraction (1 day)

### 12.5 Phase 4: Hardening (7 days)

1. Fix hardcoded categories in `src/agents/` (1 day)
2. Cognee fork rebase decision + execution (3 days)
3. MCP server refactor / split (2 days)
4. Test coverage push to 70% (1 day)

### 12.6 Phase 5: Automation Pipeline (4 days)

1. Write `scripts/upstream_diff.py` (1 day)
2. Write `scripts/auto_port.py` (1 day)
3. Write CI gate scripts (0.5 day)
4. Author 3 GitHub Actions workflows (1 day)
5. Manual dry run (0.5 day)

### 12.7 Phase 6: Docs & Rollout (2 days)

1. Promote `docs/STATE.md` as current-state doc
2. Archive obsolete docs
3. Write `docs/ops/UPSTREAM_SYNC_RUNBOOK.md`
4. Announcement + first auto-sync PR

---

## 13. Open Questions for Vincent

Please confirm or correct the following before approval:

1. **Frontend scope**: Do you want `cognee-frontend/` updated to match Original v1.0.9, or kept in its current state? (Current state is uncertain; Phase 0 will inventory it.) **User Reply:** I would like you to update `cognee-frontend/` to match Original v1.0.9

2. **Cloud mode**: Should Enhanced support `cognee.serve()` cloud connectivity at all? (Plan currently says "optional, opt-in".) **User Reply:** Yes, let Enhanced support `cognee.serve()` cloud connectivity.

3. **Graph backend swap**: Original swapped Kuzu -> Ladybug. Enhanced uses Neo4j and is unaffected. Confirm we keep Neo4j. **User Reply:** Pls keep Neo4j and do not swap it with Ladybug.

4. **Rebase strategy**: Section 8.1.2 - Option A (full rebase to v1.0.9) vs Option B (cherry-pick). Plan currently says B-then-A. Do you prefer all-at-once A? **User Reply:** Proceed with "**Option A**: Rebase Enhanced onto Original's v1.0.9 stable. High effort, high reward."

5. **Automation auto-merge**: Confirmed NO auto-merge under any condition? (Plan assumes you are the sole merger.) **User Reply:** I am fine with this that there should be no auto merge, but I will need guidance on how and when the merge is to be done. 

6. **Notification channel**: When automation opens a PR, do you want a Slack/email ping, or is the GitHub `@vincentspereira` review request enough? **User Reply:** I would like an email ping to my email id "vincentspereira@outlook.com"

7. **Breaking change handling**: If an upstream release contains a mandatory schema migration, should the automation:
   
   - (a) Open a draft PR with `breaking-change` label, no auto-port? (default plan)
   - (b) Skip the release entirely?
   - (c) Open a separate "migration plan" issue?
   
   **User Reply:** I would like you to decide on the best course of action in this case or recommend me with the best course of action.

8. **`src/agents/{ats,oma,smc}` directories**: Confirmation that these can be archived; their logic should move to a registry pattern. (Or do you have specific agents tied to those names that I should preserve?) **User Reply:** Yes, you may archive it. Bt see to it that nothing else breaks due to it.

---

## 14. Glossary

- **Original Cognee**: The upstream open-source project at `topoteretes/cognee`.
- **RNR Enhanced Cognee**: This local fork with PostgreSQL/Qdrant/Neo4j/Redis stack and 58 MCP tools.
- **Port**: Bring a feature from Original into Enhanced.
- **Sync**: Keep Enhanced up to date with Original's new releases.
- **P0/P1/P2/P3**: Priority levels (Critical/High/Useful/Optional).
- **Gate (G0-G6)**: Approval checkpoint requiring Vincent's sign-off.
- **MCP**: Model Context Protocol - Claude's tool integration standard.

---

## 15. Sign-Off

**Drafted by**: Claude (Anthropic) on 2026-05-13
**Awaiting approval from**: Vincent S. Pereira
**Approval format**: Add a section below titled `## 16. Approval Record` with:

- `Approved: YES/NO`
- `Date: YYYY-MM-DD`
- `Conditions/changes:` (any modifications to the plan)
- `Signed: Vincent S. Pereira`

Once approved, this document becomes the single source of truth for the parity and sync programme. Updates require a new revision with version bumped (1.1, 1.2, etc.).

---

## 16. Approval Record with:

* `Approved: YES`
* `Date: 2026-05-13`
* `Conditions/changes:` No modification, but I have provided my replies to your questions under the title "User Reply" after each question.
* `Signed: Vincent S. Pereira`

**End of plan.**
