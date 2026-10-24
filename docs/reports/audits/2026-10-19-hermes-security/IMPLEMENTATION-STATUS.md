# Remediation implementation status

Latest checkpoint: [reconciled Hermes/Workspace results](HERMES-WORKSPACE-RECONCILIATION-2026-10-20.md).
The published Hermes branch is reviewed and incorporated. Its complete 78-test
synthetic suite and local 27B capture passed; protected installation/backups,
owner custody, Windows recovery and frontend release conditions remain open.
The earlier "session is running" observations below are preserved history.

Latest independent Workspace repair: [release safeguards](WORKSPACE-RELEASE-GUARDS-2026-10-20.md).
Required main protection now covers unit, real-stack/image, browser and both
frontend lanes; exact-revision evidence checking refuses stale/missing results.

Current phase ledger: [pending phases and parallel work, 20 October](PENDING-PHASES-2026-10-20.md).
The owner reports the isolated Hermes deployment prompt is running in its own
Codex CLI session. That host's results remain to be reviewed; the start of a
session is not evidence of installed-host acceptance. The ledger also separates
credential ownership/revocation from recovery custody and native Windows checks.

Latest Workspace checkpoint: [completion and isolated deployment handoff](WORKSPACE-COMPLETION-2026-10-20.md).
This supersedes earlier counts/status below: 4,293 unit tests with zero skips;
clean frontend delivery, local advisory backport and measured 42-space load.
Private installed-host/model/recovery/owner requirements remain open.

Latest continuation: [canonical stack update, 20 October 2026](CANONICAL-STACK-UPDATE-2026-10-20.md).
That report records schema 3, implemented default-stack workers, canonical
adapters, real cross-language/MCP/browser tests and the exact remaining work.
The earlier checkpoints below are historical; the new report supersedes statements
that the graph worker or live Hermes installation is entirely absent.

Latest continuation: [20 October implementation update](IMPLEMENTATION-UPDATE-2026-10-20.md).
Owner decisions have been received. Selected automatic capture, reviewed library
groups, schema/runtime permission separation and encrypted backup tooling are now
implemented under qualification. The tables below retain the 19 October checkpoint;
read the dated update and [live Hermes report](HERMES-LIVE-QUALIFICATION-2026-10-20.md)
for the current continuation. The branch is published; the native Hermes test
lane passes 69 checks and the full chat capture/recall/correction/clarification
scenarios have been exercised. Everyday/private activation and merge remain open.

Date: 19 October 2026
Branch: codex/hermes-memory-hardening
Baseline: e25bd6356e38970c525e0258bdac983cd4079d29

The REMEDIATION-AND-HERMES-PLAN.md is actively being implemented. It is not a
second plan waiting to start. This is an implementation checkpoint, not completion
of all findings or authorization to activate private memories. No changes have
been committed, pushed, merged, or installed in the everyday Hermes profile.

New findings F28-F36 and their repairs are in [ADDITIONAL-FINDINGS.md](ADDITIONAL-FINDINGS.md).
See [the finding matrix](REMEDIATION-MATRIX.md) for each original finding,
[the migration runbook](LEGACY-MIGRATION.md) for the copy/upgrade behavior, and
[remediation evidence](remediation-evidence/) for results after repairs. The older
`evidence/` directory remains the original audit baseline.

| Plan phase                 | State                                                                              | Implemented and remaining                                                                                                                                                                                                                                                                                                                                                               |
| -------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0 - Preserve and baseline  | Baseline preserved; owner credential work pending                                  | Local branch and archived originals retained. Real historical key revocation/replacement needs account-owner evidence.                                                                                                                                                                                                                                                                  |
| 1 - Access control         | Substantial repairs; broader qualification remains                                 | Policies for all 122 tools; shared authentication and identity binding; streaming body size/time limits; file/origin/source grants; upstream global APIs denied to tenant callers. Complete side-effect metadata and all-provider coverage remain.                                                                                                                                      |
| 2 - Storage and recall     | Restricted canonical core tested; legacy consolidation and graph work remain       | Encrypted/versioned records, atomic events/audit, retry safety, correction/expiry/isolation/reviewed sharing, source declarations and correction lineage. Named keys and bounded current/history rotation tested. UUID/TEXT copy migration and actual schema upgrades pass. Full legacy delegation, graph/vector workers, derived cleanup, private recovery custody and erasure remain. |
| 3 - Packaging and checks   | Current full/restricted builds and runtime checks pass; security gate remains open | Three hashed locks; actual full-image dependency/API/registry/MCP checks; restricted HTTP checks with old/named key formats; both frontend builds pass. OS findings and the full image's version-matched Cognee advisory remain visible. Remote CI not run.                                                                                                                             |
| 4 - Hermes provider        | Implemented; live installation pending                                             | Six restricted tools, per-profile config/secret lookup, explicit capture only, bounded fresh recall and optional source declarations. Nine host-shim tests pass; this is not a live Hermes installation.                                                                                                                                                                                |
| 5 - Isolated qualification | Synthetic checks passing; everyday activation pending                              | Real PostgreSQL, offline search, upgrade/copy fixtures, protocol and built restricted-image tests passed. Wider retrieval quality, graph, default-stack failure/load checks and actual Hermes profile tests remain.                                                                                                                                                                     |

## Verified checkpoints

- Latest full unit lane: **4,293 passed, 0 failed, 0 skipped**, with real credential settings
  removed and outbound TCP denied. This uses the existing developer environment
  with compatible temporary pytest/MCP/dependency overlays; it is not the installed
  full-image unit suite.
- Restricted qualification lane: **52 passed**, including real disposable
  PostgreSQL, an offline local semantic model, provider host-shim checks, copy
  migration, text-cache/capability restrictions, source declarations, correction
  lineage, key rotation/rollback and repaired legacy tenant mutations.
- Legacy installer/upgrade lane: **3 passed** on real disposable pgvector.
  Covers a fresh Alembic installation, the older UUID Docker installer and an
  existing TEXT installation with a tenant table. Original records and vector
  dimensions are preserved.
- Upstream settings/ownership/log preservation lane: **10 passed**, including
  actual authentication dependency denial and an in-memory SQLite ownership test.
- Real stdio protocol: initialization, listing **122 tools**, readonly mutation
  denial and error-result handling passed. Diagnostics did not corrupt JSON-RPC.
- Built restricted image: actual HTTP checks passed for authentication, retry
  identity, project denial, recall, reviewed sharing/revocation, version conflicts,
  correction and retraction. The newer Debian 13 image passed the same behavior
  checks; its container scan remains a separate gate.
- Current full image snapshot: clean build and dependency check pass. Both APIs
  and all 122 tools import with production tenant enforcement. A real MCP child
  process initializes, lists tools and denies a readonly mutation with no external
  network, a read-only filesystem and dropped capabilities. Its application paths
  contain no local memory stores or runtime pip, and critical runtime source
  hashes match. Optional scheduling is correctly unavailable without its extra.
- Standalone Python SDK wheel builds and imports outside the repository. SDK
  registry-signature tests catch invalid forwarded fields. The checkout compatibility
  imports now use the same maintained SDK code.
- Node client: **9 passed**. Rust client: **9 passed plus 1 documentation compile
  test**. Go client suite: **passed with the race detector**. These exercise local
  mock servers/transports, not every live backend or the restricted native API.
- Both frontends pass clean production builds with type checks; the dashboard's
  existing Button tests pass (**5 tests**). Browser login/E2E remains unqualified.
- Restricted/full Python release locks and the new bootstrap lock each reported
  **no known vulnerabilities** in their advisory scans. These results do not cover
  every optional dependency set or the unchanged developer virtualenv.
- Both frontend **production dependency** scans reported zero findings. Each full
  frontend audit still reports **five high development-tool findings** in the
  upstream braces/micromatch ESLint chain, with no safe patch in those locks.
- Source syntax (**1,801 Python files**) and critical undefined-name checks pass.
  Static repair alone does not qualify the older deployment/recovery/reporting
  scaffolds operationally. The changed/new-source diff has no credential findings.
  A separate whole-file scan flags one inherited Slack URL example; it is present
  at baseline and contains placeholder wording, and is not a newly added secret.
- A disposable encrypted PostgreSQL dump was restored into a separate test
  database; the retained test key could decrypt/recall it and project denial held.
  This is not evidence of an owner-managed private-data backup system.

## Container scan finding and response

The earlier Debian 12 restricted image had 282 OS package/advisory matches,
including 61 high and 2 critical matches, plus 6 findings in its bundled pip.
Counts include repeated advisories across related packages; they are scanner
matches, not 288 independently reproduced application exploits. Many OS entries
had no fixed version offered in that release. They are not silently ignored.

The image definitions now select the official Python 3.12.15 Debian 13 base and
install a hashed bootstrap lock containing pip 26.2.1. The restricted image was
rebuilt and its functional checks passed. After removing the unused runtime installer and its vendored components, the
restricted image scan reports **zero Python-package findings and zero critical OS
findings**. It still reports **44 high OS package/advisory matches across eight
distinct high advisories**, with no fixed distribution version listed. Those
remain visible and the new image gate is expected to fail until a justified
resolution is reviewed. The clean full image also built and passed runtime
checks. Its scan remains a separate gate: the reviewed Debian 13 snapshot has
44 high OS matches and one critical Python match for CVE-2026-58473 against
`cognee==1.0.9+enhanced`, despite the tested settings backport. No version label
has been changed and no advisory has been suppressed to make the gate pass.
See [the container advisory review](CONTAINER-ADVISORY-REVIEW.md) for the eight
upstream trigger descriptions, inspected component paths and remaining limits.
Additional image hardening removes setuid/setgid file modes while retaining files
and keeps application code owned by root. The full service account owns only its
explicit data/log/tmp directories. These controls do not constitute patched OS
package versions or a waiver of the scanner gate.

## Preservation exceptions and artifact boundary

One older user log was deleted by an existing import-time cleanup before that
behavior was disabled; [the incident record](IMPLEMENTATION-INCIDENT.md) describes
the observation and correction. Earlier local full images also included an
unexamined local database file because exclusions were incomplete. They have not
been published and are excluded from release. Source stores remain intact. New
wheel/context exclusions and actual artifact checks address this packaging gap;
older local copies/cache are retained pending reviewed cleanup.

## Boundaries and remaining work

The restricted API uses canonical encrypted record tables. It does not yet replace
all legacy memory routes. Its graph and change-feed-worker capabilities are
explicitly **unavailable**. Optional local semantic recall is not graph reasoning.
Outbox events are durable records, not proof of a working Qdrant/ArcadeDB pipeline.
Legacy storage paths are not universally encrypted and must not be admitted as
private Hermes storage. Retraction retains encrypted history; it is not permanent
erasure.

Database qualification used disposable operator-capable PostgreSQL accounts.
Canonical startup currently performs additive schema bootstrap/validation; a
separate schema-provisioning role and restricted runtime DB-account qualification
remain deployment work. The tests do not establish a least-privilege production
database installation.

Local search uses a free MIT-licensed BAAI/bge-small-en-v1.5 model (384 dimensions)
loaded from a prepared offline cache. One paraphrase fixture passed; broader
language, conflict, stale-fact and multi-hop evaluation remains. No paid video
app, hosted embedding service, or existing private memory store was used.

Hermes remains isolated in Ubuntu-Hermes. Integration code must arrive through
GitHub into its own checkout. The installed Hermes version/contract was inspected
read-only; no provider was activated. Service placement, private-data admission,
key custody/revocation and final test-profile activation choices remain in the
plan's owner-decision section. No Windows mounts, WSL account changes, firewall
rules, paid services or outside-model processing have been enabled.

## Next implementation work

1. Finish the fresh container scans/rebuild, repair actionable findings and record
   any remaining upstream or configuration-dependent risks without suppressing them.
2. Consolidate legacy memory transports onto the canonical scoped service and
   qualify graph/vector/index workers, correction cleanup and durable recovery.
3. Complete model/graph retrieval quality, private key-recovery operations,
   source-verification workflows, retention/erasure and default-stack failure/load
   qualification. Canonical key rotation and source classifications are implemented;
   they do not by themselves establish these wider operational guarantees.
4. Reconcile remaining SDK/provider/frontend/browser and historical documentation
   contracts. New CI checks are prepared; remote execution/protection remains open.
5. Deliver the reviewed code through GitHub and qualify a separate Ubuntu-Hermes
   test profile when the applicable owner decisions and release checks permit it.
