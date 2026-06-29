# README.md - Proposed Changes

**Prepared**: 2026-05-13
**Status**: AWAITING APPROVAL - do not apply until Vincent approves

This document lists every change needed to bring README.md current with the
actual state of the project after Phases 1-6. No changes are made to README.md
until you reply with approval.

---

## SECTION 1: Items to UPDATE (wrong numbers/facts)

### 1.1 - MCP tool count badge (line 17)
**Current**: "58 MCP tools" in the subtitle
**Should be**: "70 MCP tools"

**Current**: badge `Tests=975 Passing (100%)`
**Should be**: badge `Tests=497 Passing (100%)` (497 is the unit test count; 975 was a miscounted total from testing/ + tests/)

### 1.2 - MCP tool count in table (line 62)
**Current**: `| **MCP Tools** | cognee-mcp directory | 4 search tools | **59 comprehensive tools** |`
**Should be**: `| **MCP Tools** | cognee-mcp directory | 4 search tools | **70 comprehensive tools** |`

### 1.3 - Overview bullet list (lines 115-136)
**Current**:
```
- 58 MCP tools for comprehensive memory management
- SDLC sub-agent coordination (21 specialized agents)
- Comprehensive test coverage (975 tests, 100% pass rate, 0 warnings, 0 skipped)
```
**Should be**:
```
- 70 MCP tools for comprehensive memory management (including v1.0.9 session memory,
  web ingestion, translation, cascade v2 graph extraction)
- Dynamic category system (no hardcoded categories; configure via .enhanced-cognee-config.json)
- Automated upstream sync monitoring (GitHub Actions weekly monitor + email alerts)
- Comprehensive test coverage (497 unit tests, 100% pass rate)
```
Remove "21 SDLC Agents" bullet - those agents were archived in Phase 4.

### 1.4 - "What is RNR Enhanced Cognee?" section, item 2 (lines 167-175)
**Current**: "59 MCP Tools" heading and bullets that list old tool categories
**Should be**: "70 MCP Tools" and updated category list including Phase 2/3 additions:
```
- Standard Memory MCP tools (add_memory, search_memories, etc.)
- Session-aware memory (remember, recall, forget_memory, improve, save_interaction)
- External loaders (ingest_url, ingest_db, list_loaders)
- Translation and NER (translate_text, regex_extract_entities)
- Graph extraction (extract_graph_v2)
- Memory management (expiry, archival, TTL)
- Deduplication and summarization
- Performance analytics and monitoring
- Cross-agent sharing and real-time sync
- Multi-language support (28 languages, cross-language search)
- Advanced AI features (intelligent summarization, semantic clustering, cascade v2 graph)
- Backup and recovery
```

### 1.5 - Search types count in table (line 71)
**Current**: `| **Search Types** | 8 specialized types | FTS5 + 4 tools | **8 specialized types** |`
**Should be**: `| **Search Types** | 15 specialized types | FTS5 + 4 tools | **15 specialized types** |`
(upstream went from 8 to 15 in v1.0.9; both columns need updating)

### 1.6 - Multi-language row in table (line 72)
**Current**: `| **Multi-Language Support** | English | **28 languages** | English (planned) |`
**Should be**: `| **Multi-Language Support** | English | **28 languages** | **28 languages (detect, search, cross-language)** |`
(detect_language, search_by_language, cross_language_search are all implemented)

### 1.7 - Test suite reference (line 188)
**Current**: "975 tests passing (100% pass rate, comprehensive coverage)"
**Should be**: "497 unit tests passing (100% pass rate); integration tests available separately"

---

## SECTION 2: Items to ADD (new features not documented)

### 2.1 - New section after "New Features": "v1.0.9 API Parity"

Insert after line ~194 (after the "New Features" heading):

```markdown
## v1.0.9 API Parity

RNR Enhanced Cognee tracks and exposes the full topoteretes/cognee v1.0.9 public API via MCP tools.

### Session-Aware Memory (Phase 2)
These tools wrap the `cognee.api.v1.*` modules added in upstream v1.0.9:

| Tool | API Module | Description |
|------|-----------|-------------|
| `remember` | `cognee.api.v1.remember` | Session-aware ingestion with background mode |
| `recall` | `cognee.api.v1.search` | 15-strategy knowledge graph retrieval |
| `forget_memory` | `cognee.api.v1.forget` | Targeted graph data deletion |
| `improve` | `cognee.api.v1.improve` | 4-stage feedback improvement pipeline |
| `save_interaction` | `cognee.api.v1.add` + `cognify` | Record user/assistant exchanges |
| `cognify_status` | internal tracker | Check background task status |

### External Loaders & Enrichment (Phase 3)

| Tool | Underlying Task | Description |
|------|----------------|-------------|
| `ingest_url` | `web_scraper_task` | Scrape URLs (BeautifulSoup or Tavily) |
| `ingest_db` | dlt pipeline | Ingest relational DB tables |
| `translate_text` | `translate_content` | LLM/Google/Azure translation |
| `regex_extract_entities` | `RegexEntityExtractor` | Configurable pattern NER |
| `extract_graph_v2` | cascade extract utils | Preview v2 graph extraction (n rounds) |
| `list_loaders` | `supported_loaders` | Show available file format loaders |

### Search Type Reference
All 15 `SearchType` values supported by `recall` and `search`:

| Type | Description |
|------|-------------|
| `GRAPH_COMPLETION` | LLM-augmented graph traversal (recommended default) |
| `GRAPH_COMPLETION_COT` | Chain-of-thought graph reasoning |
| `GRAPH_COMPLETION_DECOMPOSITION` | Decompose query into sub-questions |
| `GRAPH_COMPLETION_CONTEXT_EXTENSION` | Extend context along graph edges |
| `GRAPH_SUMMARY_COMPLETION` | Search graph-level summaries |
| `SUMMARIES` | Document and chunk summaries |
| `CHUNKS` | Raw text chunk retrieval |
| `CHUNKS_LEXICAL` | BM25-style lexical chunk search |
| `RAG_COMPLETION` | Retrieval-augmented generation |
| `TRIPLET_COMPLETION` | Knowledge triplet retrieval |
| `NATURAL_LANGUAGE` | Natural language query parser |
| `TEMPORAL` | Time-aware knowledge retrieval |
| `CODING_RULES` | Retrieve coding rules and patterns |
| `CYPHER` | Direct Cypher query against graph |
| `FEELING_LUCKY` | Auto-select best strategy for query |
```

### 2.2 - New section: "Upstream Sync Monitoring"

Add after the "Architecture" section:

```markdown
## Upstream Sync Monitoring

RNR Enhanced Cognee includes automation to stay current with upstream topoteretes/cognee releases.

### Automated Weekly Check
A GitHub Actions workflow (`.github/workflows/upstream_sync.yml`) runs every Monday at 08:00 UTC:
- Fetches the latest upstream release tag via GitHub API
- Compares against `.upstream-sync/last_seen_release.txt`
- If new release detected: builds diff report, opens tracking GitHub issue, sends email alert

### Manual Check
```bash
# Check if upstream has new releases (exit 1 = new release available)
python scripts/upstream_diff.py --check-only

# Generate full diff report
python scripts/upstream_diff.py --token $GITHUB_TOKEN

# Generate stub MCP tools and porting checklist
python scripts/auto_port.py
```

### Sync Files
| File | Purpose |
|------|---------|
| `.upstream-sync/last_seen_release.txt` | Current synced baseline tag |
| `.upstream-sync/sync-metadata.json` | Full sync state record |
| `scripts/upstream_diff.py` | Diff report generator |
| `scripts/auto_port.py` | Stub and TODO generator |
| `docs/UPSTREAM_SYNC_RUNBOOK.md` | Full porting operator guide |
```

### 2.3 - New section: "Dynamic Category System"

Add to the Configuration section:

```markdown
### Dynamic Categories

Categories are NOT hardcoded. Define your own in `.enhanced-cognee-config.json`:

```json
{
  "categories": {
    "trading": { "prefix": "trading_", "description": "Trading system memories" },
    "development": { "prefix": "dev_", "description": "Development memories" },
    "research": { "prefix": "res_", "description": "Research notes" }
  }
}
```

No code changes required - RNR Enhanced Cognee loads categories at runtime.
Any category name, any prefix. The old ATS/OMA/SMC categories are not used.
```

---

## SECTION 3: Items to REMOVE (outdated/misleading)

### 3.1 - "21 SDLC Agents Integration" section and ToC entry
The `ats/`, `oma/`, `smc/` agent directories were archived in Phase 4 for violating the dynamic categories requirement. The "21 SDLC Agents Integration" section and its Table of Contents entry should be removed (or replaced with a note pointing to the archive).

**Proposed replacement** (brief, honest):
```markdown
## Agent Integration
The original 21 SDLC agent modules (ATS, OMA, SMC categories) have been archived
as of Phase 4 due to hardcoded category violations. RNR Enhanced Cognee now uses a
dynamic agent registry loaded from `.enhanced-cognee-config.json`. See
`.archive/2026-05-13_agents_ats_oma_smc/ARCHIVE_NOTES.md` for migration guidance.
```

### 3.2 - "Support for 8 AI IDEs" bullet in Overview
This should stay but needs verification - check if all 8 IDE configs are still current. If you haven't tested all 8, soften to "Multiple AI IDE support (Claude Code, VS Code, Cursor, Windsurf, and others)".

### 3.3 - "400-700% performance improvement" claim (line 17, 79)
This is from the original design doc and was never benchmarked in the phases we did. Either:
- Remove the claim, or
- Add a note: "Based on theoretical architecture comparison; not yet benchmarked in production"

---

## SECTION 4: Items to FIX (inaccurate but not wrong enough to remove)

### 4.1 - Stars/CI badge URLs
The `Tests=975 Passing` badge is wrong and will confuse readers. Update to `Tests=497 Passing`.

### 4.2 - Table of Contents
Add new entries:
- `[v1.0.9 API Parity](#v109-api-parity)` (new section)
- `[Upstream Sync Monitoring](#upstream-sync-monitoring)` (new section)

Remove:
- `[21 SDLC Agents Integration](#21-sdlc-agents-integration)` (archived)

### 4.3 - License/Acknowledgments section
**Current**: Only credits Topoteretes UG as copyright holder. Your own contributions are uncredited.

**Proposed addition**:
```markdown
## License

RNR Enhanced Cognee is derived from [Cognee](https://github.com/topoteretes/cognee)
by Topoteretes UG, licensed under the Apache License, Version 2.0.

**Original Cognee copyright**: Copyright 2024 Topoteretes UG

**RNR Enhanced Cognee additions copyright**: Copyright 2026 Vincent S. Pereira

All RNR Enhanced Cognee additions, modifications, and original code are also
released under the Apache License, Version 2.0.

The Apache 2.0 license requires that:
1. This notice is preserved in all distributions
2. The original Cognee project is credited (done above)
3. Changes from the original are noted (done in git history and this README)
```

---

## SUMMARY OF CHANGES

| Type | Count | Examples |
|------|-------|---------|
| Update (wrong numbers) | 7 | tool count, test count, search types |
| Add (new features) | 3 sections | v1.0.9 parity, upstream monitoring, dynamic categories |
| Remove (outdated) | 2 items | 21 SDLC agents section, old claims |
| Fix (badges/ToC) | 3 items | test badge, ToC entries, license block |

**Total estimated README line change**: ~+150 lines added, ~-80 lines removed

---

**Reply with "APPROVED - apply README changes" to proceed with updating README.md.**
**Or provide specific feedback on any section above.**
