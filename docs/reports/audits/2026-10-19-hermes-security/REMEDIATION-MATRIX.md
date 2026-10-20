# Finding-by-finding remediation record

Updated: 20 October 2026. The implementation branch is published; merge and
private/everyday activation remain incomplete. See the
[latest canonical stack evidence](CANONICAL-STACK-UPDATE-2026-10-20.md) for current
local and exact hosted-image results. The original audit date was 19 October.
The original README and evidence describe the pre-remediation baseline. This
matrix records the repaired behavior and the remaining limits. "Contained" means
the restricted Hermes profile avoids the affected legacy path, not that every
optional provider or old interface has been repaired and qualified.

Latest Ubuntu-Hermes follow-up: [78/78 qualification and local capture](HERMES-QUALIFICATION-FOLLOWUP-2026-10-20.md).
All four previously skipped real-client/browser checks now pass, with zero skips.
Local Qwen 27B passes five model-driven scenarios in the separate second synthetic
profile at a verified 65,536-token context; encrypted history was independently
checked. CPU-offloaded replies take 196-387 seconds. Earlier model failures below
remain historical; protected deployment, owner custody and release gates remain
open.

| Finding | Implemented behavior | Remaining qualification or work |
|---|---|---|
| F01 - Tool permissions | Explicit permission/effect manifest for all 122 tools; canonical sixteen-alias allowlist; actual stdio readonly denial; separate human review role | Retained legacy effects conservatively marked unqualified; broader legacy tool/provider coverage remains |
| F02 - Dashboard protection | Canonical-service dashboard delegation, authenticated requests, protected origins and tab-session tokens; actual built-browser create/list/detail/edit/retract flow passes | Historical analytics/graph/session screens and broader device/browser coverage remain unqualified |
| F03 - Identity binding | Verified identity binds tenant, user and agent; project credentials confined to restricted API; nested identity conflicts denied | Real 42-space bot/controller and distinct-profile tests pass; installed fleet and wider legacy/provider identity coverage remain |
| F04 - Unscoped SQL | Scoped SQL and denied global upstream calls; historical HTTP/dashboard entrypoints can delegate to canonical mode; unsupported legacy tools denied | Individually selected legacy/provider paths remain separate qualification work |
| F05 - Derived scopes | Canonical authorization before derived candidates; real Qdrant/ArcadeDB/Valkey delivery, hashed entities, encrypted cache, version/scope checks and source-limited graph queries pass | Private deployment needs separate restricted index credentials and OS boundary; optional legacy providers remain unqualified |
| F06 - Tenant aliases | External identifiers must be canonical; no lossy external normalization; migration requires an explicit mapping | Existing noncanonical namespaces need individual reviewed mappings |
| F07 - Plaintext writes | Restricted service encrypts complete memory payload and internal vectors; real database verification passed | Legacy write paths are not universally encrypted; avoid them for private deployment |
| F08 - Encryption failure | Persistent key required; protected failures raise; named-key writes and mixed-key reads supported; bounded operator-only current/history rotation rolls back a failed batch | Approved-path backup collection/encrypted cloud-chain script prepared and synthetically tested; owner-controlled custody, installed scheduling/private recovery and all legacy-store rotation remain |
| F09 - Correction/retraction | Owner/version checks, expiry and immediate canonical exclusion; real derived correction/retraction, stale-edge rejection, graph rollback and retry/rebuild pass; history retained | Private deployed upgrade/requalification remains; permanent erasure requires a separate owner decision |
| F10 - Payload limits | Received-byte and total-body limits, bounded admission and response/history/graph budgets; 42-space, 15-minute real-store concurrent fixture plus CPU/PSS/storage-growth observations pass | Installed Hermes/model and deployment-specific capacity assessment, longer soak and broader retrieval still remain |
| F11 - Import/network capabilities | Explicit capability/root/origin grants; symlink-safe bounded file read; HTTPS-only bounded web fetch without redirects/proxies; database source aliases with operator-defined queries; scoped callers denied global imports | Operator database accounts must be read-only; direct upstream-library ingestion is outside the restricted API; arbitrary optional loaders remain unqualified |
| F12 - Python advisories | Three hashed release/bootstrap locks audit clean; restricted built-image Python scan is clean; unused runtime pip removed; full image retains the version-matched Cognee advisory with tested source backport | Restricted minimal-image HIGH/CRITICAL gate passes; lower-severity findings, full legacy-image/backport release review, optional-extra union and unchanged developer virtualenv remain separate |
| F13 - Frontend advisories | Production audits report zero; clean builds/types/browser flow pass; hash-verified local depth backport rejects the reproduced original exploit | Official version-matched five-HIGH npm findings remain enforced with no patched release; broader UI/device coverage remains |
| F14 - Dependency conflicts | Requirements/project declarations reconciled; full hashed installation and image dependency checks pass; built full APIs/122-tool registry import with production tenant enforcement; 4,293 units pass with zero skips, including restored adapter and Locust checks | Broader optional extras remain unqualified; scheduling extra intentionally unavailable |
| F15 - Packaging omissions | Full wheel/image boundaries and paths checked; small native wheel built from same tree with API/worker/SDK/MCP/operator modules; clean outside-checkout install and 55-package compatibility pass; 27 previously ignored dashboard libraries delivered; clean frontend/unit/browser and Docker-context builds pass | Private deployment and optional full-distribution extras remain separate |
| F16 - Schema mismatch | Canonical encrypted/versioned tables; copy-only UUID/TEXT migration; actual old Docker UUID, existing TEXT+tenant and fresh Alembic fixtures pass additive upgrades; invalid large-vector index removed | All legacy helpers still need consolidation; existing private data not migrated |
| F17 - SDK auth/scope | Native canonical Python/Node/Go/Rust methods and real-service tests pass; explicit canonical destinations, TLS, structured bounded errors, retries, current-version conflicts and project denial enforced | Optional legacy backend/client combinations and caller-provided Node fetch behavior remain separate |
| F18 - Partial writes | Canonical record/version/audit/event commit atomic; leased idempotent actual-store delivery, partial-failure/crash recovery and actual image worker restart/backlog tests pass | Retained historical multi-store paths remain outside canonical admission |
| F19 - Throttling | Restricted API uses shared PostgreSQL budget per verified tenant/project/subject; concurrent service-instance test passed | Legacy process-local throttling not fully replaced; wider load/outage checks remain |
| F20 - Background durability | Durable leased outbox worker implemented and real-store tested; source-serialized projections, all-store acknowledgement, retry/backoff, preserved degraded status and fresh-namespace replay pass | Schema-3 worker and newer provider not yet installed/requalified inside Ubuntu-Hermes; older queues remain unadmitted |
| F21 - Release gate | Latest hosted source/package/image/default-stack tests pass, including actual API/worker restart recovery; pinned minimal image passes the unsuppressed HIGH/CRITICAL gate with exact retained evidence | 26 MEDIUM and ten LOW image matches retained, no listed fixed versions; development advisory gate, broader legacy image and private deployment checks remain; branch protection not changed |
| F22 - Historical credentials | Values not exposed or tested; existing private triage retained; .dockerignore excludes secret files and archives | Owner must confirm revocation/replacement of real candidates; no history rewrite authorized |
| F23 - Damaged ancillary source | Originals archived; all eight original parse failures repaired; current source parses; undefined names fixed across src/bin/dashboard/production/testing/integration | Static repair is not operational qualification of retained deployment/recovery/reporting scaffolds |
| F24 - Readiness | Canonical readiness validates schema; authenticated status reports scope/model/encryption, worker heartbeat/state, lag and graph/vector capability; idle polls preserve delivery failure status | Private installed service and retained legacy health/provider paths need their own verification; no blanket production-readiness claim |
| F25 - Provenance | Encrypted bounded source ID/URI/hash/span, fact/preference/decision/inference/summary classification and declared confidence; authority explicitly unverified; correction lineage and source re-review; legacy reserved-field and checksum-verification repairs | Source declarations do not prove facts; human verification workflow, broader source quality and all legacy admission paths remain |
| F26 - Stdio protocol | Actual full-image 122-tool protocol checks pass; canonical nine-tool stdio bridge has real-service qualification; built API/worker default-stack behavior and restart recovery pass | Updated installed Hermes host/model checks remain; protocol discovery alone does not establish private service readiness |
| F27 - Documentation claims | Dated phase tracker, canonical operator runbook, current finding matrix and exact unsuppressed local/hosted evidence distinguish implementation from activation | Older dated status tables remain historical; optional-provider documentation is not blanket support |

No row authorizes private-data activation. The canonical service provides
encrypted records, local semantic recall and optional configured source-linked
graph recall with actual tested derived delivery. It reports missing/stopped/failed
workers and lag explicitly. These Workspace and hosted fixtures do not establish
that the newer stack is installed or privately isolated inside Ubuntu-Hermes.
## Installed-host continuation - 20 October 2026

See [HERMES-DEPLOYMENT-2026-10-20.md](HERMES-DEPLOYMENT-2026-10-20.md)
for the actual schema-3/eight-tool/four-store synthetic deployment, instruction
reconciliation, 73-pass/four-skip qualification, selected-model failures/repair,
two-profile checks and encrypted restore/index rebuild. Protected OS deployment,
scheduled backup execution, local selected capture, owner custody and release
acceptance remain open; historical rows above retain their original scope.
