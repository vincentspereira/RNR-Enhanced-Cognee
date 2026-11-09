# Full verification matrix

All commands ran from /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024.
PASS below means the stated check only, not unrestricted production acceptance.
Script-reported flags are preserved even where independent evidence contradicts them.

## Exact command aliases

### C1

```bash
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python integrations/hermes/deployment/verify_everything.py
```

### C2

```bash
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python .archive/fetch-html-diagnosis/comprehensive-functional-test.py
```

### C3

```bash
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python integrations/hermes/deployment/verify_fleet_memory_tools.py
```

### H

```bash
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python -B docs/reports/audits/2026-10-19-hermes-security/independent-review-2026-11-01/inspect_host.py
```

### P

```bash
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python -B docs/reports/audits/2026-10-19-hermes-security/independent-review-2026-11-01/independent_probes.py
```

### R

```bash
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python -B docs/reports/audits/2026-10-19-hermes-security/independent-review-2026-11-01/probe_read_tools.py
```

### S

```bash
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python -B docs/reports/audits/2026-10-19-hermes-security/independent-review-2026-11-01/scan_branch.py
```

### D

```bash
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python -B docs/reports/audits/2026-10-19-hermes-security/independent-review-2026-11-01/audit_dependencies.py
```

### O

```bash
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python -B docs/reports/audits/2026-10-19-hermes-security/independent-review-2026-11-01/offline_secondary_probes.py
```

### A

```bash
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python -B docs/reports/audits/2026-10-19-hermes-security/independent-review-2026-11-01/offline_security_probe.py
```

A was actually replayed from /home/vincentspereira/.hermes/cache/scratch/cognee_readonly_security_review_89d1be78/probe.py; the archived file is the same probe.
C1/C2/C3 were run without source edits. Parent runners set PYTHONDONTWRITEBYTECODE=1.
No command here is an instruction to rerun a qualification or use sudo.

## Consolidated verifier: every planned check

| # | Check | Command | Actual | Verdict |
|---|---|---|---|---|
| 1 | enhanced-cognee-api.service | C1 | active | PASS for declared scope |
| 2 | enhanced-cognee-postgres.service | C1 | active | PASS for declared scope |
| 3 | enhanced-cognee-qdrant.service | C1 | active | PASS for declared scope |
| 4 | enhanced-cognee-graph.service | C1 | active | PASS for declared scope |
| 5 | enhanced-cognee-cache.service | C1 | active | PASS for declared scope |
| 6 | memory API health | C1 | OK | PASS for declared scope |
| 7 | main assistant memory status | C1 | default | PASS for declared scope |
| 8 | protocol pin | C1 | OK | PASS for declared scope |
| 9 | role accounting-specialist | C1 | 17 tools | PASS for declared scope |
| 10 | role ai-safety-guardrails | C1 | 15 tools | PASS for declared scope |
| 11 | role aiml-engineer | C1 | 17 tools | PASS for declared scope |
| 12 | role backend-developer | C1 | 15 tools | PASS for declared scope |
| 13 | role chief-of-staff | C1 | 15 tools | PASS for declared scope |
| 14 | role cloud-engineer | C1 | 10 tools | PASS for declared scope |
| 15 | role code-implementer | C1 | 15 tools | PASS for declared scope |
| 16 | role code-reviewer | C1 | 15 tools | PASS for declared scope |
| 17 | role context-engineer | C1 | 17 tools | PASS for declared scope |
| 18 | role cross-project-collaborator | C1 | 15 tools | PASS for declared scope |
| 19 | role customer-feedback-analyst | C1 | 17 tools | PASS for declared scope |
| 20 | role data-engineer | C1 | 17 tools | PASS for declared scope |
| 21 | role data-gen-rl | C1 | 17 tools | PASS for declared scope |
| 22 | role debug-specialist | C1 | 15 tools | PASS for declared scope |
| 23 | role deep-research-specialist | C1 | 17 tools | PASS for declared scope |
| 24 | role deliberation-moderator | C1 | 15 tools | PASS for declared scope |
| 25 | role deployment-engineer | C1 | 10 tools | PASS for declared scope |
| 26 | role devops-engineer | C1 | 10 tools | PASS for declared scope |
| 27 | role ecommerce-kdp-publisher | C1 | 17 tools | PASS for declared scope |
| 28 | role educational-content-author | C1 | 17 tools | PASS for declared scope |
| 29 | role fiction-content-author | C1 | 17 tools | PASS for declared scope |
| 30 | role frontend-developer | C1 | 15 tools | PASS for declared scope |
| 31 | role github-collaborator | C1 | 17 tools | PASS for declared scope |
| 32 | role governance-privacy | C1 | 15 tools | PASS for declared scope |
| 33 | role integration-specialist | C1 | 15 tools | PASS for declared scope |
| 34 | role legal-specialist | C1 | 15 tools | PASS for declared scope |
| 35 | role marketing-social-manager | C1 | 17 tools | PASS for declared scope |
| 36 | role media-producer | C1 | 17 tools | PASS for declared scope |
| 37 | role mobile-developer | C1 | 15 tools | PASS for declared scope |
| 38 | role multimedia-producer | C1 | 17 tools | PASS for declared scope |
| 39 | role niche-hunter | C1 | 17 tools | PASS for declared scope |
| 40 | role observability-specialist | C1 | 10 tools | PASS for declared scope |
| 41 | role performance-optimiser | C1 | 10 tools | PASS for declared scope |
| 42 | role print-merch-designer | C1 | 17 tools | PASS for declared scope |
| 43 | role project-orchestrator | C1 | 15 tools | PASS for declared scope |
| 44 | role security-specialist | C1 | 15 tools | PASS for declared scope |
| 45 | role social-work-specialist | C1 | 17 tools | PASS for declared scope |
| 46 | role software-architect | C1 | 15 tools | PASS for declared scope |
| 47 | role technical-consultant | C1 | 17 tools | PASS for declared scope |
| 48 | role technical-writer | C1 | 17 tools | PASS for declared scope |
| 49 | role test-engineer | C1 | 15 tools | PASS for declared scope |
| 50 | role theology-content-author | C1 | 17 tools | PASS for declared scope |
| 51 | role uxui-engineer | C1 | 17 tools | PASS for declared scope |
| 52 | role web-researcher | C1 | 17 tools | PASS for declared scope |
| 53 | main assistant tools | C1 | 17 tools | PASS for declared scope |
| 54 | token renewal timer | C1 | active | PASS for declared scope |
| 55 | daily fleet backup timer | C1 | Sun 2026-11-01 13:16:59 GMT 8h Sat 2026- | PASS for declared scope |
| 56 | Rotation receipt: postgresql | C1 | Root directory PermissionError before receipt checks | NOT VERIFIED |
| 57 | Rotation receipt: valkey | C1 | Root directory PermissionError before receipt checks | NOT VERIFIED |
| 58 | Rotation receipt: qdrant | C1 | Root directory PermissionError before receipt checks | NOT VERIFIED |
| 59 | Rotation receipt: application | C1 | Root directory PermissionError before receipt checks | NOT VERIFIED |
| 60 | Rotation receipt: arcadedb | C1 | Root directory PermissionError before receipt checks | NOT VERIFIED |

Actual final result: complete=false, error_kind=PermissionError; exit 1. No ordinary failed-list summary.

## Functional suite: every original flag

| # | Check | Command | Original flag/output | Independent interpretation |
|---|---|---|---|---|
| 1 | memory: remember (write) | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 2 | memory: get by id | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 3 | memory: correct with version check + history | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 4 | memory: semantic recall | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 5 | memory: retract | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 6 | read tools: advertised exactly | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 7 | read tools: get_stats live | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 8 | read tools: graph traversal (connections) | C2 | OK  | FAIL independently: live payload is HTTP 422 despite script OK |
| 9 | ingest: document chunked and stored | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 10 | ingest: private-address refused | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 11 | analysis: summarize (real model) | C2 | ERR  | FAIL as supplied; seeded investigation passed; original failure retained |
| 12 | analysis: translate | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 13 | analysis: detect-language | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 14 | analysis: consolidation report-only | C2 | ERR  | FAIL as supplied; seeded investigation passed; original failure retained |
| 15 | analysis: budget accounting | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 16 | coordination: coordinator write | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 17 | coordination: 15 tools advertised | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 18 | coordination: library publish correctly reviewer-gated | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 19 | worker/graph: pending drained | C2 | OK  | PASS as scripted; see REPORT.md for assertion limitations |
| 20 | backend: active records back to baseline | C2 | OK 0 | PASS as scripted; see REPORT.md for assertion limitations |

Original suite: {"checks": 20, "complete": false, "failed": ["analysis: summarize (real model)", "analysis: consolidation report-only"]}. Process exit 0 is erroneous.

## Fleet: all 44 catalogue/config checks

| Role | Expected and configured groups | Live advertised count | C3 outcome | Additional H auth scope |
|---|---|---|---|---|
| accounting-specialist | memory_read,ingest,analysis | 17 | PASS | PASS |
| ai-safety-guardrails | memory_read,analysis | 15 | PASS | PASS |
| aiml-engineer | memory_read,ingest,analysis | 17 | PASS | PASS |
| backend-developer | memory_read,analysis | 15 | PASS | PASS |
| chief-of-staff | memory_read,analysis | 15 | PASS | PASS |
| cloud-engineer | memory_read | 10 | PASS | PASS |
| code-implementer | memory_read,analysis | 15 | PASS | PASS |
| code-reviewer | memory_read,analysis | 15 | PASS | PASS |
| context-engineer | memory_read,ingest,analysis | 17 | PASS | PASS |
| cross-project-collaborator | memory_read,analysis | 15 | PASS | PASS |
| customer-feedback-analyst | memory_read,ingest,analysis | 17 | PASS | PASS |
| data-engineer | memory_read,ingest,analysis | 17 | PASS | PASS |
| data-gen-rl | memory_read,ingest,analysis | 17 | PASS | PASS |
| debug-specialist | memory_read,analysis | 15 | PASS | PASS |
| deep-research-specialist | memory_read,ingest,analysis | 17 | PASS | PASS |
| deliberation-moderator | memory_read,analysis | 15 | PASS | PASS |
| deployment-engineer | memory_read | 10 | PASS | PASS |
| devops-engineer | memory_read | 10 | PASS | PASS |
| ecommerce-kdp-publisher | memory_read,ingest,analysis | 17 | PASS | PASS |
| educational-content-author | memory_read,ingest,analysis | 17 | PASS | PASS |
| fiction-content-author | memory_read,ingest,analysis | 17 | PASS | PASS |
| frontend-developer | memory_read,analysis | 15 | PASS | PASS |
| github-collaborator | memory_read,ingest,analysis | 17 | PASS | PASS |
| governance-privacy | memory_read,analysis | 15 | PASS | PASS |
| integration-specialist | memory_read,analysis | 15 | PASS | PASS |
| legal-specialist | memory_read,analysis | 15 | PASS | PASS |
| marketing-social-manager | memory_read,ingest,analysis | 17 | PASS | PASS |
| media-producer | memory_read,ingest,analysis | 17 | PASS | PASS |
| mobile-developer | memory_read,analysis | 15 | PASS | PASS |
| multimedia-producer | memory_read,ingest,analysis | 17 | PASS | PASS |
| niche-hunter | memory_read,ingest,analysis | 17 | PASS | PASS |
| observability-specialist | memory_read | 10 | PASS | PASS |
| performance-optimiser | memory_read | 10 | PASS | PASS |
| print-merch-designer | memory_read,ingest,analysis | 17 | PASS | PASS |
| project-orchestrator | memory_read,analysis | 15 | PASS | PASS |
| security-specialist | memory_read,analysis | 15 | PASS | PASS |
| social-work-specialist | memory_read,ingest,analysis | 17 | PASS | PASS |
| software-architect | memory_read,analysis | 15 | PASS | PASS |
| technical-consultant | memory_read,ingest,analysis | 17 | PASS | PASS |
| technical-writer | memory_read,ingest,analysis | 17 | PASS | PASS |
| test-engineer | memory_read,analysis | 15 | PASS | PASS |
| theology-content-author | memory_read,ingest,analysis | 17 | PASS | PASS |
| uxui-engineer | memory_read,ingest,analysis | 17 | PASS | PASS |
| web-researcher | memory_read,ingest,analysis | 17 | PASS | PASS |

Group counts: {"memory_read": 5, "memory_read,analysis": 17, "memory_read,ingest,analysis": 22}.
Main has memory_read,ingest,analysis: 17 MCP tools, plus a separate eight-tool native provider.
Discovery is not proof that every advertised tool call succeeds.

## Live calls to all ten memory_read tools

| Tool | Command | HTTP error status | MCP isError | Result |
|---|---|---|---|---|
| recall | R | - | false | Non-error payload returned |
| get_memories | R | - | false | Non-error payload returned |
| get_memory | R | - | false | Non-error payload returned |
| get_memory_history | R | - | false | Non-error payload returned |
| get_related | R | 422 | false | FAIL: Invalid memory fields; check the API contract |
| list_agents | R | - | false | Non-error payload returned |
| get_shared_memories | R | 403 | false | FAIL: Permission denied: 'memory:admin' is required (caller role 'api_client' lacks it). |
| library_membership | R | 403 | false | FAIL: Permission denied: 'memory:admin' is required (caller role 'api_client' lacks it). |
| get_stats | R | - | false | Non-error payload returned |
| health | R | - | false | Non-error payload returned |

One invented fixture, then versioned retraction, HTTP 404 readback and active rows=0.

## Independent bounded live probes

| Probe | Command | Actual selected output |
|---|---|---|
| manual_legal_specialist_mcp_names | P | `{"count": 15, "names": ["detect_language", "find_consolidation_candidates", "get_memories", "get_memory", "get_memory_history", "get_related", "get_shared_memories", "get_stats", "get_summarization_status", "health", "library_membership", "list_agents", "recall", "summarize_memories", "translate_text"], "passed": true}` |
| manual_legal_specialist_auth_call | P | `{"isError": false, "passed": true}` |
| manual_unoffered_tool_refused | P | `{"passed": true}` |
| malformed_params_empty_list | P | `{"reply_received": true, "server_alive": true}` |
| malformed_params_nonempty_list | P | `{"exit_code": 1, "server_alive": false}` |
| empty_scope_summarize | P | `{"fixed_detail": "Nothing to summarize", "status": 422}` |
| empty_scope_consolidation_candidates | P | `{"fixed_detail": "Too few records to compare", "status": 422}` |
| paced_fixture_write_1 | P | `{"id_present": true, "status": 200}` |
| paced_fixture_readback_1 | P | `{"passed": true}` |
| paced_fixture_write_2 | P | `{"id_present": true, "status": 200}` |
| paced_fixture_readback_2 | P | `{"passed": true}` |
| llm_route_status | P | `{"configured": true, "daily_token_cap": 50000, "model": "GLM-5.3-Flash", "status": 200, "used_today": 346}` |
| seeded_summary_investigation | P | `{"fixed_detail": null, "record_id_present": true, "seconds": 13.573, "sources": 2, "status": 200, "summary_present": true, "tokens_used": 568}` |
| seeded_summary_readback | P | `{"passed": true}` |
| seeded_consolidation_investigation | P | `{"compared": 3, "fixed_detail": null, "report_only": true, "status": 200, "tokens_used": 580}` |
| audit_fixture_retraction | P | `{"readback_state": null, "readback_status": 404, "status": 200}` |
| audit_fixture_retraction | P | `{"readback_state": null, "readback_status": 404, "status": 200}` |
| audit_fixture_retraction | P | `{"readback_state": null, "readback_status": 404, "status": 200}` |
| audit_scope_clean_readback | P | `{"active_rows": 0, "passed": true}` |

## Offline/source probes

O: see offline-secondary-probes.json. A: see offline-security-receipt.json.
These use invented fake networking/model/store responses; they do not exploit the deployed service.
S: branch-history scan; D: public lockfile OSV lookup; full outputs retained as JSON.
System metadata commands and output are preserved in the .txt files and summarised in REPORT.md.
