# Canonical stack implementation update - 20 October 2026

The remediation plan is being implemented. It is not fully complete, and the
everyday Hermes profile and other projects are not activated. This update
supersedes earlier statements that graph workers and canonical transport
consolidation were entirely unimplemented. Earlier evidence remains historical;
an old image or installed plugin does not qualify a newer source revision.

Latest continuation: [Workspace completion and deployment handoff](WORKSPACE-COMPLETION-2026-10-20.md).
That checkpoint records 4,293 zero-skip unit tests, clean frontend delivery/builds,
a tested local braces source backport with version-matched findings still
visible, 15-minute 42-space resource measurements and the exact Ubuntu-Hermes
handoff. The earlier checkpoints below remain historical.

Earlier restricted-image result: [hosted qualification 39387234569](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39387234569)
is fully passing for runtime source `91a3c467f6af0d8b330536fb1fe9142dd4d06d79`.
Its exact image
`sha256:91de18171da94cbb0e72574236bbe36de60293279db1c3db8a0276e6c395de1d`
passes 21 real-store checks, package verification, native runtime smoke and actual
API/worker restart/recovery. The unsuppressed final-image scan reports zero HIGH,
zero CRITICAL, 26 MEDIUM, ten LOW and zero UNKNOWN matches, with 21 Debian and 48
Python package records. This closes the earlier 44-HIGH gate for this restricted
artifact. It does not qualify the larger legacy image or private deployment.
The final scan and logs are retained under `remediation-evidence/2026-10-20-minimal-runtime-*`.

The complete local unit lane passes 4,290 tests with zero failures/errors/skips.
[Required CI 39386830679](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39386830679)
also passes all 4,290 unit checks, three schema checks, ten settings/security checks
and 64 canonical checks on `65d78f3cf2ae11ef9b5aecc0ce7954e9a37b41ea`.
The subsequent Docker-only xz library update also passes the exact-image recheck
above. No merge or private/everyday activation has been performed.

## Minimal runtime and backup filename follow-up

The restricted API/worker now uses pinned official CPython and distroless Debian
13 inputs. Unused OS utilities and five optional GUI/terminal/UUID native modules
are absent from the final artifact; UUID4 continues to use OS randomness. The
base package inventory and complete control/checksum records of seven additional
runtime library packages remain present. The build also applies the available signed Debian
[liblzma5 security update](https://security-tracker.debian.org/tracker/DSA-6549-1)
at version `5.8.1-1+deb13u2`. No remaining image match lists an available fixed
version in this scan. The gate contains no advisory ignore or severity exception. Build-only inspection checks retained native dependencies;
exact-image tests cover TLS, compression, SQLite, dbm, AES, UUID4 and native imports.
The [operator runbook](../../../runbooks/CANONICAL-MEMORY-AND-INDEXES.md)
describes scope and diagnosis without an interactive shell. This image does not
replace the protected native backup/recovery operator runtime.

The owner requested the new backup filename. `C:\Scripts\backup-all-wsl-v11.ps1`
now exists, preserves the updated v10 backup behavior and archive/password state
compatibility, and corrects the version banner. The original v10 file remains
unchanged. The matching private guide is
`C:\Scripts\BACKUP-ENCRYPTION-AND-RESTORE-v11.md`. PowerShell parsing and the
no-write preview passed in Linux; native Windows/DPAPI, scheduled-task path changes,
a real backup and cloud upload have not been verified. These private operator
files are intentionally outside this published repository.

## Implemented and tested in this continuation

- Additive canonical schema 3 and separately restricted worker/API database
  permissions. Existing runtime accounts can receive the new read grants without
  credential replacement. Runtime startup validates schema rather than creating it.
- Prepared two hardened service-manager units with distinct dynamic OS users and
  private role-specific credentials. Their launcher strips inherited credentials
  and refuses unsafe credential files. The API receives no cache credential and
  uses a graph client that admits only its bounded read query. These deployment
  assets have not been installed in Ubuntu-Hermes.
- A separately expiring human reviewer role can approve library membership and
  reviewed sharing without memory-write, retraction or system-management powers.
  Category, retry and topic identifiers now receive credential screening before
  storage, in addition to content, metadata and source declarations.
- Durable leased delivery to actual Qdrant, ArcadeDB and Valkey stores. Delivery
  is repeatable, acknowledges every store before completion, retries partial
  failures, recovers crashed leases and serializes against current corrections.
  Current semantic recall remains available while an index is delayed.
- Source-linked graph claims, bounded multi-hop traversal and authorization at
  every hop. Current source/version checks reject stale edges, revoked sharing,
  expired sources and retractions immediately. Graph failures are reported.
  Hashes replace entity labels in graph storage; cache snapshots stay encrypted.
  These controls do not make derived vectors opaque to infrastructure operators.
- Real graph transaction rollback and fresh-namespace rebuild from retained
  canonical events, including events processed by an earlier pipeline.
- Canonical list/history/agent reads, bounded responses and admission capacity.
  History preserves versions and withholds recognized secret/private content.
  Compatibility HTTP/tool/dashboard adapters delegate to the same service.
  Canonical mode admits sixteen reviewed aliases; unsupported legacy operations
  are denied. The full 122-tool permission/effect manifest distinguishes canonical
  behavior from conservatively unqualified legacy effects.
- A nine-tool actual stdio MCP bridge and canonical Python, Node, Go and Rust
  client methods. Real-service tests check retries, project denial, stale versions,
  correction, retraction, retained history and credential refusal. Scoped errors
  avoid returning private server error content. The Python client refuses routes
  that could forward its bearer credential to another origin.
- Dashboard authentication, explicit permitted origins, tab-session credentials,
  protected-origin checks, JSON writes, stable write identities, version-checked
  edits, dynamic category input and retraction with retained history. Fixed
  unauthenticated direct requests, stale query refreshes and edit links leading
  to a missing route. Built-browser qualification is recorded separately below.
- An eight-tool Hermes provider update adds graph connections and optional
  source-span relationship declarations. Main-model selection still governs
  summaries; no raw transcript capture or extra extraction provider was added.
  Operator upgrades archive existing test-provider files and preserve extra files.
  Token renewal preserves private originals and never copies signing keys into
  the profile. This newer provider has not yet been delivered to Ubuntu-Hermes.
- A small native distribution built from the same maintained source tree, plus
  hashed index/MCP locks. It includes no upstream Cognee engine. Its clean
  installation and dependency compatibility checks pass outside the checkout.
  The larger root Cognee wheel still requires its full dependency set; minimal
  dependency import checks alone are not full-distribution qualification.
- Required core CI coverage and a separate default-stack/image-security workflow.
  The hosted workflow builds the API/worker image and tests both processes with
  four real stores, worker restart/backlog recovery and fresh restricted database
  roles. It retains unsuppressed findings and fails on high/critical matches.

## Bot-fleet, privacy and backup continuation

One protected backend can serve the 41 separately configured bots plus the main
controller, with 42 distinct scoped identities and private spaces. Reviewed
portfolio/team libraries provide controlled sharing. The [fleet runbook](../../../runbooks/HERMES-BOT-FLEET-MEMORY.md)
describes per-profile setup, same-user isolation limits, credential renewal and
capacity requirements. This is not a claim of 42 installed bots or simultaneous
model capacity. A real PostgreSQL/API fleet test and a separate concurrent
42-profile provider-contract test pass.

The fleet check exposed a privacy false positive: generated UUIDs and embedding
decimals could resemble private phone/card details and hide a safe admitted
memory. Read screening now excludes only root-level service bookkeeping. Caller
content, nested metadata, provenance, categories and relationship declarations
remain screened, and admission still rejects credential-shaped fields. A
regression test covers get/list/semantic/history and continued private-data
withholding. Library publication now also screens relationship and fact fields.

The two former unit skips were repaired. A module-level dependency skip hid 39
adapter tests; installing the locked test-only Memcached dependency and removing
the skip restores them. Locust's actual import/eight workload classes are checked
in a separate process with a 30-second timeout, keeping gevent state out of
pytest's asyncio process. Its locked test dependencies audit clean. Required CI
installs them and rejects any skips in the unit report. The current total is
4,285 passing unit tests, zero failures/errors/skips. `requirements-test.txt` now
uses the compatible full/test locks instead of obsolete pytest pins.

Separately, the owner's Windows backup script was saved under its requested
original filename with earlier copies preserved. The diagnostic log showed
ERROR 433 on a PostgreSQL Unix socket, rather than a failed database-document
copy. A native Linux workspace archive replaces the unsuitable NTFS workspace
mirror; complete encrypted Cognee archive/manifest pairs are collected from the
approved path. Cloud generations require encrypted archives and preserve matched
base/differential recovery sets, including tiny deletion records. A private local
step-by-step password-manager/encryption/recovery guide accompanies the script.
Twenty-nine synthetic PowerShell/real-7-Zip checks and eight synthetic age inventory
checks pass. Live Windows DPAPI, full real-data backup, remote upload and installed
Hermes backup permissions/timer remain unqualified; no real backup or cloud
transfer was triggered by these edits. Private scripts/logs are not published.

## Fresh required-CI compatibility follow-up

Hosted run 39371096947 confirmed the Tenacity repair: full unit, legacy schema
and upstream settings/security checks passed. It then exposed an unused legacy
WebSocket import in the stdio-bridge HTTP fixture. The canonical API implements
HTTP endpoints; its daemon, image, test helper and service fixtures now explicitly
select Uvicorn's `ws=none` transport. No deprecation filter was added. The complete
77-check opt-in qualification suite passed again after this change.

Required CI now prepares a separate hashed canonical test environment rather
than combining the optional index/model stack with the larger Cognee application
installation. The public small embedding model is prepared before tests and
used offline during them. This also runs the formerly optional semantic fixture
in that lane. The exact 64-check required canonical command passes in a fresh
59-package environment with zero failures/errors/skips. Both unit and canonical
JUnit reports must contain executed tests and zero skips. Hosted Required CI run 39371928694 now confirms
all 64 checks with zero skips; all preceding required lanes also pass.

## Earlier local and hosted qualification checkpoints

- Full unit lane: 4,285 passed, 0 failed, 0 skipped, with credential environment removed and
  outbound network denied. This is the developer lane with documented compatible
  overlays, not an exact newly built full-image environment.
- The fresh full/test hashed environment in hosted Required CI run
  [39370495182](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39370495182)
  also passed all 4,285 unit tests, zero failures/errors/skips, in 30.50 seconds.
  Its three real legacy install/upgrade fixtures passed. A subsequent upstream
  settings check caught Tenacity's deprecated `initial` retry parameter at import
  with warnings-as-errors. All 13 affected model/embedding modules now use the
  supported `multiplier` keyword with identical configured wait/cap values; the
  root dependency minimum matches the already locked 9.2.1 API. The repaired
  local settings/security suite passes all ten checks. No warning was suppressed
  to bypass this failure. The latest fully passing Required CI entry above
  confirms the repair in the fresh hosted environment.
- Full opt-in qualification suite: 77 passed, no skipped tests, against an
  explicitly provisioned native PostgreSQL 16.15 fixture, prepared offline BGE
  search model, real Qdrant 1.18.3, ArcadeDB 26.9.1 and Valkey 7.2.13. Includes
  the three actual language clients, actual stdio bridge, encrypted age backup
  and fresh-database recovery, browser flow and operator-update checks.
- After the backup destination approval, the full suite passed again in 28.19
  seconds, including backup credential/destination override refusal and actual
  encrypted dump/fresh-database restore. The native artifact was rebuilt and its
  installed backup modules and approved path checked outside the checkout.
  System-unit syntax checks passed with temporary accessible runtime paths;
  these checks do not establish installed service or filesystem permissions.
- A subsequent expanded real-store test passed graph transaction rollback and
  rebuilding a fresh index namespace after previous delivery completion.
- A separate 60-second concurrent real-store exercise passed: four projects,
  130 rounds, 520 corrections, 650 semantic queries, 520 graph queries, zero
  observed scope leaks/failures and no pending events at completion. Round p95
  was 700.21 ms. This bounded fixture exercise is not a long soak or a production
  capacity guarantee.
- A subsequent five-minute four-project real-store exercise also passed (303.93
  seconds including setup/teardown), repeatedly checking current versions,
  semantic/graph results, scope denial and cleared indexing checkpoints. Its
  passing-test XML did not retain per-round stdout, so no throughput or latency
  figure is attributed to that run. A late Python-process sample recorded
  710,068 kB peak resident memory; that excludes the four storage processes and
  is not whole-stack resource qualification.
- A later ten-minute real-store exercise passed 1,323 four-project rounds:
  5,292 corrections, 6,615 semantic queries and 5,292 graph queries, with zero
  observed scope leaks/failures and no pending events at completion. Measured
  workload duration was 600.31 seconds; round p95 was 631.91 ms. The adjacent
  twelve-case English paraphrase set retrieved every expected source at rank
  one (12/12 top-three hits); median query latency was 47.84 ms and p95 56.67 ms.
  These are small synthetic Workspace fixtures, not a whole-stack memory/resource
  qualification, broad accuracy benchmark, long deployed soak or 42 concurrent
  inference sessions. The exact result is retained in the dated load/retrieval JSON.
- The dashboard production build passes type checks. The browser qualification
  exercises a real built frontend and service using invented data. It does not
  qualify historical graph/analytics/session screens or every browser/device.
- The index and MCP locked-dependency advisory scans report no known findings.
  The refreshed dashboard production-dependency scan reports zero findings.
  Neither result closes the separate existing OS-image or development-tool gates.
- Root and small native wheels pass the local-data/secret/test-path packaging
  boundary check. Native wheel imports and dependency compatibility pass in a
  fresh Python 3.12 environment outside the checkout.
- Hosted run [39360080552](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39360080552)
  at commit `0c374750a87face413e17679e0b93f846601ac3b` passed real-store tests,
  clean native distribution checks and the image build. Its unsuppressed image
  security gate failed: 44 HIGH package matches across eight advisories, zero
  CRITICAL and no fixed version listed in that scan. Findings were retained;
  no suppression was added. Newer source changes need their own hosted run.
- Hosted run [39364795136](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39364795136)
  qualifies source commit `6eb6114b2a98545d11394a5aa52e295c71d968da`:
  18 selected real-store tests, clean distribution installation, exact runtime
  image build and the actual API/worker image restart/recovery tests all pass.
  Image `sha256:e648f11dc57b3db5a41e1acc2dae5e44cb14a48f12285b7e204a325c3db79cb5`
  still fails the unsuppressed scan with 44 HIGH matches across eight advisories,
  zero CRITICAL and no fixed versions listed. The overall workflow therefore
  correctly remains failed. This is not evidence of installation in Hermes.
- Hosted run [39370484297](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39370484297)
  qualifies functional source commit `bad9c2831f4084dc40880a784e5d897e7a9fcd8f`:
  21 selected real-store/fleet/privacy tests, native distribution checks and the
  actual API/worker image restart/recovery checks pass. Exact image
  `sha256:c8b3a4b0b629d9ca90e342adcfa56912eb523cdc17d79cc9793585e8959a2a59`
  still has 44 HIGH matches across eight advisories, zero CRITICAL and no fixed
  versions listed in that scan. The security gate and overall run remain failed;
  findings are unsuppressed and merge remains withheld.
- The refreshed complete dashboard dependency audit retains five HIGH findings
  in its development ESLint/glob chain. The underlying
  [braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) lists no
  patched release as checked on 20 October. Production dependencies remain at
  zero findings. No incompatible framework downgrade or scan suppression was made.

Sanitized logs, XML and the policy inventory are in `remediation-evidence` with
the `2026-10-20-canonical-` prefix. Fixture data and originals were retained. No
private owner replies, service keys or profile credentials are release artifacts.

## Phase status and remaining work

| Phase | Current status | Still required |
|---|---|---|
| 0 - Preserve and baseline | Preservation and synthetic baselines established | Owner confirmation of exposed-key revocation and recovery custody |
| 1 - Access control | Canonical boundaries, manifest, adapters, reviewer role and regression checks implemented; separate service-user assets prepared | Install/verify private service/operator OS separation and deployment-specific index credentials; broader legacy capabilities remain outside canonical admission |
| 2 - Consistent memory and retrieval | Canonical memory, transport adapters and actual default-stack delivery/recovery implemented | Qualify the deployed configuration and any separately selected legacy/provider paths; no automatic bulk migration or permanent erasure |
| 3 - Packaging and release | Small native artifact, locks and actual minimal API/worker image recovery pass; unsuppressed restricted-image HIGH/CRITICAL gate now passes | Dashboard development advisories, lower-severity image findings, broader legacy-image review and supported private deployment configuration |
| 4 - Hermes provider | Earlier native provider installed and model-tested; newer eight-tool update implemented | GitHub-only delivery of this update, schema/grant upgrade, installed-host and model-driven requalification inside Ubuntu-Hermes |
| 5 - Isolated qualification | Current 77-test suite, real graph recovery, bounded concurrent load and service/client/browser checks pass | Longer soak/broader retrieval assessment, selected local chat-model qualification, isolated deployed service checks, owner-managed recovery test and review before everyday/other-project activation |

The installed Hermes version previously refused the local chat endpoint's
8,192-token serving window because it requires at least 64,000. Reusing an
existing Unsloth route does not change that served limit. Earlier model-driven
synthetic checks used the already configured authorized cloud route; they do not
qualify the chosen local serving configuration. No guard was bypassed.

Windows WSL-control executables currently fail to launch from this Workspace
session (`Exec format error`), and the local Docker control socket is unresponsive.
These are environment limitations, not a missing paid plugin or approval. Native
Workspace fixtures let independent implementation/tests proceed. WSL mounts,
firewall, interop configuration and existing services were not changed to bypass
the limits. Restoring operator access is needed to deliver/recheck the newer
provider in Ubuntu-Hermes. A hosted image workflow also exercises the actual API
and indexing-worker images together, including worker restart/backlog recovery.

## Owner actions before private activation

Backup destination update, 20 October: the owner approved
`/var/backups/enhanced-cognee` inside Ubuntu-Hermes. The scheduled backup system
unit and private credential launcher now use that exact destination. They do not
accept inherited output-directory overrides or recovery/decryption keys. This
resolves the destination decision; installation, daily scheduling and recovery
verification inside Ubuntu-Hermes remain pending while WSL control is unavailable.

All nine architectural/policy decisions were already answered; no repeat approval
is needed to continue the authorized fixes or publish the implementation branch.
The remaining owner-controlled evidence is specific: confirm real exposed keys
were revoked/replaced, keep recovery copies of the generated keys in the password
manager, and verify recovery at the approved local daily backup destination.
Existing whole-WSL and cloud backups do not establish service recovery.
An operator must apply and verify a service account/credential boundary before
Hermes handles private memories. Synthetic tests sharing its OS user do not
provide that boundary.

Publication is authorized. Merge remains conditional on complete implementation
and working required checks. This checkpoint does not satisfy every remaining
release/activation requirement, so it must not be described as fully complete or
merged solely because the local tests passed.

Use [the operator runbook](../../../runbooks/CANONICAL-MEMORY-AND-INDEXES.md)
for schema, index, project-client and isolated Hermes upgrade instructions.
