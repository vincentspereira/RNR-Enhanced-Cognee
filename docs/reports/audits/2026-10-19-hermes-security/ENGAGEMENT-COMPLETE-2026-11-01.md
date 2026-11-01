# Enhanced Cognee Engagement Record - Complete Delivery

Status date: 1 November 2026. Environment: Ubuntu-Hermes (isolated WSL
distro). Delivery branch: codex/hermes-ubuntu-deployment-launch-20261024,
head 96153d35, fully pushed to github.com/vincentspereira/RNR-Enhanced-Cognee.
Final verification: 56/56 checks green via verify_everything.py.

## 1. Goal and outcome

Goal: Enhanced Cognee as the extended memory for the Hermes Agent main
assistant and its entire bot fleet (40 roles), with governed writes,
scoped credentials, and every capability family delivered per the
approved role matrix.

Outcome: DELIVERED AND VERIFIED. The main assistant and all 40 bots run
Enhanced Cognee as memory with per-role toolsets; the backend is a
qualified protected stack; all five backend credential families are
rotated or proven current; token renewal and daily encrypted backups run
automated; one rerunnable command (verify_everything.py) re-proves all
56 checks.

## 2. Architecture as delivered

Component layout (all on Ubuntu-Hermes):

- Protected memory service stack (root-owned, systemd):
  enhanced-cognee-postgres (canonical store, schema 3, port 28434),
  enhanced-cognee-qdrant (vector index, 28535), enhanced-cognee-graph
  (ArcadeDB, 28536), enhanced-cognee-cache (valkey, unix socket),
  enhanced-cognee-api (restricted memory API, 127.0.0.1:28080), and
  enhanced-cognee-index (derived-index worker). Data directories under
  /var/lib/enhanced-cognee/{postgres,qdrant,arcade,valkey}; encrypted
  backups under /var/backups/enhanced-cognee.
- One shared stack, logical isolation: every bot addresses only its own
  project space inside the single PostgreSQL store (tenant
  hermes_gateway, project per role) via its scoped JWT. Qdrant/ArcadeDB
  hold derived indexes replayed from canonical by the worker.
- Fleet gateway: Hermes runs from
  /home/vincentspereira/agent-workspace/hermes-agent (upstream
  checkout); the Hermes Agent Desktop connects via SSH to
  127.0.0.1:2222 as vincentspereira. Profiles live in
  /home/vincentspereira/.hermes/profiles/<role> (40 roles; the two
  canary profiles were retired and archived).
- Memory provider plugin (8 tools, automatic) installed at
  /home/vincentspereira/.hermes/plugins/enhanced_cognee/ and staged
  into every profile's own plugins dir (profiles scan their own).
- Stage-C MCP server (pure stdlib) at
  /home/vincentspereira/.hermes/mcp-servers/enhanced-cognee/server.py,
  spawned per profile by the gateway with each role's token from its
  .env via the secret-scope ${...} rendering.
- LLM route A (approved): GLM-5.3-Flash via
  https://open.bigmodel.cn/api/coding/paas/v4; key in root-only
  /etc/enhanced-cognee/llm.json, loaded through the daemon credential
  whitelist as ENHANCED_LLM_* env; per-project daily token cap 50000.

## 3. Delivery phases and how each was done

### 3.1 Protected runtime and native binding

- Managed MCP runtime install: sealed 464,097,280-byte payload (5005
  members, SHA256 68a0325f...e521) installed into the protected Hermes
  release (python 3.14.7 + uv 0.12.3) via a guarded owner-terminal
  installer; a umask defect (directories created 0700) was reconciled by
  a hash-verified mode correction (233 directories) and the
  restricted-identity proof passed under the actual UID 992.
- Native MCP binding qualification (operator unit + hardened transient
  units as the restricted identity): stdio definitions resolved through
  the release's own _resolve_stdio_command (Fetch via managed uvx, 1
  tool, 2 private-address denials; Filesystem via managed npx, 14
  tools); remote HTTP endpoints (context7: 2 tools, deepwiki: 3 tools)
  qualified via a streamable-HTTP MCP client stage. Receipts carry
  names/counts only - never URLs or header values.

### 3.2 Memory provider for the main assistant and fleet

- Live main profile of the protected deployment inspected read-only
  under the restricted identity: memory.provider already
  enhanced_cognee (config hash pinned).
- Gateway fleet: provider plugin staged and discovered; tokens issued
  per profile by provision_gateway_profile_access.py (issuer-signed
  HS256, identity tenant=hermes_gateway project=<role>, denial checks
  for unauthenticated/expired/altered tokens, atomic .env publication
  chowned to the gateway identity, 30-day TTL). Hyphenated role names
  map to canonical underscored memory-space IDs (backend rule).
- First live proof: explicit remember stored record 28f557e8; a fresh
  session received automatic recall injection and answered the test
  phrase exactly. A policy gate refused the first malformed write
  attempt (guardrails enforcing on live writes).

### 3.3 Stage C - API-backed read tools (10)

Server: pure-stdlib stdio MCP server; tools: recall, get_memories,
get_memory, get_memory_history, get_related, list_agents,
get_shared_memories, library_membership, get_stats, health. End-to-end
pilot verified under the web-researcher token (handshake, exact
advertisement, authenticated status, real recall). Error responses
surface the API's detail (e.g. private-address refusal reason).

### 3.4 Stage D - capability families

- Family 1 ingestion: service endpoint POST /v1/memories/ingest
  (paragraph chunking 32-chunk budget, public-address guard on every
  resolved IP, redirect-free bounded fetch, stdlib HTML strip) storing
  through the normal remember() admission with origin=ingest
  provenance. MCP tools ingest_url/ingest_text. Verified live:
  document stored+listed, loopback refused, version-checked retraction.
- Family 2 graph: complete by architecture - the index worker drains
  the change feed continuously (worker running, pending 0, graph
  source_linked_graph); traversal (get_related) and visibility
  (get_stats) already served; legacy cognify/extract/compact are the
  monolith's manual-batch equivalents, redundant here.
- Family 3 summarize/organize: POST /v1/memories/summarize (stores an
  origin=summarize digest in the same encrypted space),
  /v1/memories/consolidation/candidates (report-only duplicate
  detection), GET /v1/memories/summarization/status (route+budget
  state). Live-verified with a real GLM-5.3-Flash summary and budget
  accounting.
- Family 4 language: POST /v1/memories/translate (returns, never
  stores), /v1/memories/detect-language (Unicode-script heuristic, no
  model). Live-verified (French translation, Cyrillic detection).
- Coordination group: publish_to_library, revoke_library_publication
  (version-checked reviewed-library API), set_memory_sharing - enabled
  for the four coordinator roles.
- Deliberate protections verified on live traffic: per-profile
  120 requests/minute budget (429), and a clarification gate that
  holds rapid automated write bursts for a sanitized summary (the
  anti-transcript-dump design).

### 3.5 Role matrix (all 40 roles, live-verified per role)

Groups: memory_read (10 tools) for all; +ingest (2); +analysis (5);
+coordination (3). Main assistant: all 20 tools (coordinator-grade).

| Group | Roles |
|---|---|
| memory_read,ingest,analysis (17-18 tools) | web-researcher, deep-research-specialist, niche-hunter, educational-content-author, fiction-content-author, theology-content-author, technical-writer, technical-consultant, marketing-social-manager, customer-feedback-analyst, ecommerce-kdp-publisher, print-merch-designer, multimedia-producer, uxui-engineer, github-collaborator, context-engineer, aiml-engineer, data-engineer, data-gen-rl |
| memory_read,analysis (15 tools) | backend-developer, frontend-developer, mobile-developer, code-implementer, code-reviewer, debug-specialist, test-engineer, integration-specialist, software-architect, security-specialist, governance-privacy, ai-safety-guardrails |
| memory_read,analysis,coordination (18 tools) | chief-of-staff, project-orchestrator, cross-project-collaborator, deliberation-moderator |
| memory_read (10 tools; ops by design) | devops-engineer, deployment-engineer, cloud-engineer, observability-specialist, performance-optimiser |

Future (documented, not built): structured/DB ingestion (data roles),
deeper ops metrics (ops roles).

### 3.6 Automation

- Token renewal: systemd timer ec-hermes-memory-token-renew (Mondays
  04:00, persistent, 5m jitter); root-side pinned job renews only
  profiles inside their final 7 days via the audited provisioner;
  first unattended run verified (default renewed to 2026-11-29, 40
  roles correctly skipped). Provisioner accepts the renewal unit's
  cgroup as operator provenance (SUDO_USER absent under systemd).
- Daily encrypted fleet backups: enhanced-cognee-qualified-fleet-
  backup-v2.timer (running; next fire verified).
- Canary retirement: both test profiles archived to
  ~/.hermes/profile-archive and removed (registry, profiles, Desktop);
  verified 40 roles remain.

### 3.7 Credential rotation (all five families, receipts retained)

Executed family-by-family by execute_staged_rotation.py (owner sudo;
per-family verify + automatic rollback; every refusal ever encountered
rolled back fully - the fleet was never half-rotated):

- postgresql: roles rotated under operator rights (operator.json DSN;
  legacy operator name kept with the staged operator secret);
  api.json/index.json already current; api healthy.
- valkey: three users rotated; the formerly disabled memory_worker
  renamed-and-enabled as the staged ec_api user; every AUTH verified
  via RESP (unix socket from valkey.conf).
- qdrant: both service keys proven already current (verified no-op).
- application: issuer JWT key proven already current by dual-HMAC
  verification (token verifies with old AND new only when equal);
  operator file consistent; fleet tokens untouched.
- arcadedb: staged operator secret replaced the forgotten root
  password (root name preserved); ec_api/ec_worker verified
  already-current live; worker.json unchanged (already current).

Root causes closed with live evidence (arcadedb): the salt FIELD TEXT
is used as raw salt bytes (never base64-decoded; brute-proven against
the worker's live known-good pair), and /api/v1/server hangs for valid
non-admin credentials while degrading the server to 403-everything -
verification must use the command endpoint with a not-401/403
criterion. Other key lessons baked into helpers: daemon credential
whitelist (CREDENTIALS_DIRECTORY never reaches the app; llm.json loads
via credential_environment as ENHANCED_LLM_*), MemoryScope.project
attribute, list_records results key, per-service file ownership
(valkey ACL and arcade users files must stay service-owned), qdrant
keys live in a JSON-in-.yaml config under service.*, and authenticated
route probes (the auth boundary answers 401 before routing).

### 3.8 Verification tooling (rerunnable)

- verify_fleet_memory_tools.py - per-role config + live server spawn
  proving the exact advertised toolset (40/40 + home).
- verify_everything.py - the consolidated 56-check command: five
  backend services, API health, main-assistant authenticated status,
  live per-role toolsets, renewal timer, backup timer, all five
  rotation receipts (latest receipt per family by timestamp).
- Historical evidence: sanitized receipts under
  docs/reports/audits/2026-10-19-hermes-security/ and root-side
  operator-evidence directories; every phase's receipt chain retained.

## 4. Boundaries maintained throughout

No fleet admission policies were enabled beyond the reviewed rollout;
no main merge; scoped tokens only (admin families operator-only by
design); no secrets in logs, receipts, prompts or git (a redacted
git-history scan closed audit F22: no structural provider keys; three
fingerprints recorded as defaults/templates). All owner-terminal
actions used fixed prepared commands; the agent never held a secret
value.

## 5. Post-completion comprehensive testing (1 November 2026)

Two suites, both green:

- Consolidated verifier: 56/56 (backends, API, main assistant, all 40
  roles live-proven per matrix, timers, all five rotation receipts).
- Functional suite (20 checks, real paths and tokens): memory CRUD
  (write, get, version-checked correction with history, semantic recall,
  retraction), MCP read tools (exact advertisement, live status, graph
  traversal), ingestion (document chunked and stored; private-address
  refused), analysis (real GLM-5.3-Flash summarize with token
  accounting, translate returned-not-stored, Cyrillic detect-language,
  report-only consolidation, budget state), coordination, worker/graph
  health (pending drained, source-linked graph), and clean state after.

Governance correction found and applied by the testing itself: the
library publication endpoints are permission-gated to memory:admin
(the fleet-memory reviewed-sharing design - a separate reviewer
credential, never given to an agent). Exposing publish/revoke tools to
coordinator role tokens was a wiring error on my side; the API's 403
refusal was the architecture working correctly. The coordination group
was removed from role enablement (coordinators and the main assistant
now carry memory_read[,ingest],analysis; the three library tools remain
in the server for use with a future reviewer credential only). The
functional suite now asserts the refusal itself as the expected
behavior. If direct bot publication is ever wanted, the correct path is
an owner-issued reviewer credential or a reviewed-proposal endpoint -
an explicit owner decision, not a silent permission change.

## 6. Fleet expansion: four specialist roles (1 November 2026)

The owner created four new profiles (media-producer, accounting-
specialist, legal-specialist, social-work-specialist; roster now 44
unique roles). Memory onboarding completed the same way as the original
fleet: the memory provider plugin staged into each profile's own
plugins/enhanced_cognee directory (profile-scoped discovery), the MCP
server definition confirmed in each config.yaml with per-role groups
(media-producer/accounting-specialist/social-work-specialist:
memory_read,ingest,analysis; legal-specialist: memory_read,analysis -
matching the approved matrix logic), scoped tokens issued into each
profile's own .env by the audited provisioner - initially at the
default 7-day TTL (owner question caught it), reissued at the
fleet-standard 30 days - and the enablement role table extended to
44 with the verifiers updated (the per-role verifier now requires 44
and live-spawns every role including the four new ones). The renewal
job's profile list now unions the enablement role table with the
batch receipts (which were updated with a backup to include the
four), so all 44 bots auto-renew inside their final 7 days.
