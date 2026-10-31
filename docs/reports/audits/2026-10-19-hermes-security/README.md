# Enhanced Cognee audit and Hermes integration decision

Audit date: 19 October 2026 (Europe/London)

Source revision: `e25bd6356e38970c525e0258bdac983cd4079d29`

Decision: retain Enhanced Cognee as a candidate memory service, but do not connect
Hermes to its broad tool surface or enable automatic capture until the blocking
findings below are fixed and tested. A green unit suite does not establish the
security of the exposed interfaces.

This is a repository-wide source, dependency, history, and isolated-behavior audit.
It is not a live penetration test, production certification, or a finding that a
deployed system has been compromised. No production application code, live
configuration, credentials, databases, or Hermes installation was modified.

## Deliverables

- [Remediation and Hermes implementation plan](REMEDIATION-AND-HERMES-PLAN.md)
- [Uses across Vincent's projects](PORTFOLIO-USES.md)
- [Machine-readable audit summary](evidence/audit-summary.json)
- [Reproduced behaviors](evidence/security-probes.json)
- [All 122 tool contracts](evidence/tool-contract-inventory.json)
- [Dependency scan summary](evidence/dependency-summary.json)
- [Secret-scan summary without credential values](evidence/secret-scan-summary.json)
- [Reproduction instructions](evidence/README.md)

## Scope and evidence

| Check                                   | Result                                            | Meaning and limitation                                                                                                  |
| --------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Tracked-file inventory                  | 2,611 files                                       | Entire tracked inventory; focused manual review of security, interfaces, storage, deployment, and clients               |
| Python syntax                           | 1,766 files checked; 8 do not parse               | Includes ancillary integration/production/testing trees outside the required unit lane                                  |
| Full existing unit suite                | 4,183 passed; 2 skipped                           | Python 3.12.3, temporary missing dependencies, outbound network denied                                                  |
| Initial local-environment unit run      | 4,088 passed; 83 failed; 14 skipped               | Missing neo4j, psycopg2, watchdog caused 82 failures; one timing-sensitive failure did not recur                        |
| Targeted security reproductions         | 11 observations                                   | Synthetic inputs, fake stores, in-process HTTP requests; these demonstrate defects rather than passing acceptance tests |
| Tool permission inventory               | 122 tools; 33 explicitly mapped; 89 unmapped      | Some unmapped tools read; others write, schedule, restore versions, ingest, or emit events                              |
| Literal shared-document SQL             | 20 registered tool bodies                         | Scope helpers in other modules do not rewrite these SQL statements                                                      |
| Git history secret scan                 | 13,416 commits; 61 candidates                     | Pattern detections, not 61 confirmed active credentials                                                                 |
| Current tracked snapshot secret scan    | 11 candidates                                     | Tests, examples, and a monitoring webhook-shaped value; not confirmed live secrets                                      |
| Installed Python environment audit      | 158 distributions; 7 flagged package versions     | 24 package/advisory pairs after repeated advisory IDs are deduplicated                                                  |
| uv.lock audit                           | 556 package-version records; 38 flagged versions  | Union across platforms/extras, not the installed or deployed set                                                        |
| Explicit production-image override pins | 21 pins; 3 flagged versions                       | 12 package/advisory pairs; not the complete image SBOM                                                                  |
| npm lockfiles                           | 3 scanned                                         | Version ranges checked against actual locked versions; dev/transitive packages included                                 |
| Broad Bandit scan                       | Raw 20 high, 219 medium, 4,907 low; 1 parse error | Includes tests and non-security MD5 uses; scanner counts are not confirmed vulnerability counts                         |
| Broad critical lint scan                | 57 undefined names plus syntax diagnostics        | Undefined names are in ancillary production scripts, not src/bin runtime code                                           |
| Combined dependency resolution          | Failed                                            | `structlog==24.1.0` conflicts with `structlog>=25.2.0,<26`                                                              |

Unit tests ran with real credentials removed from the child-process environment,
telemetry disabled, and a socket guard preventing outbound/live service use.
Missing packages were supplied under a temporary directory, not installed into
the repository virtualenv. The test overlay was neo4j 5.25.0, psycopg2-binary
2.9.12, and watchdog 3.0.0; their installation is not a recommendation to use
these versions in a repaired release.

Static scanning is repository-wide. Manual review is risk-focused rather than a
claim that every line of vendored upstream code was individually reviewed.
Full raw scanner results are not substituted for the triaged findings below.

### Checks not completed against live infrastructure

- Docker build/start, container-image OS-package scan, and real-stack migrations:
  Docker was unavailable in this WSL environment.
- PostgreSQL/Qdrant/ArcadeDB/Valkey round-trips, restore drills, multi-worker load,
  and live cross-tenant attacks: no disposable live stack was started.
- Hermes version, installed plugin behavior, and cross-WSL service connectivity:
  the isolated Ubuntu-Hermes environment was not accessed.
- Frontend browser E2E, Go/Rust SDK execution, and every optional storage provider:
  not qualified by the Python unit suite or lockfile scans.
- Credential validity/revocation: deliberately not tested against any provider.
- Branch-protection settings and remote CI state: not inspected; required-gate
  conclusions below concern workflow files only.

These remain explicit release gates, not passing or presumed-safe checks.

## Video retrieval and relevance

The ordinary web fetch returned `Online fetch throttled`. Direct requests
recovered the title and description. Direct caption requests returned empty
responses; yt-dlp then received HTTP 429 for subtitles. The free, MIT-licensed
youtube-transcript-api subsequently retrieved 149 English transcript segments.
No paid video tool was called and no video/audio file was downloaded.

The linked video, [Give Hermes Agent Graph Memory in Two Commands](https://www.youtube.com/watch?v=FOx9_Jtrd2E),
describes a memory-provider installation, a separate local server on port 8011,
and session capture plus recall. At about 03:12 it identifies its server as
Cognee 1.4.0; at about 04:25 it resets Hermes' own notebook for a demonstration;
the later question combines service ownership and key-rotation history.

This supports the architecture. It does not demonstrate this fork's storage,
authorization, or compatibility. Do not reproduce the notebook reset against
Vincent's real memory; use a disposable Hermes profile. The transcript was
analysed; visual frames were not independently inspected. Automatic captions
can contain transcription errors.

Free resources: [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)
and [yt-dlp](https://github.com/yt-dlp/yt-dlp). Transcript retrieval succeeded with
the former on this run; neither can guarantee access when YouTube blocks a request.

## Findings

Severity is an engineering priority for the stated deployment conditions, not a
calculated CVSS score. "Reproduced" means the isolated behavior was observed;
it does not mean an external attacker compromised an installed service.

### F01 - Critical: missing tool permissions allow authenticated mutation

Evidence: `src/security/enterprise_auth.py:488-529`,
`src/enhanced_cognee_mcp.py:1388`, and `bin/enhanced_cognee_mcp_server.py:4765`.
Only 33 of 122 tools have explicit permission entries. `remember`, `improve`,
`revert_memory`, scheduling operations, `undo_last`, `redo_last`, and document
loading are examples without an entry. A missing entry returns `None`, and
authorization treats that as no additional permission required. The stdio guard
also returns without enforcement if the enterprise-auth import fails.

Reproduced: a readonly JWT reached the fake backend through `/tools/remember`
with HTTP 200, while `/tools/add_memory` correctly returned 403 as a control.

Change: make permission and side-effect declarations mandatory for every tool;
deny unknown tools and fail startup when a declaration/auth dependency is missing.
Enforce actor identity inside the shared service, not just the transport wrapper.

Acceptance: enumerate the actual registry in tests; all tools have a classification;
readonly identities cannot cause writes, background jobs, network sends, or file
reads outside their grants. Test both HTTP and stdio.

### F02 - Critical when reachable: dashboard bypasses main-server protections

Evidence: `dashboard/dashboard_api.py:304`, `:754`, `:813`, `:859`, `:921`, `:1606`.
The `/api/security/user` endpoint has a bearer dependency, but the memory CRUD
routes do not. They directly address shared tables. CORS does not authenticate
non-browser clients.

Reproduced: an unauthenticated DELETE reached a fake database and returned 204.
No actual record was deleted.

Change: put dashboard CRUD behind the same authentication, actor/tenant policy,
and memory service as the main API. Keep this service inaccessible until fixed.

Acceptance: every non-public route rejects missing credentials; cross-tenant and
readonly mutation requests fail before storage. Test REST and event streams.

### F03 - High: caller-selected tenant and agent are not bound to identity

Evidence: `src/enhanced_cognee_mcp.py:391-468`,
`src/security/enterprise_auth.py:342-366`, `:411-415`, and HTTP memory models.
JWTs can carry a tenant, but middleware independently trusts `X-Tenant-ID`.
`agent_id` comes from request data. The static operator key maps to admin.
Some accepted `user_id` fields are not persisted or used by the route.

Reproduced: a JWT for audit_a submitted a write under header audit_b and another
agent's ID; the route accepted it. Storage was replaced by a recording fake.

Change: derive permitted tenant/user/agent/project from a verified principal.
Reject conflicting selectors; distinguish service credentials from an operator
key. Require an explicit cross-project grant rather than a model-supplied field.

Acceptance: mismatched JWT/header/body identities return 403; omission cannot
fall back to global storage. Test profile and messaging-user separation.

### F04 - High: registered tools still use unscoped SQL

Evidence: `bin/enhanced_cognee_mcp_server.py:749`, `:1058`, `:1211`, `:1395`.
Twenty registered tool bodies contain literal SQL against the shared documents
table. The asyncpg adapter does not rewrite SQL according to TenantContext.
Tenant-aware implementations in `src/mcp_memory_tools.py` are separate code.

Reproduced: extracted search_memories ran under two tenant contexts, and both
queries addressed `shared_memory.documents`.

Change: remove duplicate storage implementations behind the transports; route
every operation through a single actor-scoped service and repository layer.

Acceptance: actual registered tools, not only helper functions, pass concurrent
two-tenant write/search/get/update/forget tests on real stores.

### F05 - High: vector, graph, and cache scopes are inconsistent

Evidence: `src/enhanced_cognee_mcp.py:768`, `:797`, `:900-965`, `:1001`.
Vector writes add a tenant suffix, but vector reads construct unsuffixed names.
Cache writes use `memory:<id>` without tenant scope. The graph relation route
opens the configured graph without applying tenant_scoped_graph.

Reproduced: a vector write and subsequent read used different collection names
within the same tenant context; cache keys were unscoped.

Change: scope every storage tier from the same trusted identity. Filter before
retrieval and graph traversal, not after adding results to a model prompt.

Acceptance: matching read/write namespaces and negative cross-tenant tests for
vectors, graph entities/edges, cache reads, updates, and invalidation.

### F06 - High for user-created tenants: identifier normalization aliases tenants

Evidence: `src/multi_tenant.py:91-105`, `:233-271`.
Lossy normalization maps distinct names to one identifier. PostgreSQL identifier
case folding and length limits create additional cases requiring explicit design.

Reproduced: `audit-a` and `audit_a` become the same tenant identifier.

Change: allocate immutable internal tenant IDs with a validated, bounded mapping.
Reject ambiguous aliases. Do not transform arbitrary external identifiers into
access-control identities by character replacement.

Acceptance: punctuation, case, Unicode, long names, and concurrent onboarding
cannot alias; migrations preserve existing owners and names.

### F07 - High for sensitive memories: normal writes remain plaintext

Evidence: `src/enhanced_cognee_mcp.py:760`,
`bin/enhanced_cognee_mcp_server.py:1132`, and encryption manager integration.
An encryption utility exists, but ordinary memory insertion does not call it.
The simple HTTP route also caches plaintext content.

Reproduced: normal add passed the exact plaintext into the fake SQL insertion.

Change: define an explicit encryption policy covering canonical records, derived
stores, caches, logs, exports, and backups. Integrate it into the shared write/read
path. Application encryption of content must not silently break semantic indexing;
document which derived data remains searchable and who can access it.

Acceptance: an enabled policy demonstrably protects every stated tier; a missing
key or unavailable cryptography blocks protected writes. Do not label utilities
as universal encryption at rest.

### F08 - High: encryption uses ephemeral keys and returns plaintext on errors

Evidence: `src/encryption_manager.py:112-183`,
`bin/enhanced_cognee_mcp_server.py:672-684`.
Without ENCRYPTION_MASTER_KEY, a new key is generated in memory. A new process
cannot decrypt old ciphertext. encrypt() catches errors and returns plaintext;
decrypt() returns the original ciphertext after failures.

Reproduced: two fresh managers could not share ciphertext, and a simulated
encryption error returned the input plaintext.

Change: require a persistent, externally supplied key when encryption is enabled;
store key IDs, use fail-closed typed errors, and implement verified rotation and
backup recovery. Never print or store keys in the repository.

Acceptance: restart/rotation/restore tests, damaged ciphertext rejection, and
assertions that protected writes never silently store plaintext.

### F09 - High: update and forget do not consistently remove derived content

Evidence: `src/enhanced_cognee_mcp.py:1296-1350`,
`src/gdpr_manager.py:174-215`.
Simple update/delete routes change SQL and attempt one cache deletion, without
coordinating vectors/graph. Erasure uses a fixed `memories` Qdrant collection,
while actual writes use category/tenant names; its cache pattern also differs
from ordinary `memory:<id>` keys. Different modules interpret user_id as agent_id.

Change: introduce versioned records, a derived-store manifest, tombstones, and
reconciliation jobs. Define correction, hiding, erasure, and backup retention
separately. Preserve owner approval for irreversible deletion.

Acceptance: corrected/forgotten content cannot reappear through any recall path;
partial failure is reported as partial and retried safely. This is a code/data
semantics finding, not a legal compliance opinion.

### F10 - High: body-size enforcement trusts Content-Length

Evidence: `src/enhanced_cognee_mcp.py:414-433`, `src/mcp_security.py:199`.
The middleware checks the declared length rather than bytes actually received.

Reproduced: a 525-byte body was rejected with 413 when length was supplied but
accepted with 200 as a streamed/chunked request under a 128-byte cap.

Change: enforce a bounded ASGI receive stream plus request-model limits; cap
multipart parts, individual fields, graph expansion, and background-job input.

Acceptance: equal enforcement with missing/incorrect length, streamed bodies,
multibyte text, and uploads, before unbounded buffering or parsing.

### F11 - High for remote clients: file and outbound-request capabilities are broad

Evidence: `src/plugin_loader.py:105-155`,
`bin/enhanced_cognee_mcp_server.py:7107`, `src/webhook_manager.py:111-135`,
and compose flags ACCEPT_LOCAL_FILE_PATH / ALLOW_HTTP_REQUESTS / ALLOW_CYPHER_QUERY.
Built-in loaders read caller-selected local paths without an allowed-root policy.
Webhook registration accepts arbitrary URLs. Notifications and ingestion introduce
additional outbound request paths. Some relevant tools are unmapped under F01.

Change: disable these capabilities on the Hermes-facing service by default.
For an explicitly granted importer, enforce resolved allowed roots, symlink
boundaries, size limits, URL schemes, DNS/IP policies, redirects, and egress
allowlists. Keep database/graph administration off the agent tool surface.

Acceptance: synthetic forbidden paths and private/metadata destinations are
rejected without opening a file or making a network request. No live SSRF or
private-file exploit was attempted during this audit.

### F12 - High: Python environment and release pins have known advisories

Evidence: `evidence/dependency-summary.json`; local environment, uv.lock, and
explicit Docker override versions were scanned independently.
Installed packages flagged include aiohttp, diskcache, fsspec, litellm, multidict,
pypdf, and urllib3. Older explicit image pins include python-multipart 0.0.9 and
python-jose 3.3.0. Requirements and installed versions are not interchangeable.

Change: resolve one supported dependency set, update affected packages together,
review no-fix findings individually, and remove image-layer downgrades. Recheck
current advisories when implementing; scanner fix-version lists are observations,
not instructions to update one package in isolation.

Acceptance: reproducible lock, dependency audit of the exact built environment,
reachability review, and documented bounded exceptions. No vulnerabilities were
exploited and no production package inventory was inferred from the local venv.

### F13 - Critical advisory priority: frontend locks contain affected versions

Evidence: cognee-frontend locks Next 16.1.1 / React 19.2.0; the separate dashboard
locks Next 16.1.6 / React 19.2.3 / Axios 1.13.4. Public npm advisories were matched
to locked versions using semver. Counts include transitive and development code.

The maintainer's [AVIF image-optimization advisory](https://github.com/vercel/next.js/security/advisories/GHSA-2xp9-vwfh-vxw4)
lists affected Next releases and fixes. Its exploit requires the relevant image
optimization path. A separate [Windows-hosted server advisory](https://github.com/vercel/next.js/security/advisories/GHSA-p293-qw3h-jr36)
has a Windows deployment condition; a Windows host running a Linux WSL server
does not itself establish that condition.

Change: update each frontend's complete supported Next/React dependency set,
review server-side routes and image settings, regenerate locks, and build/test
in the intended runtime. Do not treat the advisory count as proof of RCE in a
currently running deployment.

Acceptance: actual build SBOM, applicable-advisory review, route/auth tests, and
E2E checks on the target platform.

### F14 - High: dependency declarations cannot be resolved together

Evidence: combined requirements.txt and pyproject.toml resolution failed because
structlog is pinned to 24.1.0 while the project requires >=25.2.0,<26.
The optional neo4j extra also requires >=5.28 while requirements pins 5.25.
Multiple dependency and lock formats plus image-local overrides can drift.

Change: establish one authoritative dependency declaration and generated lock;
derive runtime/test/provider extras and container installs from it.

Acceptance: clean Python 3.11 and 3.12 installations for the explicitly supported
profiles, pip/uv consistency checks, and no post-lock image overrides.

### F15 - High: image layouts omit code required by advertised interfaces

Evidence: both docker/Dockerfile.enhanced-cognee and Dockerfile.production copy
src but omit bin and cognee. The /tools dispatcher dynamically imports the bin
registry, whose tools import cognee. The production image copies
alembic-enhanced.ini but omits alembic_enhanced. The root Dockerfile follows a
different layout and still requires an explicit registry packaging check.

Change: package application modules and migrations consistently, install the
project itself, and smoke-test the actual image. Prefer one release image with
declared profiles over parallel hand-maintained package lists.

Acceptance: initialize, authenticate, list the actual registry, run synthetic
remember/recall, and migrate an empty disposable database from the final image.

### F16 - High: schema definitions and helper SQL disagree

Evidence: alembic_enhanced baseline creates TEXT IDs and embedding vector(1536);
docker/init-scripts/01-init-pgvector.sql creates UUID IDs, memory_category/tags,
and vector(2560) embeddings. The HTTP default vector dimension is 1024.
src/mcp_memory_tools.py deletion reads `data->>'category'`, although the inspected
document definitions use metadata and memory_category, not a data column.

Change: migrate to one canonical schema and model/dimension configuration.
Preserve existing data and explicitly map ID types. Ensure tenant tables receive
all required constraints, related tables, indexes, and later migrations.

Acceptance: fresh install and upgrade from each existing schema, real JSONB
round-trips, helper delete/correction checks, and embedding dimension tests.

### F17 - Medium: Python SDK authentication and scope differ from the server

Evidence: `sdk_pkg/enhanced_cognee_client/client.py:34-65` sends api_key as a
Bearer token, builds an http-only URL, and has no tenant constructor parameter.
The server's static operator key expects X-API-Key, while bearer means JWT/OIDC.
Node/Go/Rust clients target different route sets and accept tenant settings.

Reproduced: SDK header inspection confirmed the mismatched static-key header,
absent tenant header, and fixed HTTP scheme.

Change: shared contract tests; explicit base_url, access_token, api_key, tenant
selection rules, TLS options, stable error envelopes, and timeout/retry policy.

Acceptance: all clients exercise the same authenticated service contract without
depending on admin identity or silently dropping required scope.

### F18 - Medium: partial writes can be reported as complete failures

Evidence: `src/enhanced_cognee_mcp.py:737-815` inserts SQL, then writes vectors and
cache without an outbox or idempotency transaction. A cache failure propagates
as HTTP failure after the canonical row was written.

Reproduced: a fake cache outage raised an HTTPException after an INSERT.

Change: commit canonical data plus an outbox atomically; retry derived writes
with an idempotency key. Distinguish accepted, indexed, degraded, and failed.

Acceptance: interrupted writes and repeated session turns produce one logical
memory, with visible indexing status and reconciled derived stores.

### F19 - Medium: throttling is optional, process-local, and caller-keyed

Evidence: `src/mcp_security.py:127-185` and route _enforce_rate_limit.
Only per-tool variables enable limiting; the generic variable documented in
AGENTS.md does not enable this helper. A caller can vary agent_id. Each worker
has independent buckets, and the bucket map has no expiry/size bound.

Change: validated startup settings, principal/tenant budgets, bounded state,
distributed enforcement for multiple workers, and a coarse request ceiling.

Acceptance: identifier rotation and multiple workers cannot multiply a budget;
memory stays bounded; disabled protection is visible in readiness/config reports.

### F20 - Medium: background state is not durable across restarts/workers

Evidence: `_cognify_tasks`, asyncio.create_task in registered memory tools,
in-memory WebhookManager/NotificationManager configuration, and the production
image's default two workers. Process-local state does not provide a durable
acknowledgement that a session was indexed.

Change: persist jobs/config with ownership, deduplication, retry/backoff, and
flush/checkpoint semantics. Propagate actor/tenant through workers explicitly.

Acceptance: restart during session close or indexing; no lost accepted writes,
no duplicate finalization, and consistent status from either worker.

### F21 - Medium: required local gate does not qualify release behavior

Evidence: `.github/workflows/ci-required.yml` runs tests/unit only. Broader CI
contains additional checks, but includes informational scans and tolerated
integration failures. Coverage and unit success do not test every transport,
actual image, tenant mapping, or production-like database schema.

Change: require security regressions, exact dependency audit, schema upgrade,
container smoke, transport contracts, and a disposable-stack integration lane.
Separate optional-provider coverage from default-profile release gates.

Acceptance: blocking findings have regression tests on public entrypoints and
the release cannot pass by skipping its core services. Verify remote branch
protection separately when implementation is ready.

### F22 - High triage priority: provider-shaped secrets exist in Git history

Evidence: redacted Gitleaks history scan and sanitized historical-secret-triage.
Historical `level_2/.env` at commit 81b6cc192041 and `.dlt/secrets.toml` at
8cbf488e59ad contain candidates without obvious placeholder labels. Several
match provider-key shapes. This does not establish that any remain valid.

Change: owner verifies these are revoked/rotated; treat uncertain credentials as
exposed until confirmed. Add secret scanning with narrow reviewed test-fixture
allowlists. History rewriting is a separate owner-approved action, not a
substitute for revocation. Do not paste values into chats, reports, or tickets.

Acceptance: recorded owner/provider revocation evidence and clean new-change
scans. No credential was tested, rotated, exposed in this report, or uploaded.

### F23 - Medium: ancillary production/testing trees contain damaged code

Evidence: eight tracked Python files fail parsing; see evidence/inventory.json.
Critical lint also finds 57 undefined names in ancillary production modules.
The existing src/bin required syntax lane does not cover all these trees.

Change: classify supported entrypoints versus preserved historical material.
For damaged files that remain supported, archive originals and perform a clean
restoration preserving logic, following AGENTS.md; avoid repeated regex repairs.
Do not delete historical files without Vincent's permission.

Acceptance: all supported Python parses and imports; useful behavior tests for
restored modules; explicit documentation of retained non-runtime historical code.

### F24 - Medium: readiness is weaker than memory capability readiness

Evidence: src/enhanced_cognee_mcp.py dependency health marks readiness from
PostgreSQL, even when vector/graph/cache dependencies are degraded. Generic
tools can return text beginning ERR in an HTTP 200 result envelope.

Change: capability-specific readiness and structured error/status codes.
Expose text-only versus semantic/graph capability and indexing lag explicitly.

Acceptance: a Hermes connector can distinguish an empty recall, unavailable
index, denied access, failed processing, and a truly healthy graph service.

### F25 - Medium: provenance features are not a universal admission policy

Evidence: memory provenance/confidence/versioning modules exist, but simple
memory writes accept arbitrary content/metadata, with no enforced provenance,
fact-versus-inference, expiry, or retrieved-instruction trust contract.

Change: stamp source actor, project, session, source reference/hash, timestamp,
confidence, authority, and correction lineage in the service. Treat retrieved
content as data; imported instructions do not gain permission by being recalled.

Acceptance: prompt-injection fixtures cannot override tools/identity/policy;
conflicting facts retain provenance and corrections; stale claims are identifiable.

### F26 - Medium: stdio emits non-protocol output

Evidence: bin/enhanced_cognee_mcp_server.py:51 and main():7971 onward print
environment/banner/tool-list text to stdout before run_stdio_async. The optional
remote setup also calls an async serve() without awaiting it.

Change: keep stdout exclusively for protocol messages; send diagnostics to stderr
and await asynchronous initialization. This matters if an MCP bridge is chosen.

Acceptance: a real MCP client completes initialization and calls a synthetic tool
without parsing noise, coroutine warnings, or accidental local fallback.

### F27 - Medium: documentation overstates uniform readiness and configuration

Evidence: AGENTS.md and other guides say tools accept tenant_id, semantic search
is automatic, and encryption is universal, while the inspected registered tools
and simple routes differ. Legacy wrappers/compose settings retain fixed ATS/OMA/
SMC prefixes; these should not become restrictions in the new integration.

Change: generate tool/settings documentation from actual contracts; distinguish
implemented helpers, transport wiring, runtime evidence, and release admission.
Keep project categories configurable strings and preserve dated historical claims
as historical evidence rather than silently declaring them current.

Acceptance: examples exercise a clean release, configuration knobs are validated,
and documented guarantees have matching entrypoint integration tests.

## What is already useful

The project has substantial reusable work: a passing broad unit suite, a provider
factory, dynamic category configuration, tenant helpers, authentication primitives,
versioning/provenance, encryption primitives, SDKs, and deployment material.
The recommended repair is to consolidate and wire those components consistently,
then prove the combined behavior. A wholesale rewrite of the product is not
justified by this audit.

## Source references for the integration decision

- [Hermes memory provider lifecycle and plugin layout](https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin)
- [Hermes memory provider behavior](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers)
- [Hermes MCP transport configuration](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
- [Cognee Hermes integration](https://github.com/topoteretes/cognee-integrations/tree/main/integrations/hermes-agent)
- [Current plugin HTTP contract](https://github.com/topoteretes/cognee-integrations/blob/main/integrations/hermes-agent/cognee_integration_hermes/http_backend.py)

These are changing upstream sources. Pin and qualify the actual Hermes/plugin
revisions used for implementation; a main-branch README is not a compatibility
test of the installed version.
