# Ubuntu-Hermes synthetic deployment - 20 October 2026

The updated native API, schema-3 worker and eight-tool provider now work with
four real stores in the dedicated synthetic environment. Private/everyday use
is NOT admitted. Protected OS installation, daily scheduled backup execution,
local selected capture, owner custody and release acceptance remain open.

## Environment and source

- Verified Ubuntu-Hermes, Ubuntu 24.04.4 LTS, user `vincentspereira`.
- GitHub fetch resolved delivery source to
  `3b05b4ae996c0d605e143a76397c4109abfba3b1`, a descendant of the required
  `474d21d96fe682a22fd2144d2c4c7e3b3b8f395a` checkpoint.
- Work is on `codex/hermes-ubuntu-deployment-20261020`; main was not merged.
- Installed Hermes 0.22.2, source `d923a5eb487a17c0a68801bba9ef0f56c81040a8`,
  actual managed CLI Python 3.14.7. A bare interpreter lacks managed dependencies;
  the host tests use Hermes' reported runtime bootstrap and its own profile store.
  Desktop installation/version was not independently qualified.
- Service Python 3.12.13; built `rnr-enhanced-cognee-memory` 1.1.0 from this
  fork using hashed build/index/MCP dependencies. Wheel boundary, installed
  imports outside the checkout and `pip check` passed. The upstream Cognee
  engine was not installed into Hermes.
- The API/worker use the installed wheel from the isolated `.venv-deployment`
  environment, with working directory `/tmp`. That environment remains in the
  user's writable home; it is not the protected `/opt` installation.

## Instruction reconciliation

Read the actual global Codex and Claude files, repository instructions, relevant
parent paths and the preserved originals in the newest relevant
`~/hermes-instructions-before-klww4qpa` folder. No configured instruction fallback
or size override was found. `CODEX_HOME` was unset; the active global source is
`~/.codex/AGENTS.md`. No applicable override or `AGENTS..md` was found.
Relevant home/workspace Claude files and a checkout-root CLAUDE.md were absent.

Original bytes, original paths/modes, hash manifest and raw comparisons are in
the restricted private home archive
`~/hermes-instruction-reconciliation-20261020T142603Z`. Archive hashes were
verified. Claude instructions, configuration, credentials and model routes were
not changed. No nested Codex session was started.

The global Codex instructions now retain unique local project exclusions,
assigned-repository scope, caller budget/turn limits and human merge review.
Old Windows/Workspace directory examples and old Docker/GPU status were treated
as historical evidence rather than access authority or current capability.
Only a portable reconciliation reminder enters repository AGENTS.md; private
originals and raw diffs are not publication artifacts.

The resulting global/root instruction sizes are 15,639 and 8,857 bytes:
24,496 bytes before separators, below the default 32 KiB budget. They were read
for this session; their standard discovery paths are ready for a future session.
No automatic proof of a new session's loading is claimed.

## Preservation and actual deployment

Before changes, preserved and hashed 87 synthetic profile/credential files and
retained the earlier runtime source. The encrypted pre-upgrade backup was
authenticated and restored to a new database: 33 records and 46 versions matched,
including exact encrypted history. Earlier checkouts, databases, notebooks,
credentials, failed fixtures and backups remain present.

Applied the additive schema-3 migration to the original test database without
replacing encryption/signing keys. The first worker correctly reported degraded:
31 older, unrelated synthetic fixture records could not be decrypted with the
installed service key. Their keys were not guessed, and their events were not
falsely marked complete.

Made a copy-only migration of `qualification/hermes_test` into
`cognee_hermes_selected_20261020` in the existing native PostgreSQL cluster.
At migration, all six selected records, 16 versions, 16 events and 16 audit
entries matched exactly. The original `cognee_hermes_test` database remains intact.
New runtime/worker roles were provisioned for the selected database. Both the
new and old canonical data retain the original encryption key. Further tests
added synthetic records; those migration counts are a dated snapshot.

Current synthetic topology:

| Component | Placement and scope |
|---|---|
| API | Loopback 28080; selected database; API database/graph reader credentials |
| PostgreSQL | Existing native 16.15 cluster, loopback 28434; preserved old databases |
| Qdrant | New native 1.18.3, loopback 28535; distinct write/read API keys |
| ArcadeDB | New native 26.9.1, loopback 28536; database-scoped reader/writer groups |
| Valkey | New locally built 7.2.13, loopback 28537; worker namespace ACL |
| Index worker | Separate database and derived-store credentials; `hermes_deploy_v1` pipeline |
| Hermes profiles | `enhanced-cognee-test` and newly created `enhanced-cognee-test-two` |

Qdrant/ArcadeDB published release digests were verified. Valkey source came from
its pinned GitHub tag; its tag object and downloaded archive hash were recorded.
No Docker startup, mount, firewall change, Windows/Workspace access, model-weight
copy, cloud backup upload or everyday/bot activation occurred. Existing
unidentified stores/listeners were not reused. These are manually launched
synthetic processes, not installed persistent services.

## Test evidence

Machine-readable sanitized metadata and artifact hashes:
[2026-10-20-hermes-deployment.json](remediation-evidence/2026-10-20-hermes-deployment.json).
Raw traces, operator scripts, fixtures and recovery material remain private in
`~/agent-workspace/enhanced-cognee-test-runtime`.

| Scope | Result |
|---|---|
| Final current qualification suite | 73 passed, 0 failures/errors, 4 skips, 80.35 seconds |
| Skips | Node/Go/Rust live clients and built-dashboard browser prerequisites not prepared here |
| Installed first-provider lifecycle | 11 passed after schema upgrade and again after selected migration |
| Provider/operator targeted checks | 14 passed after prompt clarification |
| Installed graph/API checks | Six passed: two-hop provenance, project denial, actual worker restart/backlog recovery, current correction, retraction, three retained versions |
| Installed second-profile/library checks | Six passed: private denial, sanitized sharing, membership revocation, correction review, publication revocation, actual second Hermes loader/scope |
| Store credential boundaries | Eight positive/negative checks passed; graph reader cannot write, graph worker cannot create a database, Qdrant reader cannot write, Valkey worker cannot leave its namespace or administer the store |
| Database role boundaries | API, worker, backup and restored API deny schema creation, history update and record deletion; worker/backup also deny record update |

The first suite run passed 72 with five skips; subsequent authenticated four-store
qualification removed the index-store skip. This does not turn the four remaining
skips into passes. Full legacy, image and frontend qualification was not rerun
as an installed-host claim.

The final test command was `python -m pytest tests/qualification/ -q -s -p
no:cacheprovider --override-ini=addopts=` with explicit private
`RNR_QUALIFICATION_DATABASE_URL`, `RNR_QUALIFICATION_MODEL_CACHE` and
`RNR_QUALIFICATION_INDEX_SETTINGS`, plus a 60-second synthetic soak. Logs, JUnit
XML and fixtures were retained outside Git. Installed-host checks used private
operator runners and the actual Hermes runtime bootstrap; they were not pytest
host shims. The eight proposed publication files passed Gitleaks 8.30.1 with
zero detected secrets, ASCII validation and `git diff --check`.

The final 60.07-second, four-project real-store exercise completed 150 rounds:
600 corrections, 750 semantic queries, 600 graph queries, zero observed scope
leaks/failures and zero pending events. Round p95 was 528.78 ms. It measured
1,354 calls to the local embedding method and no chat calls. Database size grew
from 8,649,751 to 25,166,351 bytes while retained versions grew from six to 610.
These counters cover the fixture workload, not the separately running API.

Twelve installed API semantic queries measured median 44.62 ms and p95 179.37 ms.
The 82.25-second resource observation sampled every two seconds. Peak RSS was
approximately 310 MiB API, 303 MiB worker, 73 MiB Qdrant, 171 MiB ArcadeDB,
6 MiB Valkey, 460 MiB PostgreSQL process tree and 674 MiB qualification workload.
RSS double-counts shared pages; component peaks are not simultaneous totals.
CPU deltas and PSS coverage are in the JSON. The chat server, Hermes and GPU are
excluded. No production capacity, long-soak or memory-leak conclusion follows.

## Model behavior and repairs

The configured authorized GLM-5.3-Flash cloud route was used only with invented
facts, with temporary test settings restored byte-for-byte afterward. A fresh
fixture passed selected automatic capture, new-session recall and clear
correction, but initially FAILED ambiguity handling: the model changed the
decision to undecided rather than calling `enhanced_clarify`. The changed
synthetic version and failed trace are retained.

Strengthened the provider prompt to say explicitly that uncertainty must not
rewrite a standing decision to undecided, save alternatives or retract it.
After preservation-aware plugin upgrade, a new five-scenario cloud run passed:
capture, recall, versioned correction, ambiguity clarification without mutation,
and invented-credential refusal without a write. This is measured behavior for
that run, not a universal model guarantee or semantic enforcement proof.

The unchanged configured local Granite route completed a bounded chat, but
FAILED automatic capture: it answered the invented planning question without
calling a memory tool. Its exact served context window could not be established
from current authenticated metadata. The old 8,192-token result remains historical;
the current route was not relabelled as meeting Hermes' 64,000-token requirement.
Local selected capture and the full local lifecycle remain unqualified. No guard,
context setting, fallback or model capability was falsified.

Other retained harness failures: the old correction scenario started with an
already corrected fixture; a custom sharing runner used the wrong correction
URL before switching to PATCH; bare-runtime smoke needed explicit profile
dotenv loading. Those corrected runner results are distinct from application
defects. A recovery readiness assertion also failed initially; subsequent direct
delivery inspection and bounded polling verified replay. Its original timing
failure was not conclusively isolated.

The real-store qualification runner now accepts optional Qdrant write/read keys
for provisioning, reader, API, rebuild and point checks. Authentication stayed
enabled throughout. README schema/graph descriptions were corrected to match
the current implementation.

## Backup and recovery

Created a dedicated read-only backup database account and persistent signing
configuration containing only its database URL, manifest key/ID and public age
recipient. It contains no memory decryption key, JWT key or age private identity.
Generated a completed encrypted archive/manifest pair in the private synthetic
backup folder, authenticated it and restored into
`memory_restore_selected_20261020_162017`.

Compared the restored canonical data: 15 records, 30 versions, 42 audit entries,
two library memberships and one publication matched. All current payloads
decrypted, cross-project denial held, actual restored role restrictions passed,
and retained events rebuilt into a fresh Qdrant/ArcadeDB/Valkey namespace with
working source-linked graph recall. Failed/intermediate fixtures remain present.

This is actual synthetic encrypted recovery, NOT execution of the scheduled
root-owned backup service. `/var/backups/enhanced-cognee`, `/etc/enhanced-cognee`
and `/opt/enhanced-cognee-memory` remain absent. The daily timer is not enabled.
No owner password-manager custody confirmation has been supplied.

## Exact remaining operator and owner work

1. Establish an approved service-manager route. PID 1 is WSL init; systemd reports
   offline. Enabling systemd requires an owner-controlled host configuration and
   distro restart, affecting more than this test service. No such change was
   made. An alternative supervisor needs equivalent credential/isolation and
   scheduling qualification; manually detached processes are not equivalent.
2. Use operator authentication at a local terminal. `sudo -n true` requires a
   password. Do not supply that password in chat. Install the reviewed native
   runtime under `/opt/enhanced-cognee-memory`, with an accessible protected
   Python 3.12 interpreter, hashed dependencies, public offline model files and
   non-secret index settings outside the user's home. Retain originals first.
3. Install separate protected API/worker/operator/store identities and root-only
   role credential files using the existing deployment templates. The current
   user belongs to sudo and Docker groups; noninteractive arbitrary root was not
   demonstrated, and the Docker CLI points to an unavailable external link.
   Review effective privilege paths and prove ordinary agents cannot read keys,
   modify runtime/store data or become an operator. No groups were removed and
   no global privileges weakened. Current same-user synthetic credentials fail
   the required private-filesystem boundary.
4. Prepare root-owned mode-0700 `/var/backups/enhanced-cognee` and root-only
   `backup.json`; install protected compatible PostgreSQL and age tools. Install
   the supplied backup service/timer only after the root-owned service's real
   backup/restore, permission and index-rebuild tests pass. Verify enabled state,
   next run and missed-run catch-up. Retain every existing generation.
5. Owner: privately retain/review recovery material in the password manager,
   confirm exposed historical credentials revoked/replaced, and review these
   synthetic results before any private/everyday or other-bot activation.
6. Qualify a local route that actually performs selected capture and establish
   its served context capacity without overrides that misrepresent it. The
   already authorized cloud route is a tested synthetic alternative. Arrange
   scoped token renewal before unattended use; no renewal daemon was installed.
7. Keep release gates open. At the fetched revision GitHub returned one passing
   canonical-browser check and two failing frontend checks in run
   [39423649799](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39423649799).
   This is not a fresh pass of all runtime/image/legacy/release gates. The prior
   unsuppressed advisory requirements remain applicable. No main merge.

Use `docs/runbooks/CANONICAL-MEMORY-AND-INDEXES.md` and the unchanged hardened
units in `integrations/hermes/deployment/` for the reviewed target configuration.
ArcadeDB's [upstream configuration source](https://github.com/ArcadeData/arcadedb/blob/26.9.1/engine/src/main/java/com/arcadedb/GlobalConfiguration.java)
and [user/group documentation](https://docs.arcadedb.com/arcadedb/how-to/operations/groups)
were consulted for native loopback configuration and database-scoped roles.

Implementation, synthetic host qualification, protected deployment, scheduled
recovery and private acceptance remain separate stages.
