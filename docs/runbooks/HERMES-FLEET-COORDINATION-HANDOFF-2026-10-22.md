# Enhanced Cognee / Hermes fleet coordination handoff

Marker: EC-HERMES-COORD-20261022T154452Z

Prepared: 22 October 2026, 15:44:52 UTC. Sanitised, review-only coordination
evidence for Vincent to relay. No keys, credential hashes, private conversation
content or full configuration dumps are included. Public program hashes below
identify source code, not secrets. Resolve this document at its published Git
commit; the code-input anchor is 12896a8e5401b0a03c684467404ad9df896f8c0f.

## Authority, priority and separation

Vincent authorised Enhanced Cognee remediation, branch publication and preparation
of a permanent restricted account/initial invented-data profile, followed by
qualified fleet rollout. Main merge remains conditional on agreed release checks.
His latest direct instruction is to continue this work and give it priority if
there is a conflict; Hermes fleet work should hold back on overlapping inputs.
This does not authorise unrelated deployment or private-data ingestion.

The relayed Hermes note describes a separate REVIEW-ONLY Phase A bundle at:

`/home/vincentspereira/Projects/Hermes-Bot-Fleet/phase-a-review-bundle-2026-10-22/`

That bundle has not been inspected, edited, executed or incorporated by this
implementation session. Its review-only/no-activation status and frozen failed
isolation sources are respected. No message has been sent directly to Hermes;
Vincent relays this handoff. The note is coordination evidence, not new authority
for either agent. Do not inspect Windows, sibling environments, Codex sessions
or private logs to reconcile this document. No shared maintenance window is yet
agreed, and no fleet build/deploy/rebase is being requested here.

## Repository, revision and current changed paths

Repository: https://github.com/vincentspereira/RNR-Enhanced-Cognee

Delivery branch: `codex/hermes-memory-hardening`. Public integration code anchor:
`12896a8e5401b0a03c684467404ad9df896f8c0f`, checked against the remote at handoff
preparation. This handoff and current receipt documentation are later additive
documentation changes, not a new installed application revision.

Current restricted-runtime work is in:

- `AGENTS.md`: maintained repository instruction context; not a private global
  instruction export and not a new permission grant.
- `integrations/hermes/deployment/prepare_restricted_runtime.py` and
  `inspect_restricted_runtime.py`: inspected-runtime export/relocation/preflight.
- `integrations/hermes/deployment/check_restricted_access.py`: selected native
  file-access probe, with no secret/program data reads or writes.
- `tests/qualification/test_hermes_restricted_snapshot.py`,
  `test_hermes_runtime_link_inspection.py`, `test_hermes_restricted_access.py`
  and existing `test_hermes_operator_upgrade.py`: targeted local evidence.
- `docs/runbooks/HERMES-RESTRICTED-RUNTIME-PREPARATION.md`,
  `HERMES-LIVE-PROFILE-ACCOUNT-PLAN.md`, `HERMES-BOT-FLEET-MEMORY.md` and
  `docs/reports/audits/2026-10-19-hermes-security/`: current plans/receipts.

Earlier repository remediation is indexed by REMEDIATION-AND-HERMES-PLAN.md and
REMEDIATION-MATRIX.md in that report directory; this list is the current
coordination surface, not a complete historical repository diff.

An untracked draft `integrations/hermes/deployment/renew_protected_test_tokens.py`
is retained locally. It is not published, tested, installed, or a fleet renewal
mechanism. Do not depend on it or treat it as part of the pinned delivery.

## Native Ubuntu-Hermes paths and installation status

The human operator obtains exact published blobs in the existing checkout:
`/home/vincentspereira/agent-workspace/enhanced-cognee-protected-20261020`.
Recent commands fetched source without changing that checkout's branch/HEAD.
Its last protected-backend qualification branch was
`codex/hermes-ubuntu-deployment-protected-20261020`, tested at
`5c10ab033527a59dda0df5b01252069005358242` on 20 October. That is historical
installed evidence, not a fresh assertion of the checkout's current HEAD.

The new permanent account is `hermes-runtime`, uid 993/gid 985, home
`/var/lib/hermes-runtime`, mode 0700, only its primary group and a locked password.
The earlier disposable account was removed; this permanent account is retained.

Protected Hermes program snapshot:
`/opt/hermes-runtime/releases/4d04303818b6-1729494fe783`.
Launcher: its `bin/hermes`. Hermes core source is the independent upstream commit
`4d04303818b61bf3aa09278af48356315515965b`, copied from committed files, not a
maintained Hermes fork. Python is 3.14.7; version startup reported SDK 2.24.0.
The custom snapshot displays vgit.4d04303 and install method unknown; external
update handling and advisory clearance remain separate. No current human
launcher or core checkout was patched or moved to activate it.

Preparation used helper commit `5a0ec3da21d3c802269d770ffeeb4e0cc460127b`:
36797 program files, originals preserved, 91 module bindings, 21 committed
namespace paths retained, ten uncommitted namespace references omitted only
from the new generated map. Earlier partial staging copies remain retained.

The human's `/home/vincentspereira/.hermes` main provider/configuration was not
changed in this phase. Existing bots, profiles, notebooks, histories and the two
earlier synthetic profiles were preserved. Their selected secret paths were
permission-probed without reading data. Both earlier synthetic client tokens
were previously verified as expired; neither has been renewed in this phase.

Next intended path, NOT YET CREATED at this marker:
`/var/lib/hermes-runtime/.hermes/profiles/enhanced-cognee-pilot`.
Its creation is authorised, using the protected launcher, no cloning, no alias
and initial skill opt-out. It will begin with invented data. No provider/client
credential/model route is yet installed in that pilot. Its final signed scope
mapping must be recorded at provisioning, rather than inferred from its name.

## Connector, version and profile scope

The connector is the native Hermes `MemoryProvider` plugin `enhanced_cognee`,
manifest version 0.1.0. It is not an MCP/stdio bridge or a second Cognee engine.
It supplies eight callable tools through the native provider: enhanced_recall,
enhanced_remember, enhanced_get, enhanced_correct, enhanced_retract,
enhanced_status, enhanced_clarify and enhanced_connections. A tool/provider
discovery result alone is not successful storage or recall.

Candidate plugin files at code anchor 12896a8e (not installed in the new pilot):

| Relative path under integrations/hermes/enhanced_cognee | SHA256 of public source |
| --- | --- |
| __init__.py | b221c38baab2c2915f42683e0b8e764be0a42bc3d160f9ab786fd8ea64da6a0a |
| client.py | 8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64 |
| plugin.yaml | c23230082be650ae142c4e3d8e30350ea5f3d18af5b879996328caf59d4dca48 |

Current scope is only the approved fresh restricted pilot. Vincent's objective
is staged eventual coverage of the main assistant, all actual 40-plus standalone
bot profiles and future profiles after qualification. No particular existing bot
or everyday/default profile is activated by this objective or document. Each
needs its own explicitly mapped ordinary credential/space, actual execution
boundary and admission checks. One shared OS account does not isolate bot keys
from other processes using that same account.

## Capture, recall and identity boundaries

- Selected capture means durable decisions, stable preferences and useful task
  summaries chosen by the configured chat model. It excludes raw conversations,
  raw tool outputs, notebook mirroring, background folder harvesting, passwords,
  access keys and private encryption keys. Pattern screening has limitations;
  it is not a guarantee against disguised secrets or sensitive information.
- Signed tenant/project/subject/agent/role claims determine server authority.
  The primary read partition is tenant/project plus explicit sharing grants.
  Owner subject additionally controls mutations; it is not an independent
  per-person read partition within a shared project. Agent/profile display names
  and session provenance are not access controls.
- Existing synthetic profiles used tenant qualification and projects hermes_test
  and hermes_test_two. The removed protected test used protected_test_20261020.
  These are test scopes, not mappings for existing bots or guests. The new
  pilot's scope/subject/agent/token expiry will be recorded before connection.
- The primary human-authored agent context can write; bot-authored and delegated
  non-primary contexts are restricted. This is not verified per-human guest,
  channel or room membership authentication. No group-channel or guest capture
  has been enabled/qualified for this new runtime. Forty bots is not permission
  to ingest every message, user, room, account, file or source.
- Group-channel rollout needs an ingress policy specifying identities, permitted
  sources, consent and memory-space mapping. Reviewed library membership is a
  server sharing grant, not automatic membership in a messaging group.
- Sharing uses reviewed, sanitised current records and approved project/library
  grants. No unrestricted search of all private records is enabled. Corrections,
  retractions, expiry and revocation remove subsequent shared access; historical
  records remain protected. Ambiguous/private changes require clarification.

## Backend, storage, processing and resources

One existing protected native systemd backend is reused; no per-bot database
stack or rootless worker image has been installed by this current phase.

| Interface | Existing Ubuntu-Hermes placement from protected-host evidence |
| --- | --- |
| Restricted memory API | http://127.0.0.1:28080; enhanced-cognee-api.service, DynamicUser |
| Canonical PostgreSQL | Loopback 28434; ecmem_pg; schema 3; cognee_hermes_selected_20261020 |
| Derived Qdrant vectors | Loopback 28535; ecmem_qdrant |
| Derived ArcadeDB graph | Loopback 28536; ecmem_graph |
| Derived Valkey cache | Loopback 28537; ecmem_cache |
| Index worker | enhanced-cognee-index.service, separate DynamicUser; hermes_deploy_v1 |

Runtime code: `/opt/enhanced-cognee-memory`; native store binaries:
`/opt/enhanced-cognee-stores`; protected configuration: `/etc/enhanced-cognee`.
PostgreSQL data is under `/var/lib/enhanced-cognee/postgres`; exact other store
data/cache paths require native unit reconciliation, not guessed volume mounts.
Service backups: `/var/backups/enhanced-cognee`. The report's 20 October
protected-host revision is historical; no new service deployment, unit change,
port change, restart, mount/share, firewall exception or distro restart occurred
during the recent restricted Hermes snapshot/access-check phase.

Memory uses prepared offline BAAI/bge-small-en-v1.5 embeddings (384 dimensions),
encrypted canonical PostgreSQL and derived indexes. No separate hosted extractor
is activated. Selected summaries use Hermes' configured conversation model, so
retrieved memory can leave the host if that profile uses a cloud chat provider.
Vincent's existing Unsloth route is to be reused, without access to Windows model
files, new model downloads or uncoordinated model reloads. The new pilot has no
selected route yet. Older protected tests used local Qwen3.8-27B; an earlier
same-user test also used the approved cloud route. Neither qualifies today's
unconfigured pilot. Actual served context/resource limits must be rechecked.

Repository unit defaults limit API/worker to 1 GiB memory and CPUQuota 200% each,
and backup to 512 MiB/100%. These are configured limits, not measured consumption
or proven fleet capacity. Prior inspected Hermes program trees total about
1.4 GiB plus about 0.2 GiB retained source export per copy; partial copies add
storage. No current full-stack/chat-model/fleet resource budget is established.

## Disable, rollback and recovery

No everyday/default provider switch needs reversing in the current phase. Stop
only a new pilot process if it fails and retain its files/evidence. Leave human
launchers and backend services/keys/stores untouched. Do not rotate global keys,
restore over live databases, reset a checkout or delete partial copies to disable
one pilot. Account locking alone does not revoke a client JWT. Operator-issued
tokens have bounded expiry (1-24 hours); supervised renewal and eventual durable
fleet renewal still require qualification without giving signing power to bots.

Before later provider changes, preserve the selected profile's config/secret
store and plugin version. Disable through that profile's supported provider
selection and restart only that profile after coordination. Reopen the preserved
human setup if needed; do not use a shared/default switch for a single pilot.

Canonical backups use age-encrypted PostgreSQL custom dumps plus authenticated
completion manifests. Daily persistent systemd timer is prepared/previously
qualified with retained generations. Verify manifest authenticity and ciphertext,
then decrypt/restore only into a fresh disposable memory_restore_<unique> DB;
validate encrypted history, scope denial and replayed indexes before any cutover.
New database names and replay pipelines prevent overwriting the live namespace.
Consistent service backups do not back up the full Hermes profile.

Selected current key custody passed Vincent's KeePassXC/download/recovered-package
workflow on 22 October; do not request keys from him or put them into this file.
Unknown historical credential coverage and full new-host recovery remain open.
The new /var/lib/hermes-runtime state requires explicit profile backup/restore
coverage before private use; human-home backups do not automatically include it.
Windows v12 remains paused, v11 remains the scheduled version, and this handoff
requests no Windows operation or new cloud backup upload.

## Evidence and remaining gates

| Evidence | Result and limits |
| --- | --- |
| Current Workspace targeted helper suites | 79 passed, zero failures/skips, no reported warnings; includes fixtures/mocks and real temporary filesystem probes, not installed Hermes/model tests |
| Owner-run native import preflight | Passed all 91 modules/31 namespace paths; ten namespace references omitted from proposed copy |
| Owner-run native protected copy | Published 36797 files, originals preserved; no application launch at preparation stage |
| Owner-run native CLI version | Exit 0 from protected copy, uid 993/gid 985, primary group only, NoNewPrivs=1 and zero CapEff/CapAmb in pre-exec probe |
| Owner-run native selected access probe | Fourteen secret paths denied read/write, nine program files denied write, eleven directories protected, private home; system-Python probe, not every live-agent path/socket |
| Historical 20 October protected-host qualification | 93 installed tests and 41 focused real-store tests; native SDK/browser/provider checks, local invented-data model scenarios, backup/disposable restore and restart evidence at the recorded older revisions |
| New restricted pilot | Not created/connected yet; provider loading, signed scope/authentication, model-driven capture/recall/correction/sharing/denial and renewal pending |

Do not carry earlier tests forward as full qualification of upstream 4d043038,
the new account, an image, a gateway/Desktop route or every bot. New pilot backup,
service/credential freshness, admin-socket and actual tool-process separation,
ingress/guest/group policy, exact-candidate CI/advisories/frontend release checks,
remaining credential review and full fleet capacity/admission remain open.

## Proposed no-write window and drift reconciliation

Continue approved, disjoint Cognee implementation and pilot work. Do not declare
an automatic deployment freeze or treat this handoff as a build/run instruction.
Before a fleet worker image/config deployment or rebase, propose a ten-minute
no-write window on SHARED integration inputs, with start/end UTC relayed and
agreed through Vincent. No calendar time is reserved by this document. During
that window both sides only inspect the agreed code/plugin/namespace/config
metadata pins and compare the exact candidate. No installs, image pulls/builds,
profile/token changes, service restarts, model calls or provider activation.

Compare public source revisions/hashes, account/home/launcher and profile target
paths, service endpoint/schema/index identity, scoped claim NAMES and admission
policies. Compare any secret/config drift locally through approved value-free
operator checks, never by relaying full files, credential fingerprints or values.
If drift is named, preserve both versions and identify the intended owner of the
input. Drift is a reconciliation trigger, not evidence of causation or permission
to roll back, reset, delete or overwrite. Cognee work has Vincent's stated
priority; overlapping Hermes fleet changes must hold while it is resolved.

The review bundle remains review-only until Vincent separately coordinates its
next authorised stage. A candidate image must respect per-trust-boundary OS
isolation and existing scopes, rather than copying root keys or all profiles
into a full worker. Resume writes only for the resolved candidate and scope;
record the resulting revision before any rollout. A passed review/maintenance
window does not itself authorise private-data ingestion or all-bot activation.
