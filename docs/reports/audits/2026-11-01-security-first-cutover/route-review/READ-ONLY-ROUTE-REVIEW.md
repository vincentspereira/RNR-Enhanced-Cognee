# Independent read-only route review: security-first cutover

## Verdict

PASS, source-scoped and conditional: withholding llm.json is sufficient to keep
all optional backend chat/analysis dispatch OFF in the reviewed API WHEN the new
process is launched through the reviewed memory_daemon api sanitizer and the
manager actually supplies no llm.json credential. Canonical memory, local
embeddings, index reads and normal CRUD do not depend on that credential.

BLOCKED for installed-state acceptance or restart: removing one LoadCredential
line from a unit is not by itself proof of either condition. The existing
process keeps its startup route; an eventual explicitly approved API restart is
necessary. Unknown protected drop-in directives still require owner-root
metadata review. No restart, reload, installation or protected change was made
or is authorized by this report.

This is not a blanket no-network or no-model assertion: ordinary embeddings
still execute the admitted local ONNX model. Configured database/index/OIDC and
explicit public URL ingestion can perform network work; they are not optional
chat fallback. Hermes' own answer-generation route is a separate system.

## Source and evidence boundary

- Worktree: /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/security-first-cutover-worktree-20261101
- Observed HEAD: 41e4de7a5db99970a7629ef3f274138eef3031e8.
- Reviewed application source: c14f595ccd53f432b455b16f116765d9aa6c9a14.
  The offline receipt binds 29 source/template files to that commit with SHA-256
  and exact byte equality, including the 26-module local import closure.
- Supplied installed-state context, NOT reverified here: OLD candidate
  21abf4857ca8dce8e0a3aafc725266c8d3754529; staged NEW
  /opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101; eight staged
  hashes/imports already passed as the actual API account. That is not evidence
  of an activated service, an inspected cutover helper or an updated shared MCP.
- Supplied unit context, NOT reverified here: enhanced-cognee-api User/Group,
  DynamicUser=yes, current UID 63764 only, ProtectSystem=strict, StateDirectory
  unset; root20-launch-runtime.conf has unknown extra directives.
- Read only applicable instructions and application/MCP/deployment source. Did
  not read .env, private JSON values, raw live profiles, process environments,
  protected drop-in contents, real memories or the implementation agent's new
  helper/tests/progress. No qualification reruns, server imports/startup,
  network/model calls, systemd operations, bot/profile edits or source edits.
- No source-review acceptance is given to any implementation helper or tests.

## Exact route trace and why the source result holds

1. Initial launch consumes the manager directory, not a guessed credential path.
   memory_daemon.main reads CREDENTIALS_DIRECTORY, calls
   credential_environment(role, directory), and execve replaces the process with
   uvicorn src.memory_api:app and the explicitly constructed environment
   (src/memory_daemon.py:131-144). The proposed outer -I -B flags apply to the
   launcher; its child argv does NOT repeat those flags. Child bytecode writes
   are disabled by PYTHONDONTWRITEBYTECODE. Protected installed interpreter,
   module paths and working directory remain deployment prerequisites.

2. Inherited model/fallback environment does not reach the API child.
   credential_environment starts with ONLY LANG, LC_ALL and TZ from os.environ,
   then adds the validated role JSON and fixed production flags
   (src/memory_daemon.py:80-94,124-128). Inherited ENHANCED_LLM_*, OPENAI_API_KEY,
   LLM_PROVIDER, LLM_MODEL, PYTHONPATH, HOME and CREDENTIALS_DIRECTORY are not
   copied. api.json may contain only _API/_COMMON fields; route fields,
   CREDENTIALS_DIRECTORY and ENHANCED_LOAD_DOTENV are forbidden
   (src/memory_daemon.py:13-19,80-90). Values are strings, not interpolated
   environment assignments or shell commands. Duplicate keys are refused.

3. Only the optional llm.json path adds route environment and the fixed budget
   path (src/memory_daemon.py:95-123). With it absent, those assignments do not
   happen. Keeping the original /etc/enhanced-cognee/llm.json untouched does not
   matter: the launcher checks only its supplied private directory, not /etc.
   No inherited provider default, default local server or paid endpoint is used.

4. API lifespan first verifies production auth, explicit JWT/OIDC verification,
   persistent encryption and the explicit PostgreSQL URL; it then constructs
   optional local embeddings and readonly derived sinks, checks schema 3, and
   only afterward selects the optional route (src/memory_api.py:126-165;
   src/memory_keys.py:63-78; src/memory_service.py:144-147).
   Its expression is load_route_env() OR load_route(CREDENTIALS_DIRECTORY).
   After the daemon's execve, both route variables and CREDENTIALS_DIRECTORY are
   absent. load_route_env returns None when all three route fields are absent;
   load_route(None) returns None (src/llm_summarize.py:33-63). Thus llm_route=None
   and no TokenBudget object is constructed. Importing its class creates no
   ledger (src/llm_budget.py:22-35).

5. IMPORTANT bypass boundary: direct uvicorn/API startup can use inherited
   ENHANCED_LLM_* or the fallback CREDENTIALS_DIRECTORY/llm.json. The latter
   loader is not the daemon's private-file/allowlist verifier
   (src/llm_summarize.py:55-85). Withholding only a systemd file is NOT a universal
   kill switch for arbitrary launchers or an already running process. A partial
   invalid route raises and can fail startup, rather than silently selecting a
   fallback. Effective entrypoint and absence of alternate routing must be
   proven before activation.

6. The admitted API has exactly three model dispatch endpoints: summarize,
   consolidation/candidates and translate. Each calls _llm before source reads
   or prompt construction. _llm rejects route=None, or budget=None, before
   dispatch (src/memory_api.py:274-283,313-327,348-367). All three then use
   budgeted_chat, whose reservation precedes chat
   (src/llm_summarize.py:88-105). No automatic summary task starts in lifespan.
   detect-language is a script heuristic only
   (src/memory_api.py:369-372; src/llm_summarize.py:152-192).

7. No alternate model tool is exposed through canonical aliases. The admitted
   alias set delegates to MemoryService; unknown analysis/admin/legacy tools are
   refused, not routed to legacy code (src/canonical_adapters.py:20-22,38-43,
   59-94,135-163; src/security/tool_policy.py:22-39). Static traversal of all
   imports, including imports inside functions, found no dotenv, Cognee model
   stack, OpenAI, LiteLLM, intelligent_summarization, auto_configuration or
   advanced_search_reranking dependency in the selected local closure. This
   does not certify arbitrary installed .pth/site hooks, dependency binaries,
   another running service or an unreviewed wrapper.

## Normal memory, embeddings and index settings

- Remember/get/correct/retract/recall/list/status/connections delegate to the
  canonical store independently of llm_route (src/memory_api.py:245-247,374-435).
  Encryption, scope, history/version checks and schema prerequisites remain.
  Missing/wrong API settings can still prevent startup; route withholding does
  not bypass any protected-store prerequisite.
- LocalEmbeddings accepts only BAAI/bge-small-en-v1.5 and verifies the pinned
  local model bytes, then uses CPUExecutionProvider. There is no hub download,
  remote inference or alternate-model fallback
  (src/local_embeddings.py:14-24,27-38,41-68,70-90).
  Remember, correction and recall call that embedder when configured
  (src/memory_service.py:249,359-360,426-430). No llm credential is consulted.
- Retain api.json AND index.json in Phase A. The daemon does not merge index.json
  into its environment: ENHANCED_INDEX_CONFIG from api.json names the bounded
  absolute index settings file. IndexSettings forbids extra fields and contains
  no LLM route keys; its model field is an embedding identity, not chat routing
  (src/index_runtime.py:17-39). Retaining the index credential alone is therefore
  not enough unless that reference resolves correctly in the new mount.
- Configured readonly sinks require the same embedding model as the API;
  mismatch fails startup (src/memory_api.py:139-150). API sinks use explicit
  origins, trust_env=False and follow_redirects=False, with no Valkey client in
  readonly mode (src/index_sinks.py:19-27,35-62).
- Without an embedding setting the API uses text recall; without indexes graph
  is unavailable. These are not chat fallbacks, but would violate an intended
  semantic/graph configuration if accidentally lost. Existing index worker and
  its separate credentials are outside the Phase A change. A stale worker can
  yield graph 503 while canonical recall remains available
  (src/memory_service.py:497-502; src/recall_service.py:29-36,62-67).
- Explicit URL ingestion still fetches bounded public text and delegates writes
  to remember; it is not LLM extraction (src/ingestion.py:1-9,180-218,243-255).
  Withholding llm.json is not an egress firewall or proof that configured index,
  database or OIDC destinations are local/authorized.

## Temporary endpoint contract

These are source-derived results for authenticated, authorized, admitted valid
requests. Middleware/validation can return 401/403/408/413/422/429/503 earlier.
POST analysis and detect-language currently require MEMORY_WRITE through the
method fallback, not merely the MCP analysis group name
(src/security/http_boundary.py:63-99; src/security/enterprise_auth.py:459-493).

| Endpoint | Expected no-route result | Effect |
| --- | --- | --- |
| POST /v1/memories/summarize | 422, detail: The model route is not configured for this service | No store read or model dispatch |
| POST /v1/memories/consolidation/candidates | Same 422/detail | No store read or model dispatch |
| POST /v1/memories/translate | Same 422/detail | No model dispatch |
| GET /v1/memories/summarization/status | 200, configured=false; model, daily_token_cap, used_today=null; scoped project_id | No budget access when absent |
| POST /v1/memories/detect-language | 200 for valid allowed request, method=script_heuristic | No model |
| Normal CRUD/read/recall/status | Existing endpoint semantics | Not disabled by missing route |

LlmUnavailable subclasses ValueError, so the temporary unavailability is 422,
NOT the generic exception handler's 503
(src/llm_summarize.py:29-30; src/memory_api.py:214-227). Do not describe these
refusals as successful analysis, a health failure or a transient retry loop.

## MCP compatibility gate

The current reviewed shared MCP source is
integrations/hermes/enhanced_cognee_mcp/server.py, SHA-256
7013cb6aa87afda4b0f80bae20ed7a8e29067c5693751fdf9eb90cf767e3bb20.
Installed shared MCP bytes were NOT inspected, and the OLD API revision does not
contain this MCP path. For historical contrast only, the receipt binds the MCP
at c14f595c's parent to its full ref/hash; that is not an installed-version claim.

Required compatibility:

- summarize_memories now requires explicit record_ids (1-50 unique nonempty
  bounded IDs); category/limit are forbidden API fields. Results are returned,
  NOT automatically stored. consolidation requires 2-50 selected record_ids
  (src/memory_api.py:46-65,288-325;
  integrations/hermes/enhanced_cognee_mcp/server.py:217-230).
- Selected sources must be active, owned by the signed subject, same-project,
  non-shared and verifiably unexpired. No broad recent-memory sweep is implied
  (src/memory_api.py:288-311). Old calls with limit/category receive generic
  contract 422 even when the route is deliberately off.
- get_related still accepts query in its MCP schema but sends entity to the API.
  The API entity bound is 160 characters even though MCP _query accepts up to
  2000; overlong values correctly receive 422, not truncation
  (src/memory_api.py:95-100;
  integrations/hermes/enhanced_cognee_mcp/server.py:113-117,158-161).
- Current serve marks a handler's returned error object isError=true and checks
  required/unknown fields and primitive argument types. The pre-hardening MCP
  sent query instead of entity, used limit-based analysis, and wrapped HTTP
  refusals without isError. Offline controls reproduce those differences
  (current server.py:123-131,327-362; historical parent server.py:118-125,
  153-156,212-224,329-334).
- Ordinary native eight-tool memory provider is a distinct component, not this
  shared MCP registry. Its source tools use ordinary CRUD and entity-based
  connections, not optional summarization
  (integrations/hermes/enhanced_cognee/__init__.py:59-78). No live profile was read
  and no installed provider upgrade is claimed.

PROPOSED: after owner-approved preservation/install scope, install the exact
reviewed shared MCP script, verify its installed hash/schema/error behavior, and
refresh only affected MCP connections/processes/tool caches. Existing processes
can retain old code/schema after a file replacement. This compatibility gate is
needed for graph/error correctness even while optional analysis is off. It is
NOT fleet activation, profile enrollment or permission for a full gateway
restart. If targeted refresh is unavailable, retain that limitation and obtain
separate owner approval rather than restarting the gateway automatically.
The shared MCP write/sharing groups are not certified by this review; do not
enable additional groups merely because route withholding is safe.

## Minimal remaining gates, with no secret-value disclosure

1. Owner-root effective-unit metadata: inventory all applicable fragments,
   drop-ins and directive names, including unknown root20-launch-runtime.conf.
   Record sanitized effective User/Group, DynamicUser, working directory,
   interpreter/argv/module entrypoint, credential IDs and source-path metadata,
   hardening and writable-path policy. Do not dump raw Environment, credentials,
   EnvironmentFile contents or private JSON. Use names/presence booleans and
   validation outcomes for secret-bearing configuration.
2. Confirm the reset really results in ONLY api.json and index.json delivered to
   the new API process; no llm.json through LoadCredential, encrypted/imported or
   SetCredential variants, alternate namespace/mount or wrapper. Different
   systemd credential directive types may need their own reset/exclusion. A
   LoadCredential reset alone does not prove the whole effective credential set.
   Confirm no alternate ExecStart bypasses the reviewed daemon or reinstates
   model environment after sanitization. Mere inherited model env is stripped by
   the reviewed launcher, but is dangerous if the entrypoint changes.
3. Private config metadata, supplied only as owner-validator booleans/approved
   public identifiers: api JSON passes the current allowlist; required database,
   encryption and scoped JWT/OIDC configuration are present and unchanged;
   ENHANCED_INDEX_CONFIG resolves to the retained index mount; embedding model
   is the admitted identifier and matches index model/dimension 384; protected
   cache and five pinned model files are accessible; intended database/index/
   auth origins and namespaces remain unchanged/authorized; new service account
   can access them without privileges widening. Do not print/copy key values,
   private URLs or whole JSON. These facts cannot be established from source.
4. Bind activated imports to the reviewed protected candidate/interpreter rather
   than writable home/source trees; preserve prior code/unit/provider artifacts
   and rollback metadata. Supplied eight staged import receipts are useful but
   are not the activated process. Phase A has no ledger, StateDirectory, schema
   migration, key rotation or index-worker change.
5. Obtain explicit API-only restart approval for the exact prepared plan. After
   an authorized restart, separately verify candidate identity, core readiness,
   intended semantic/index capability and unconfigured analysis status with
   sanitized metadata. No new live qualification is authorized by this review;
   reuse valid prior evidence and agree any additional bounded readbacks first.
6. Close the shared MCP compatibility/install/targeted-refresh gate above. Keep
   this separate from all fleet activation, bots, ordinary profile changes and
   full gateway restart decisions.

These are metadata/deployment gates, not a requirement to reveal private config
to the reviewer. There is no remaining source-level requirement to provision a
model ledger merely to perform the route-OFF Phase A.

## Rollback and later route restoration

- Preserve the exact original root-owned unit/drop-ins and their metadata before
  approved edits; keep credential source files and both candidate runtimes.
  No rollback artifact was created or protected content read here.
- A runtime rollback must keep llm.json withheld. Do NOT blindly restore the
  full old credential-loading configuration: that can reintroduce model access
  when a route-aware runtime is used. Select the prior protected runtime with
  api/index only, preserve scoped credentials and keys, and separately decide
  whether reverting core security fixes is acceptable. If it is not, stop the
  affected API rather than quietly restoring vulnerable behavior.
- OLD source 21abf4857ca8dce8e0a3aafc725266c8d3754529 has schema version 3
  (src/memory_service.py:113) and enc2:kid: prefix
  (src/memory_keys.py:15), like the reviewed source. That is limited storage
  compatibility evidence, NOT proof every newly written record/policy is safe
  under an older runtime. No database restore/downgrade or key replacement is
  part of this rollback; those could lose acknowledged writes/history. Do not
  let rollback re-expose records the newer privacy policy suppresses.
- Preserve and select compatible MCP/provider bytes deliberately; do not promise
  that a new MCP against OLD API supports the new analysis endpoints. OLD API
  source predates them. Changes to a running connection still need refresh.
- Restoring optional analysis is a later, separate authorization gate: manager-
  provisioned persistent private ledger under DynamicUser, service-private
  ownership across UID changes, writable confinement under ProtectSystem=strict,
  accounting/concurrency/failure/restart checks, consistent ledger backup and
  recovery, and a clean UTC usage boundary that cannot refund earlier unknown
  spend. Do not chown to the observed transient UID 63764 or create an ad hoc
  agent-owned ledger. TokenBudget requires the immediate parent and files to be
  current-service-owned/private and rejects unsafe paths
  (src/llm_budget.py:22-35,41-95). No StateDirectory in Phase A is intentional.
- Preserve outstanding charges through failure/cancellation/recovery; do not
  erase the ledger or roll it back to reset caps. Missing/unreliable provider
  usage retains conservative charges; tenant/project/UTC-day accounting is
  separate from canonical memory backup
  (src/llm_budget.py:37-39,100-131; src/llm_summarize.py:88-107).
  Require destination/data authorization and separate owner approval before
  returning llm.json and dispatching any backend model call.

## Actual offline receipts

Executed once, exit 0:

    python -I -B docs/reports/audits/2026-11-01-security-first-cutover/route-review/offline_route_probe.py

Result: 13 distinct offline cases passed, 0 failed; 29 source/template files
bound exactly to c14f595c; 26 local import modules inventoried. Cases include
hostile inherited model environment, four forbidden API JSON fields within one
case, absent-route composition, positive fallback/llm controls, three model
endpoint bodies/422 handler in one case, status nulls, six ordinary endpoint
bodies in one case, script-only detection and current/historical MCP wire/error
behavior. These counts are not assertion totals or live acceptance cases.

The launcher and stdlib MCP modules were executed under non-main namespaces.
Route/API functions were compiled from actual AST nodes with framework/store/
module doubles; no real FastAPI app, database, embedder, ledger or server was
imported or opened. A stdlib-only static local import scan is not a third-party
package/runtime security audit. Scratch dynamic namespaces are not a formal
static-type-check acceptance. Invented fixture credentials are retained under
route-review/invented_credentials and are not real usable credentials.

Artifacts (absolute paths):

- /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/security-first-cutover-worktree-20261101/docs/reports/audits/2026-11-01-security-first-cutover/route-review/READ-ONLY-ROUTE-REVIEW.md
- /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/security-first-cutover-worktree-20261101/docs/reports/audits/2026-11-01-security-first-cutover/route-review/offline_route_probe.py
- /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/security-first-cutover-worktree-20261101/docs/reports/audits/2026-11-01-security-first-cutover/route-review/offline-route-receipt.json

Final status: conditional source route-OFF proof PASS; installed cutover,
protected unit/config metadata, restart approval, shared MCP installation/refresh,
later accounting/recovery and fleet activation remain NOT PASSED by this review.
