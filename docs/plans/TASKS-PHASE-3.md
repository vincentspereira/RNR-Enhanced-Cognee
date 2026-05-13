# Phase 3 Task Tracking: P2 Port Implementation

**Status:** COMPLETE
**Branch:** feature/phase-3-p2-ports
**Merged into main:** 2026-05-13
**Tests:** 975/975 pass
**MCP tools:** 70 (up from 64 after Phase 2)

---

## Objective

Surface the remaining v1.0.9 upstream capabilities not yet in the MCP server:
external data loaders (web + database), text translation, regex entity extraction,
v2 cascade graph extraction, and loader discovery.

Scope is "P2 ports" - the second-priority feature gaps after Phase 2's P1 ports.

---

## Tasks

### 3.1 External Loaders - Web Scraping

**Status:** DONE

Tool: `ingest_url`

Wraps `cognee.tasks.web_scraper.web_scraper_task.web_scraper_task` and
`cron_web_scraper_task`. Accepts a single URL or comma-separated URL list.
Supports both Tavily (API key required, high quality) and BeautifulSoup
(free, no deps beyond scraping extras). Optional `schedule` parameter enables
cron-based recurring scrapes via APScheduler.

### 3.1 External Loaders - Database Ingestion

**Status:** DONE

Tool: `ingest_db`

Wraps `create_dlt_source_from_connection_string` + `ingest_dlt_source` from
`cognee.tasks.ingestion`. Supports PostgreSQL, MySQL, SQLite, MSSQL, Oracle
connection strings. Optional `query` parameter filters to a specific table
or SQL WHERE clause. Requires `dlt[sqlalchemy]` optional group.

### 3.2 Translation Pipeline

**Status:** DONE

Tool: `translate_text`

Wraps `cognee.tasks.translation.translate_content.translate_text` convenience
function. Supports three backends:
- `llm` (default) - uses configured LLM, no extra API keys needed
- `google` - Google Cloud Translate API (requires GOOGLE_TRANSLATE_API_KEY)
- `azure` - Azure Translator (requires AZURE_TRANSLATOR_KEY)

Auto-detects source language via langdetect (already a core dependency).
Returns translated text with source/target language and provider info.

Note: `detect_language`, `get_supported_languages`, `search_by_language`,
`get_language_distribution`, and `cross_language_search` were already in the
MCP server from a previous sprint - not duplicated here.

### 3.3 Loader Discovery

**Status:** DONE

Tool: `list_loaders`

Reads `cognee.infrastructure.loaders.supported_loaders.supported_loaders` at
runtime to show which loaders are active (ACTIVE) vs not installed (OFF).

Always active: PyPdfLoader, TextLoader, ImageLoader, AudioLoader, CsvLoader
Optional: UnstructuredLoader, AdvancedPdfLoader, BeautifulSoupLoader, DoclingLoader

### 3.4 Regex Entity Extractors

**Status:** DONE

Tool: `regex_extract_entities`

Wraps `cognee.tasks.entity_completion.entity_extractors.regex_entity_extractor.RegexEntityExtractor`.
Accepts optional `config_path` for custom regex pattern JSON; defaults to
the built-in cognee config (emails, URLs, phone numbers, dates, IP addresses, etc.).
Returns structured entity list with type and description for each match.

### 3.5 v2 Graph Extraction

**Status:** DONE

Tool: `extract_graph_v2`

Runs the v1.0.9 cascade extraction pipeline directly on provided text:
1. `extract_nodes(text, n_rounds)` - discover node candidates
2. `extract_content_nodes_and_relationship_names(...)` - refine with relationship names
3. `extract_edge_triplets(...)` - build edge triplets

Returns extracted nodes and edges as human-readable text. This is a preview
tool - it does NOT store the graph; use `remember()` or `cognify()` + recall
with GRAPH_COMPLETION for full pipeline storage.

### 3.6 Memify Pipeline MCP Tool

**Status:** DEFERRED to Phase 4

The memify tasks (`apply_feedback_weights`, `cognify_session`, `extract_user_sessions`,
etc.) are wired internally to `improve()` (Phase 2). No additional MCP tool is needed
as the `improve` tool already triggers the full 4-stage memify pipeline.

---

## CI Gate Results (2026-05-13)

| Gate                        | Result |
|-----------------------------|--------|
| Syntax check (py_compile)   | PASS   |
| Unit tests (975 total)      | PASS   |
| ASCII output gate           | PASS   |
| Hardcoded categories gate   | PASS   |

---

## Diff Summary

**File changed:** `bin/enhanced_cognee_mcp_server.py`

New `@mcp.tool()` functions added after line 4351 (after `cognify_status`):

| Tool                    | Lines    | Wraps                                          |
|-------------------------|----------|------------------------------------------------|
| ingest_url              | +75 loc  | web_scraper_task / cron_web_scraper_task       |
| ingest_db               | +55 loc  | create_dlt_source + ingest_dlt_source          |
| translate_text          | +50 loc  | translate_content.translate_text               |
| regex_extract_entities  | +50 loc  | RegexEntityExtractor.extract_entities          |
| extract_graph_v2        | +65 loc  | cascade_extract utils (3-step pipeline)        |
| list_loaders            | +40 loc  | supported_loaders dict                         |

**Total new lines:** ~400
**Tool count:** 64 -> 70

---

## Not In Scope (Deferred to Phase 4)

- src/agents/{ats,oma,smc} archive - Phase 4.1
- MCP server refactor (split 4500+ line file into modules) - Phase 4.2
- Test coverage push (>80%) - Phase 4.3
- cognee-frontend/ update to v1.0.9 - Phase 4.4
- Memify pipeline direct tool (deferred - already covered by improve()) - Phase 4 or skip

---

## Phase 3 Sign-Off

Branch `feature/phase-3-p2-ports` merged into `main` on 2026-05-13.
All 975 unit tests pass. 70 MCP tools active.
