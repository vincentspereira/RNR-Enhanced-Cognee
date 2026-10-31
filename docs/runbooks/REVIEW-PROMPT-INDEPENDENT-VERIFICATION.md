# Independent review prompt: Enhanced Cognee fleet memory delivery

Copy the prompt below into the reviewing agent. It is sanitized: no
passwords, tokens, keys or private profile contents. The reviewer needs
command access to Ubuntu-Hermes as vincentspereira; the few root-side
checks are marked OWNER and need Vincent's terminal.

---

You are an independent reviewer. Another agent delivered Enhanced Cognee
as the extended memory for the Hermes Agent main assistant and its
40-bot fleet on this host (Ubuntu-Hermes). Your job is to verify with
fresh eyes that everything works as expected and to find anything that
was missed, mis-stated or left inconsistent. You are NOT continuing the
delivery; you are auditing it. Report findings honestly, including
criticisms - the value of this review is independence.

## Ground rules

- Read the repository AGENTS.md first. ASCII-only output. Never print
  or copy secrets, token values, key material or raw profile contents.
- Treat every file under /opt, /etc/enhanced-cognee, /var/lib/enhanced-
  cognee* and the profile .env files as read-only evidence.
- Do NOT: activate bots or fleet admission, merge to main, rotate or
  re-run any credential family, re-run completed native/memory
  qualification tests, restart services without need, modify profiles,
  or "fix" anything you find - report it instead. The delivery branch is
  codex/hermes-ubuntu-deployment-launch-20261024; do not push to it.
- Verification must be evidence-based: run the commands, paste real
  output. Do not trust the documentation without executing checks.

## What is claimed to be delivered (verify all of it)

Authoritative record: docs/reports/audits/2026-10-19-hermes-security/
ENGAGEMENT-COMPLETE-2026-11-01.md on branch
codex/hermes-ubuntu-deployment-launch-20261024 (worktree
/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/
launch-worktree-20261024). Claims in brief:

1. Protected stack: 5 systemd services (postgres, qdrant, graph/
   ArcadeDB, cache/valkey, api on 127.0.0.1:28080) plus index worker.
2. Memory provider (8 enhanced_* tools, automatic capture/recall) for
   the main assistant and all 40 profiles under
   /home/vincentspereira/.hermes/profiles/ (canaries retired).
3. MCP server at ~/.hermes/mcp-servers/enhanced-cognee/server.py with
   per-role tool groups: memory_read (10 tools) for all; +ingest,+analysis
   for 19 roles; +analysis for 12; ops roles read-only; coordinators
   memory_read,analysis (library tools deliberately reviewer-gated);
   main assistant (gateway home config) memory_read,ingest,analysis.
4. Service API endpoints: ingestion, summarize/consolidation/status,
   translate, detect-language, plus the original memory CRUD/recall/
   share/library routes. LLM route GLM-5.3-Flash via root-only
   /etc/enhanced-cognee/llm.json, per-project 50k token/day cap.
5. Automation: weekly token renewal timer ec-hermes-memory-token-renew
   (Mondays 04:00, 7-day window); daily encrypted fleet backup timer.
6. Credential rotation complete for 5 families (postgresql, valkey,
   qdrant, application issuer, arcadedb) with receipts under
   /var/lib/enhanced-cognee-rotation/candidate-*/execution-*.json.
7. Governance protections verified: per-profile 120 req/min budget;
  clarification gate on rapid automated writes; library publication
  requires memory:admin (role tokens refused by design); ingestion
  refuses non-public addresses.

## Verification commands (run these yourself)

As vincentspereira (no root needed):

  cd /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024

  # 1. Consolidated verifier: EXPECT {"complete": true, "failed": []}.
  # (Without sudo the 5 rotation-receipt lines read False; all other 51
  # checks must pass. With OWNER sudo below, all 56 pass.)
  /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python \
    integrations/hermes/deployment/verify_everything.py

  # 2. Functional suite, 20 checks across every family (memory CRUD,
  # read tools, ingest + refusal guard, analysis incl. real model call,
  # coordination governance refusal, worker health). EXPECT complete.
  /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python \
    .archive/fetch-html-diagnosis/comprehensive-functional-test.py

  # 3. Per-role tool verification (config + live spawn per role).
  /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/.venv-deployment/bin/python \
    integrations/hermes/deployment/verify_fleet_memory_tools.py

OWNER (Vincent's terminal, paste-only summaries back):

  # 4. Full 56-check verifier as root (adds rotation receipts).
  sudo .../venv-deployment/bin/python .../verify_everything.py

  # 5. Renewal state: /opt/enhanced-cognee-memory/fleet-renewal/state.json
  #    (shows last run, renewed/skipped, expiry per profile).
  sudo cat /opt/enhanced-cognee-memory/fleet-renewal/state.json | head -20

## Deep-review checklist (beyond the scripted checks)

- Consistency: does ENGAGEMENT-COMPLETE-2026-11-01.md match reality?
  Spot-check at least 5 claims against live state (paths, unit names,
  tool counts, timer schedules, receipt files).
- Code review: read integrations/hermes/enhanced_cognee_mcp/server.py
  and src/{ingestion,llm_summarize}.py + the new memory_api endpoints.
  Look for: secret leakage into logs/receipts, missing input bounds,
  auth gaps, error paths that mis-report success.
- Security posture: confirm no credential values in git (run a fresh
  secret scan over the branch); confirm profile tokens are only in
  0600 .env files; confirm the LLM key exists only in /etc root-only.
- Per-role spot checks: pick 3 roles from different groups; open their
  config.yaml mcp_servers.enhanced_cognee args and confirm the group
  matches the matrix in the engagement doc section 3.5.
- MCP live behavior: for one role, spawn the server with its token and
  verify tools/list matches the group exactly (the scripted verifier
  does this for all 40; do one manually to validate the validator).
- Rate limit and gates: one paced write loop (stay under 120/min) to
  confirm normal writes succeed; a single library publish attempt with
  a role token must get 403 memory:admin.
- Renewal math: check state.json expiries are inside the 30-day window
  and the timer next-fire is Monday 04:00 +/- jitter.
- Gap hunt (the real point of this review): anything NOT covered above
  that a production memory backend for a 40-bot fleet should have.
  Consider: monitoring/alerting, restore drill recency, log rotation,
  disk headroom for stores/backups, dependency CVE recheck, gateway
  restart resilience of MCP children, token renewal edge cases
  (gateway restart mid-renewal), documentation drift.

## Known open items (do not re-report as new findings; assess whether
they were handled honestly)

- Main merge not done (deliberate; delivery branch only).
- Remote MCP endpoints (context7, deepwiki) qualified but not enabled
  for fleet profiles.
- Structured/DB ingestion and deeper ops metrics: documented future
  items. Live long-session max-context capture test: documented
  protocol, owner-run. Library publication by bots: governance decision
  pending owner (reviewer-credential path documented).
- Hosted CI not green for the newest helpers (no gh auth in the
  delivery environment); unit tests all pass locally.

## Reporting

Produce a report with: (a) verification matrix - each check, command,
actual output summary, pass/fail; (b) findings - each with severity,
evidence, and the minimal fix; (c) gaps found in the gap hunt;
(d) overall verdict. Distinguish verified facts from opinions. If any
scripted check fails, preserve the output and investigate the cause
before concluding - do not retry destructive actions.
