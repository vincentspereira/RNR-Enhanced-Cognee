# Workspace continuation and isolated deployment handoff

Date: 20 October 2026. This is an additional implementation checkpoint, not a
claim that all phases or private/everyday activation are complete. Source changes
are published on `codex/hermes-memory-hardening`; main remains unmerged.

The later [instruction reconciliation](AGENT-INSTRUCTION-RECONCILIATION-2026-10-20.md)
records the Claude/Codex comparison, preserved originals, portable root AGENTS.md
delivery and the actual Hermes-local instruction checks still required.

## Completed from this Workspace session

### Source delivery and frontend behavior

The broad Python `lib/` ignore rule also excluded 27 pre-existing dashboard
TypeScript library files. Local builds could use those files even though GitHub
could not deliver them. A scoped ignore exception now includes maintained
dashboard libraries. Their local material is preserved in the ignored
`.archive/2026-10-20-dashboard-qualification` folder. New code was scanned before
publication. A clean export of the Git index, subsequently committed as
`16ee6a954bdfef9d8ee2cd9e155285d88a55710c`, installs with fresh dependencies,
builds both frontends and passes the actual browser/database test.

The dashboard's 23 initial lint errors and the upstream frontend's 25 errors
under its repaired lint command were corrected without disabling rules. The
dashboard retains one React Virtual compiler compatibility warning; the older
frontend has zero lint warnings. The default Vitest command now selects its unit
tests rather than mistakenly loading the separate Playwright suites.

Implemented repairs include proper memory response types/identifiers, React
subscription/lifecycle handling, stable reconnect backoff, validated persistent
preferences, failed-save reporting and cancelled-draft behavior. The upstream
notebook renderer now uses a real React error boundary and bounded nested result
rendering. These lint/type repairs do not qualify every historical notebook,
analytics, graph or session screen against every provider.

Fabricated analytics growth/activity/sparkline/trend measurements were removed.
Missing measurements remain empty, and an unavailable statistics response gets
an explicit error rather than invented values or a non-null assertion crash.
Ten dashboard unit tests pass, including cross-origin credential refusal and
preference persistence/cancellation/error handling. A real browser exercises
canonical memory creation, detail, correction and retraction against PostgreSQL.

### Development-tool source backport

Both npm production audits remain clean. Their complete audits each retain five
HIGH findings in the braces/micromatch/fast-glob/Next ESLint development chain.
The [official advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) lists no
patched release; the npm registry still reports braces 3.0.3.

A local source backport adds bounded parser/AST recursion. The maintained
applier verifies exact original hashes of all four files, validates every file
before writing, refuses source drift/escaped files, preserves originals and
supports repeat application. It does not alter package versions, audit output
or advisory severity. `prelint` and `prebuild` apply it explicitly after the
locked installation. Checked generated copies keep each standalone frontend
and Docker context independent of an outside source directory.

The bounded regression runner reproduces the original stack overflow with an
8,003-character pattern, then verifies rejection of nested strings and direct
cyclic ASTs, ordinary/escaped expansion, real fast-glob matching, repeat
application and refusal of modified/escaped sources. Source backporting reduces
the tested trigger's risk; it is not an official patched release or universal
glob-resource guarantee. The full frontend release gate deliberately still
fails on the version-matched advisory. No suppression, unsafe downgrade or fake
version was introduced.

Frontend Docker inputs were repaired: pinned Node 22, full build dependencies,
standalone dashboard output, self-contained backport files and secret context
exclusions. The older upstream frontend's Docker target remains a development
server. A successful image build is not a security scan, hosting approval or
private/public deployment qualification.

### Sustained 42-space fixture and resources

The opt-in real-store workload now accepts 2-42 concurrent synthetic spaces and
up to 30 minutes. This continuation ran **900 seconds requested, 901.34 seconds
of workload**, across 42 spaces, using real PostgreSQL, Qdrant, ArcadeDB and
Valkey with the offline local BGE search model. It completed:

- 150 full write/index/recall/check rounds.
- 6,300 corrections, 6,450 semantic queries and 6,300 graph queries.
- Zero observed scope leaks, failed assertions or remaining pending events.
- 12,792 measured local embedding-method calls and zero chat-model calls.
- 8,923.14 ms p95 for an entire 42-space round, including writes, indexing and
  recall. This is not a per-request HTTP latency measurement.

Current rows grew from four to 46 after the 42 initial records; retained versions
grew from six to 6,348. The selected fixture database grew from 8,649,751 to
110,083,095 bytes, including retained versions, events and database allocation.
This is approximately 96.73 MiB of additional fixture storage. Keep monitoring
history growth; no automatic deletion or retention-policy change was introduced.

A separate observer sampled the explicitly selected process trees 438 times
over 906.8 seconds. It never reads process arguments, environment values or
private file contents. Peak proportional-memory observations were approximately:

| Fixture tree | Peak PSS MiB | Observed CPU seconds |
|---|---:|---:|
| PostgreSQL and its children | 180.12 | 367.34 |
| Qdrant | 117.27 | 21.83 |
| ArcadeDB | 195.82 | 85.09 |
| Valkey | 7.22 | 1.59 |
| Python qualification workload, memory service/indexing and local embeddings | 428.33 | 770.25 |

These are independent sampled component peaks, not a simultaneous machine-wide
peak. One PostgreSQL PSS sample was incomplete because process reads are not
atomic; no selected backend root disappeared. RSS includes shared pages and is
reported separately. Other laptop work, including frontend builds, occurred
during observation. The fixture does not qualify 42 concurrent Hermes chats,
Unsloth/GPU resources, HTTP throughput, production capacity or absence of memory
leaks. PID attribution, process-tree boundaries, recycled PIDs, missing PSS and
failing-workload propagation have three passing regression tests.

## Verified checks and release boundaries

[Required CI 39411603494](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39411603494)
passes on functional revision `16ee6a954bdfef9d8ee2cd9e155285d88a55710c`:
4,293 unit tests, three legacy schema tests, ten settings/security tests and 64
canonical memory tests, all with zero failures/errors/skips. The independent
credential-scrubbed/network-denying local unit run also passes all 4,293 tests.

[Memory image run 39411568065](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39411568065)
passes 21 real-store tests, exact runtime smoke and actual API/worker restart
recovery. Exact image:
`sha256:4070546710bbdb6e3ec3a9635fea831b740a5840ae28942af714d3d97cd44dda`.
Its unsuppressed scan retains zero HIGH/CRITICAL/UNKNOWN, 26 MEDIUM and ten LOW
matches. This does not qualify the larger legacy image or optional providers.

[Initial clean-frontend run 39411568026](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39411568026)
passes both frontend lint/build checks, all ten dashboard units and the actual
browser/PostgreSQL test. Its only failed steps are the two enforced complete
dependency audits.
[Backport/frontend run 39413284329](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39413284329)
on `474d21d96fe682a22fd2144d2c4c7e3b3b8f395a` also passes the original-exploit
reproduction/backport checks, both standalone frontend Docker builds, both
lint/production builds, ten dashboard units and the actual browser/database test.
Its only failed steps remain the two enforced version-matched development
dependency audits. Frontend Docker build success is not image-security or
private/public hosting qualification.

Evidence is under `remediation-evidence/2026-10-20-workspace-*`. Raw private fixture
logs, generated secrets and recovery material are not publication artifacts.
The earlier full-image, optional-provider and dated reports retain their narrower
scope and remaining findings.

## What must happen in the other environments

| Location or owner | Remaining work |
|---|---|
| Ubuntu-Hermes operator session | Verify actual host/source; preserve and upgrade the test service/provider; apply schema/index grants; install and prove separate service/operator boundaries; run installed host/model tests; create approved-path backup, prove restore and enable/check its timer |
| Existing Unsloth/model setup | Verify the real served context window against the installed Hermes requirement and measure the chosen local chat route; Workspace embedding tests are not that evidence |
| Vincent | Confirm real exposed candidates revoked/replaced and private recovery copies held in the password manager; review qualification before everyday/other-project activation |
| Windows session | Verify v11 under actual Windows PowerShell/DPAPI, update any scheduled-task script path and run/check the real backup/cloud recovery chain using the existing private guide |
| Upstream/frontend release review | Keep version-matched development findings visible despite the tested source backport; review an eventual fixed upstream release and remove the backport only after verification |
| Separately selected legacy/provider scope | Supply appropriate disposable endpoints/credentials and qualify that configuration before admitting it; do not assume unit mocks or canonical containment qualify every enterprise feature |

No mount, firewall, interop, everyday profile, private-data import, cloud upload,
permanent erasure or main merge was performed from this session.

## Ready-to-use Ubuntu-Hermes prompt

Use [the complete deployment handoff](../../../runbooks/UBUNTU-HERMES-DEPLOYMENT-HANDOFF.md).
It provides the exact new checkout folder, safe startup commands and the full
task prompt for Codex CLI or Hermes Agent Desktop. It preserves the previous
qualification checkout/runtime and carries forward all answered owner decisions.
The new session must perform the actual host checks; this document does not
certify them in advance.
