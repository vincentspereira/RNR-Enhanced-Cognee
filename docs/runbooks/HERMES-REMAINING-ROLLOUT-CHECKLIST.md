# Remaining Hermes memory rollout work

30 October 2026 PER-PROFILE PLUGIN DISCOVERY FIXED: memory plugins resolve
per profile (profile isolation scans the profile's own plugins directory),
so role profiles did not see the gateway-home plugin install. The provider
plugin is now staged into ALL 42 profile directories (39 staged, 3 already
covered), and discovery verified for five sampled roles across role
families. Owner-side effect: every role's Memory Provider dropdown now
includes Enhanced Cognee (refresh the settings page; a role session open
since before staging may need close/reopen). Stage 8 can proceed; no
further restarts required for this.

30 October 2026 STAGE 8 READY: all 40 role tokens issued and API-verified
(30-day expiry, ~Nov 29; the batch command re-run is the renewal), the
gateway restarted with the provider selected, and the per-role Memory
Provider dropdowns now include Enhanced Cognee. Two batch-issuer defects
were found and fixed on the first run: root-owned receipts (now chowned to
the gateway identity) and hyphenated role names refused by the backend's
canonical space-ID rule (roles address underscored space ids; default
unaffected). Hyphenated names mapping to canonical ids must stay in the
tests. The owner approved: 30-day rotation + automated renewal as the end
state (the unattended-renewal design is a fleet-review decision), remote
endpoint and MCP phase-two work after Stage 8, and providing the
memory-wiring addendum to the fleet activation bot. Owner decisions still
parked: ArcadeDB operator credential reset (folded into the stack
rotation), historical exposed-key disposition (scan closed F22), fleet
admission enablement and main merge at the final review.

30 October 2026 MILESTONE: ENHANCED COGNEE IS LIVE AS THE DEFAULT
ASSISTANT'S EXTENDED MEMORY. Verified in the owner's Desktop against the
fleet gateway: the provider appears in and is selected by the Memory
Provider dropdown for the default profile; an explicit remember stored
record 28f557e8 (the first write attempt was refused by a policy gate and
the adjusted retry passed — guardrails enforcing on live writes); and a
fresh session received automatic recall injection and answered the test
phrase exactly. Token for the default profile: issuer-signed, expires
2026-11-06 (weekly renewal cadence until the fleet lifecycle policy
lands). Remaining for the full goal: wire the 42 role profiles in Stage 8
batches (per-role tokens via the provisioner's --profile flag, provider
selection per role, the memory-wiring addendum), the remote-endpoint and
MCP phase-two work, served-capability and maximum-context verification,
the credential rotation execution, and the fleet-switch review. The owner
is holding Stage 8 until memory wiring is confirmed per role.

30 October 2026 CANARY PROFILES FOUND: the two enhanced-cognee-test profiles
in the gateway home are not dummies — both are issuer-provisioned (Oct 25:
.env with a scoped token, .env-before-issuer backups, prepared/published
receipts, renewal lock), with empty memories/sessions and the standard
persona. RECOMMENDATION to the owner: keep both as the memory canaries
(first wired, first verified); they are not part of the 40 roles. This also
means the issuer flow has already provisioned real gateway profiles once —
the activation path is renewal/re-issue for the canaries plus issuance for
the roles, not a new provisioner build. Renewal flow inspection is next.

30 October 2026 ACTIVATION DESIGN (gateway fleet): the token publication
targets are confirmed — the gateway home carries ~/.hermes/.env (0600,
vincentspereira) for the app-level default profile, and every role profile
has its own .env overlay (exactly what agent.secret_scope reads, per-profile
private memory spaces via per-profile tokens). The gateway config
(~/.hermes/config.yaml) has no memory section yet; activation adds
memory.provider: enhanced_cognee and requires a gateway restart at an
owner-chosen window. The retained pilot provisioner (342 lines, phased:
identity, profile preflight, environment backup/publication/readback,
issuer-signed expiring tokens) is hardcoded to the old pilot home and
profile, so a gateway-profile variant is the immediate build: same audited
flow, new targets (home .env for default; profiles/<role>/.env per role),
identity claims tenant=hermes_gateway with project_id per profile. The
plugin is staged and discoverable; the API is on the provider default
origin. Everything else (served-capability verification, max-context,
remote endpoints, role batches) follows activation.

30 October 2026 ARCHITECTURE RECONCILED: the owner's Hermes Agent Desktop
manages the fleet through an SSH gateway to THIS host (127.0.0.1:2222 as
vincentspereira; Hermes from ~/agent-workspace/hermes-agent, upstream
checkout bf0203a794). The fleet's 42 role profiles live in
/home/vincentspereira/.hermes/profiles/. The Desktop's provider dropdown
(Built-in only, Byterover, Retaindb) reflects that gateway installation,
which had no Enhanced Cognee provider. The provider plugin is now STAGED at
/home/vincentspereira/.hermes/plugins/memory/enhanced_cognee/ (plugin.yaml
c23230082be650ae142c4e3d8e30350ea5f3d18af5b879996328caf59d4dca48,
__init__.py fcc7be3d7659671f14006f685c8e5419554075a1e35ca4dde687d7ae46400061,
client.py 8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64),
which activates nothing until memory.provider is set and the gateway
restarts. The memory API already listens on 127.0.0.1:28080, the provider's
default origin. The provider serves EIGHT tools under the official
memory-provider contract (distinct from the ~120-tool MCP server).
Remaining activation steps: issue one scoped ENHANCED_COGNEE_ACCESS_TOKEN
for the default profile (issuer machinery is deliberately disabled for
fleet admission, so the single-profile issuance path is being prepared),
set memory.provider: enhanced_cognee in the gateway config, restart the
gateway at an owner-chosen window, select the provider for default in the
Desktop, verify served tools and capture/recall, then roll out to the roles
in batches with per-profile tokens. The clarified 8-tool provider versus
the ~120-tool MCP server distinction is recorded here.

29 October 2026 FINDING: the live main profile's memory provider is ALREADY
enhanced_cognee (read-only inspection under the actual restricted identity;
config hash 0f46e8c6e945b27878d6e93f23acd256172dd2afb6db08671ecb540237cbc289,
4 MCP definitions). No controlled switch is needed for the main profile;
the remaining main-profile gates are served capability and maximum-context
capture. The live remote HTTP endpoints (context7, deepwiki) remain deferred
behind the owner external-endpoint gate; the owner has since AUTHORIZED
their qualification, which will be prepared on the binding machinery.
Separately, a redacted git-history credential scan found NO structural
provider keys; audit item F22's candidates are accounted for as upstream
defaults, templates and invented fixtures, with three fingerprints recorded
for an optional owner glance
(`2026-10-29-git-history-key-scan.txt`). The actionable exposure remains
the stack credentials in the agent-readable .env (staged rotation) and the
provider-side model/Telegram keys. See
`2026-10-29-main-memory-selection.json`.

29 October 2026 COMPLETE: the native MCP binding gate is CLOSED. The v6
operator ran both stages under the actual restricted main identity. The
catalogue read the live main profile config (4 definitions: fetch,
filesystem, context7, deepwiki), resolved the stdio definitions through the
release's native managed launchers, and bound them: Fetch via managed uvx
(1 tool, 2 private-address denials) and Filesystem via managed npx (14
tools). The live profile holds remote HTTP endpoints context7 and deepwiki,
which are accounted and explicitly DEFERRED: connecting to external
endpoints with profile credentials needs the owner's qualification gate; the
receipts carry names only, never url or header values. The fetch-public
stage then completed the authorized public example.com retrieval in raw and
default modes through the native binding (converted-Markdown structural
check qualified). Evidence:
`operator-evidence/native-mcp-binding-ggu1psf5`; sanitized record
`2026-10-29-native-mcp-binding-preparation.json` (v1-v5 retained attempts
documented). Still open: full main tools/context and current served
capability (including the unverified maximum-context capture), production
launcher bindings for live fleet processes, admitted credential
renewal/reload, fresh main-state reconciliation with backup/rollback
membership, the remote-endpoint owner gate, and one concrete fleet-switch
review. Admission stays disabled; no fleet activation or main merge.

29 October 2026 PREPARED: the native MCP binding qualification group awaits
the owner's sudo terminal. The first attempt (v1) stopped itself in the
operator's verification phase with zero effects: it tried to read a helper
from the owner's 0750 home, which the capability-less operator unit cannot
traverse; it is retained. The corrected v2 freezes every staged source,
including the pinned installer, into the artifact at launch and the worker
loads nothing from the worktree. It runs the pinned driver as the actual
restricted main identity; the identity reads only its own Hermes config,
resolves every preserved definition through the release's native launcher
resolution, and launches each server exactly as production would (networked
posture recorded honestly). A second unit, if a Fetch definition exists,
completes the authorized public example.com raw and default-mode retrieval.
Config values never cross the identity boundary; receipts carry counts,
flags and error kinds only. 54 focused tests pass; the offline resolution
probe confirmed managed npx/uvx/node/uv selection. Receipt:
`2026-10-29-native-mcp-binding-preparation.json`. After this gate: full main
tools/context and current served capability, production launcher bindings
for live fleet processes, admitted credential renewal/reload, then the fresh
main-state and fleet-switch review.

29 October 2026 COMPLETE: the native managed-launch packaging gate is CLOSED.
The owner ran the corrected reconciliation: every payload member verified
against the sealed archive, 233 directory modes corrected to their archived
0755 values, and the restricted-identity proof PASSED under the actual UID
992/GID 984 (zero capabilities, private network namespace): resident PM
runtime qualified, native uvx/npx launcher selection qualified, python and uv
digests verified. The managed uv 0.12.3 and Python 3.14.7 binaries run and
the pm-runtime marker is readable by restricted identities. Retained: the v1
partial publication (umask directory-mode defect), the v2 verification
refusal (over-strict checks, zero effects), the completed v3 receipt.
Sanitized record: `2026-10-29-managed-runtime-install-reconciliation.json`.
Next gate: actual native MCP-server binding for all six preserved main
definitions (Fetch native binding plus remote acceptance; the candidate-level
HTML extraction qualification is already recorded), full main tools/context
and current served capability, production launcher bindings, admitted
credential renewal/reload, then the fresh main-state and fleet-switch review.
No service, profile, credential, policy or bot changed; admission stays
disabled.

29 October 2026 (installation history, retained): the owner ran the
protected PM installation. It
published all 5,005 members plus the marker and merged facts correctly, then
failed only its restricted-identity proof because the operator umask left the
new directories at 0700 and the UID-992 proof child could not read the
pm-runtime marker. The first reconciliation attempt refused in its read-only
verification stage (it compared the merged facts against the staged copy and
walked the whole store) and applied nothing; it is retained as evidence. The
corrected helper verifies the payload member-by-member, checks the merged
facts bytes separately, walks only the payload subtrees, corrects only the
payload directory modes to their archived 0755 values, and reruns the
identical proof with captured output into a v3 receipt (47 focused tests,
fixture reproductions of both refusal causes; read-only dry runs passed). It
awaits the owner's sudo terminal. Receipt:
`2026-10-29-managed-runtime-install-reconciliation.json`.

29 October 2026: the Fetch candidate's default HTML-to-Markdown extraction is
now QUALIFIED at the ordinary-owner candidate level. The retained failure was
root-caused to a stale page-copy expectation (example.com's body text was
reworded; the Node extractor also legitimately moves the heading into article
metadata), not a server defect. The probe now checks conversion structurally.
The full probe passed again on the retained frozen build: initialize, one-tool
catalogue, two private-address refusals, raw retrieval and converted-Markdown
extraction. 38 focused tests and native 3.14.7 compilation pass. Receipt:
`2026-10-29-fetch-html-extraction-qualified.json`. Native Hermes Fetch
binding, remote acceptance and fleet use remain open. The protected managed PM
runtime installation is unchanged and still awaits the owner's sudo terminal;
its read-only preflight was re-verified PASS on 29 October 2026 (all five
helper hashes, sealed archive SHA256, four protected pins and inactive
restricted accounts rechecked).

28 October native managed-launch support is PREPARED, not installed. A NEW
ordinary-owner supported-PM build, exact frozen Fetch lock, sealed 464,097,280-byte
public payload and 5,005-member disposable restore passed. The relocated resident
PM and native uvx resolver passed with no network and zero capabilities. Fetch
initialize/catalogue, private-address denials and raw public retrieval passed;
HTML extraction and actual native server binding remain unqualified. OSV found
zero findings for 50 exact public dependencies in these NEW environments only.
Thirty-seven focused security tests and native compilation pass.

The [single guarded PM installation and restricted-identity group](HERMES-MANAGED-MCP-RUNTIME.md)
is ready. Its actual read-only public preflight passed; execution awaits the
owner's sudo terminal. It adds missing pinned components and retains original
facts, interpreters, code and settings. No service or bot is started, and active
restricted bots cause refusal. The owner confirms concurrent fleet work is
preparation only. Current inspection found no processes under 43 restricted
accounts; older roster labels are not treated as current acceptance. All prior
Filesystem/REA/Java/Ghidra/model/memory passes and failures remain preserved.
Full native MCP/main tools/context, production dispatch/binding, admitted renewal,
deferred bindings, fresh main state and final switch review remain open.
No main merge or fleet activation is claimed. See
2026-10-28-managed-mcp-runtime-preparation.json for sanitized evidence.

## Earlier checkpoints (preserved)

28 October protected REA continuation PASSED at
main-local-mcp-rea-finish-esoknsn8 under the actual restricted main identity.
Initialize and the full 207-tool catalogue passed with the bounded 10 MiB
reader. Filesystem's 14-tool catalogue/read/write/outside-root-denial pass and
both protected public package copies were reused. No Filesystem, Java/Ghidra,
model, memory or earlier completed native test was replayed. The unit stopped;
credentials, profiles, policies and launchers were unchanged. This closes the
local Filesystem/REA component checks, not their full native Hermes launch.

Read-only inspection found a separate native packaging blocker: the protected
release lacks pm-runtime/pm-runtime.json and its independent PM environment;
its Python fact contains only entry='.' without the lock identity/digest, and
uv is absent from the managed store. Hermes resolves bare npx/uvx through PM,
so shell PATH checks alone do not establish native launcher readiness. The
unchanged public PM is being used in a NEW isolated ordinary-owner build to
prepare pinned tools, an independent manager and locked Fetch dependencies.
No running protected runtime is changed by that build. Native launch, Fetch/
remote acceptance, full main tools/context, production dispatch, admitted renewal,
deferred profiles, fresh final main state and switch review remain open.
All fleet admission policies remain disabled. See the sanitized
2026-10-28-main-local-mcp-components-pass.json receipt.

## Earlier checkpoints (preserved)

28 October REA finish stopped before REA at public_code_pins,
main-local-mcp-rea-finish-evjjlpz3. All five hashes/owners/permissions match; the
qualification helper incorrectly applied its 16 MiB script cap to the
123,655,872-byte Node executable. The [exact-size Node continuation](HERMES-MAIN-LOCAL-MCP-QUALIFICATION.md)
changes only that fixed binary's size bound and preserves every integrity guard.
The exact corrected preflight passes all five real artifacts; 52 focused tests
and native compilation pass. Protected V2 REA-only execution is pending in the
owner's terminal. No Filesystem/package/Ghidra/model pass was replayed; all prior
failures and disabled policies remain retained. Main tools/context/native launch,
Fetch/remotes, production dispatch, admitted renewal and final fleet review remain
open. No fleet approval is claimed.

## Earlier checkpoints (preserved)

28 October protected Filesystem MCP and both public package readback checks
PASSED at main-local-mcp-hi_qvtkz. REA's group remained failed. A local isolated
diagnostic identifies the qualification reader's 2 MiB cap: REA initializes and
then returns a roughly 3.16 MB full-schema catalogue of 207 tools. The bounded
10 MiB reader from its exact pinned SDK PASSED locally; no schemas or Hermes
guards changed. The [REA-only finish](HERMES-MAIN-LOCAL-MCP-QUALIFICATION.md)
reuses Filesystem/copy/main recovery passes and retains the old failure. Sixty
focused tests and native/public-pin checks pass. Actual main-UID protected REA
execution is pending in the owner's sudo terminal; all admission stays closed.
Full tools/context/native launch, Fetch/remotes, production dispatch, admitted
renewal, deferred bindings, fresh final main state and fleet review remain open.

## Earlier checkpoints (preserved)

28 October OWNER-RUN MAIN CANDIDATE AND CONFIGURED RECOVERY PASSED at
main-rea-reviewed-lsamkulo, helper
fc389e21e8f13dd9feb54e35a760ccf482fc0bcf6d79c76ffa13bf3e47bd1d51.
The current settings/OAuth and Telegram home record were preserved in a NEW
inactive main candidate. All six MCP definitions survived, nine SQLite databases
recovered and unresolved filesystem references reached zero. Two ordinary
fixed-scope credentials and two signed encrypted generations were created.
Current source fingerprints matched at completion. Source profiles, earlier
candidates, launchers and backup registry were preserved; all admission policies
remain disabled. The completed Java/Ghidra dependency proof was reused without
replay. No model, platform adapter, external platform connection or send ran.

This pass reused the qualified operational snapshot, so it does not establish
fresh main operational state at a future switch, full MCP/server/tool behavior,
served context, native production dispatch, admitted renewal or fleet approval.
Do not rerun either main preparation or the completed Java/Ghidra proof.
See 2026-10-28-main-telegram-candidate-pass.json and the next
[offline local MCP component group](HERMES-MAIN-LOCAL-MCP-QUALIFICATION.md).

## Earlier preparation (preserved)

28 October latest protected main preparation stopped before credentials or
generations at main-rea-reviewed-pq0i9j79. The additional setting is a new
Telegram enabled/home-channel record. Preserve it as current configuration data;
Telegram activation, messages and fleet routing are not qualified. The
[grouped inactive copy and encrypted recovery action](HERMES-REA-PROGRAM-DEPENDENCIES.md)
now permits only that bounded public shape, retains strict controls for all
other changes and reuses the completed Java/Ghidra proof without replay.
Forty-eight focused tests and native Python/public-schema checks pass. The NEW
protected action is pending; source/old candidates and all admission gates stay
preserved. Full MCP/context, production dispatch, admitted renewal, deferred
bindings, final live main state and fleet switch review remain open.

## Earlier checkpoints (preserved)

28 October protected Java/Ghidra dependency execution is now QUALIFIED at
rea-owner-receipt-finish-zy8t6r38. Owner-only receipt recovery, unchanged timestamps
and trusted PID-1 proof passed; copies/readback/execution were reused without a
replay. Keep this pass. Full REA MCP/tool acceptance is still separate.
Current approvals.timeout is 600 seconds (previously 900); one further change
remains redacted. The prepared [guarded main candidate and encrypted recovery job](HERMES-REA-PROGRAM-DEPENDENCIES.md)
preserves that current limit only under a narrow inactive-preparation policy.
All other unreviewed changes stop before issuance; no fleet policy is admitted.
Twenty-seven focused tests/native compilation pass; protected execution pending.
Main candidate recovery, full MCP/context, production routing, admitted renewal,
deferred bindings, final live-state reconciliation and fleet review remain open.

## Earlier checkpoints (preserved)


28 October dependency proof service has trusted PID-1 start/success/stop
metadata and the exact driver hash, but parent evidence collection failed with
PermissionError at rea-settings-programs-x1l5absn. The parent lacks DAC override;
the 0700 receipt directory belongs to the restricted UID. Keep that boundary.
The prepared [owner-read finish](HERMES-REA-PROGRAM-DEPENDENCIES.md) validates the
retained receipt as its owner and reuses copies/readback/execution without a
replay. It refreshes safe settings metadata, accepts no settings and activates
no profile. Twenty-two focused tests/native compilation pass; private receipt
recovery remains pending. approvals.timeout and one redacted change still need
disposition. Broader candidate/tool/production/renewal/final-switch gates remain.

## Earlier checkpoints (preserved)


28 October V3 configuration comparison at rea-main-programs-1oj9htt6
STOPPED on a meaningful change in other_settings. Core model/memory/gateway/MCP
sections matched. Zero credentials, generations or program staging; all prior
state and disabled policies preserved. Do not bypass this review gate.
The new [grouped settings review and independent REA dependency proof](HERMES-REA-PROGRAM-DEPENDENCIES.md)
reports only schema-approved field metadata and qualifies pinned Ghidra/Java
without accepting settings or activating profiles. Twenty-nine focused tests
and native compilation pass; protected execution remains pending. Candidate
recovery, full tool/context acceptance, production dispatch, admitted renewal,
deferred bindings and final fleet switch review remain open.

## Earlier checkpoints (preserved)


28 October latest inspection at rea-continuation-inspection-wxp7kgjd
locates the V2 failure in current-settings capture, after model binding passed.
No program staging, credential or generation occurred. Both failures are retained.
The new [grouped REA capture reconciliation](HERMES-REA-PROGRAM-DEPENDENCIES.md)
requires authenticated typed configuration equality before staging/issuance;
formatting alone may differ, changed settings stop for review. If equal, the
same command finishes dependency execution and NEW candidate encrypted recovery.
Thirty-five source tests and native compilation pass. Protected execution and
all broader fleet acceptance gates remain pending; no fleet approval is claimed.

## Earlier checkpoints (preserved)


28 October confirmed REA diagnosis: all protected identity checks pass;
source .env and auth.json drifted while config.yaml matched. The zero-effect
failure and previous recovery passes are retained. The guarded
[current-settings REA continuation](HERMES-REA-PROGRAM-DEPENDENCIES.md) now
captures fresh encrypted settings and preserves current OAuth in a NEW inactive
copy, reusing the qualified nine-database snapshot. Forty relevant tests and
native compilation pass; protected staging/execution/recovery remain pending
until the owner runs continue-rea-programs. No completed tests are replayed.
Production dispatch, full MCP/context acceptance, admitted renewal, deferred
bindings and final switch review remain open; no fleet approval is claimed.

## Earlier checkpoints (preserved)

28 October latest REA batch result: STOPPED before credentials/staging, at
rea-main-programs-s784o2c_. Original profiles, REA/Ghidra/Java installations,
candidates and disabled policies are preserved. The broad identity label also
covers source-fingerprint comparison; the failing predicate is not confirmed.
The next action is the [read-only retained REA preflight inspection](HERMES-REA-PROGRAM-DEPENDENCIES.md),
not a batch replay. Thirty-one relevant diagnostic/controller tests and native
compilation/negative control pass. Protected inspection remains pending; the
nine-database live-state recovery and prior program readback passes stay valid.


28 October latest owner-run PASS: live main state and configured encrypted
recovery at main-live-gk1v63p6, including nine SQLite databases, current settings/
OAuth and six MCP definitions. The current-source operational refresh gate is
closed; no previous operational state was reused. All admission policies remain
disabled and no source/candidate promotion/registry change occurred.

The owner identifies Ghidra and Java as REA plugin dependencies. Actual local
metadata observes rea 0.2.0 and pinned rea-agents@6.7.0. Preserve the plugin,
command, arguments, timeout and existing versions. Both public distributions
have source-side snapshot/disposable-restore/readback passes. The grouped
[protected REA dependency and candidate recovery job](HERMES-REA-PROGRAM-DEPENDENCIES.md)
is implemented and passes 68 relevant checks; its protected execution is pending.
The earlier settings-only and RAM-only checkpoints below retain their scopes.
Production dispatch, full MCP/context coverage, admitted renewal, deferred
bindings and final switch review remain open. No fleet approval is claimed.


28 October Ubuntu-Hermes: current main configuration/recovery PASSED at
main-current-j0zy5ttp with all six MCP definitions preserved. The retained
40-profile qualification and 41-profile scheduled backup passes remain valid
for their recorded scopes. No completed native/model/memory test was replayed.

The changing telemetry items are now verified display/log outputs, not guard
configuration. V4 preserves durable configuration and database checks; native
RAM-only capture passes for 5,915 files and nine SQLite databases. The grouped
[live main refresh and encrypted recovery](HERMES-MAIN-LIVE-STATE-REFRESH.md) is
implemented and source-tested (46 relevant tests), with protected execution
pending. The prior current-settings pass reused older operational state and
remains distinct from this new capture/restore qualification.

Production dispatch/callback/outbox integration, actual launch binding,
Ghidra/Java and full current MCP/tool/context coverage, admitted unattended
operation, deferred bindings and final mapping/switch review are still open.
All admission policies remain disabled. The four relevant delivery CI workflows
still pass at exact revision 21abf485; broader coverage/full-runtime workflows
remain failed. No main merge or whole-fleet activation is claimed.

## Historical checkpoints (retain their dates and scopes)

27 October Ubuntu-Hermes update: the grouped inactive main implementation and
all 40 named credential/reload/recovery qualifications PASSED. Main provider
selection, eight-database recovery, own/peer/OS/index checks and trusted
scheduling proof passed. The current ZAI model capture/recall, native human
answer, canonical/derived recovery and custody passes remain retained.
See [current candidate evidence](HERMES-CONSOLIDATED-CANDIDATE-BATCHES.md).
The dated unresolved checkpoints below are historical; do not replay them.
The owner-run [daily backup coverage for all 41 qualified candidates](HERMES-QUALIFIED-FLEET-DAILY-BACKUPS.md)
and [kernel-authenticated transport under two restricted UIDs](HERMES-ISOLATED-GATEWAY-TRANSPORT.md)
have now PASSED. Protected
[native DM text authorization and clarification handling](HERMES-ISOLATED-NATIVE-TEXT-INGRESS.md)
also PASSED under two restricted UIDs. Protected
[native adapter delivery and persistent crash/replay refusal](HERMES-ISOLATED-DELIVERY-RECOVERY.md)
subsequently PASSED all four phases at isolated-delivery-807r2x1g. The next
prepared grouped operation reconciles
[current main settings into a new inactive copy and verifies recovery](HERMES-CURRENT-MAIN-RECONCILIATION.md).
Its protected execution is pending; 83 source/security tests and a read-only
six-definition preparation against installed helpers passed.
Production bot/CLI dispatch and explicit launch binding,
main tools/MCP and served-context coverage, unattended admitted-fleet operation,
the two deferred existing bindings and final mapping/switch review remain open.
No whole-fleet activation or main merge is approved by these component passes.

Latest main-source metadata observes six MCP definitions, while the retained
candidate qualified four. Preserve the current six and unrelated/OAuth settings;
reconcile them into a new inactive candidate before main tool qualification or
final switch. No source or candidate configuration was changed by the inspection.
Strict live-source capture currently refuses a changing telemetry file. Its
writer/purpose remain unresolved and its guard is unchanged. The prepared
settings reconciliation reuses the older candidate's operational state; full
current live-state refresh remains a separate admission gate.

Latest source checkpoint: the restricted text-only service now has a clean
locked dependency audit, matching real BGE vectors and disposable encrypted
recovery evidence. The full legacy lock retains three filelock findings.
See [the source report](../reports/audits/2026-10-19-hermes-security/TEXT-EMBEDDING-SECURITY-2026-10-24.md)
and [the consolidated host continuation](HERMES-SYSTEM-WIDE-LAUNCH-CONTINUATION.md).
Installed renewal/recovery, native completion and real fleet admission remain
open. Do not replay the completed version-4 record. Older checkpoints below
retain their dates and do not override this update.

24 October continuation: the owner authorized proceeding in two consolidated
work batches. See [the current qualification report](../reports/audits/2026-10-19-hermes-security/CONSOLIDATED-LAUNCH-QUALIFICATION-2026-10-24.md)
and [the two-batch procedure](HERMES-CONSOLIDATED-LAUNCH-QUALIFICATION.md).
The 62-check native synthetic Windows pass is verified. New clarification
restart/same-turn gaps are repaired and source-tested; installed candidate
qualification and the other operational/fleet gates remain open. The dated
checkpoint below is preserved and does not override the new evidence.

Current installed state checkpoint: the owner's f63cdd52 read-only inspection
of test 5d0e9a49bdf544359ae6deff confirms canonical version 4, a retracted
record, all four history versions, no pending clarification and peer HTTP 404.
The actual human answer passed on the preceding continuation. Preserve this
completed state and do not replay correction/retraction or resume that record.
The earlier native turn's overall completion predicate failed; its exact cause
and the driver's native_followup_qualified gate remain open. Verified canonical
effects and a fully completed native-turn receipt are distinct evidence.
See [the current installed checkpoint](../reports/audits/2026-10-19-hermes-security/CANONICAL-EFFECTS-AND-SECURITY-2026-10-24.md).

The subsequent [dependency audit follow-up](../reports/audits/2026-10-19-hermes-security/DEPENDENCY-LAUNCH-BLOCKER-2026-10-24.md)
confirms the required CI pass but a still-failing restricted FastEmbed/Pillow
security gate. Source/conversation passes do not close that launch blocker.

Reviewed in Workspace on 23 October 2026 against repository source and the
owner-relayed installed results. This is not direct access to Ubuntu-Hermes.

## What is already working

The protected backend and restricted pilot are installed. Owner-run native
evidence establishes selected capture, fresh-session recall, clear versioned
correction and fresh-session recall of the corrected version. The second pilot
OpenAI account is independently enrolled, and the local API accepted the ordinary
memory credential at its last check. Settings/defaults and prior evidence were
preserved. These completed gates do not need replaying to reconstruct evidence.

Historical uncertainty diagnostic (superseded by the passes below): the owner
returned complete=false/native_agent_turn with category
ambiguous_change_not_preserved_for_clarification at helper revision
ef39013eab7aba9df2c1413e39f53943ddaaa0f8. Checked settings/credentials were
unchanged and memory_writes_may_have_occurred=false. That report does not say
which condition failed: missing clarification, no preceding read, an editing
tool attempt, a blocked write or unexpected pending state. It did not complete
the post-turn canonical/receipt comparison. That run remained failed/pending
until the later, verified native-prefetch pass.

Subsequent owner-run diagnostics at 5b2538ad verified post-turn preservation,
correct pending target, a completed native turn/question, no editing tool and
zero write attempts. Only the explicit-read-tool predicate failed. Pinned native
Hermes also recalls automatically before tools. The updated qualification helper
requires actual matching current-record retrieval and successful model-request
delivery before accepting this alternative, preserving all other guards. The
historical report alone did not establish delivery; the later 0768a43e pass
established it for the single-turn uncertainty case.

## How much remains

There are five shared readiness groups, followed by the actual fleet rollout.
These are six work groups, not six tests or a promise of six commands. Some
mechanisms still need implementation, and a failed installed check may need a
repair and a bounded repeat. Unit-test counts measure source checks; they are
not a countdown to deployment. Group independent checks into safe operator runs
when they use the same trust boundary; do not ask the owner to replay passes.

| Group | Required result | Current status |
|---|---|---|
| 1. Conversation safeguards | Uncertainty asks a question without editing; a later genuine human answer permits only the confirmed change; sensitive details/credentials are rejected; correction/retraction retain appropriate history without claiming sensitive history was erased | Earlier capture/correction/recall/privacy passes retained; current owner-run candidate question and human-answer gate pass; read-only canonical observation verifies correction/retraction, four versions and cleared pending state. Overall native-turn completion failure remains unresolved; do not replay the completed record |
| 2. Access and reviewed sharing | The intended runtime cannot reach privileged/peer secrets; private spaces deny other callers; only approved shared summaries are visible and revocation/current-version rules hold | Current installed signed-scope negative/reviewer-sharing/revocation checks passed; the completed record returns peer 404. Actual peer-secret, OS and everyday fleet boundaries remain open |
| 3. Credential operation | Protected fixed-scope renewal, expiry/refusal controls, safe atomic publication and interrupted-renewal recovery work without giving agents signing authority | Owner-run manual pilot renewal and API refusal controls pass; installed interruption recovery and unattended/fleet lifecycle remain open |
| 4. Recoverable state | Explicit encrypted restricted-profile/workspace/receipt coverage, consistent database generation and disposable restoration prove recovery without overwriting live state | Owner key custody, inventory and manual encrypted profile restore pass; df79510b now verifies the upgraded protected runner, signed 60-file/205571-byte ciphertext and enabled/active daily timer with next run. Future scheduled firing, current database generation, full-fleet/SQLite homes, Windows/remote collection and fresh-machine rebuild remain open; ea6f2438 source-side inventory passes for six database/two profile pairs; native Windows dual-family collection remains pending |
| 5. Runtime and release checks | Relevant backend/provider dependencies and required checks pass, failures/unready indexes are reported honestly, and deployed artifacts match the admitted source | Known dependency/release issues and final candidate checks remain; a unit pass alone does not close these |
| 6. Fleet inventory and staged admission | Enumerate actual main/bot/other profiles, map distinct scopes/credentials and real launch identities, back up configurations, then qualify batches with own-scope/other-scope/shared checks and a preserved disable/recovery path | Everyday main/bot profiles remain unchanged; no whole-fleet activation claimed |

The installed daily profile-backup/timer gate passed at owner-run df79510b.
The no-export collection inventory also passed at ea6f2438: six completed
encrypted database pairs and two profile pairs, both recent families present
and ciphertext hashes verified. No keys, export, backup or upload were used.
Do not repeat these passed checks. The next backup step is native Windows
qualification of the updated files; source inventory is not Windows collection,
remote recovery or a v12 resume. Conversation follow-up, peer/fleet sharing,
unattended credentials and release checks remain open. Preserve everyday
profiles/bots and current model defaults.

Group 5's relevant runtime/backend checks must be distinguished from the full
repository release: separate frontend issues remain tracked for release/main
merge, not relabeled as failed Hermes conversations. Reuse older finite evidence
only where its exact code, identity and scope still apply. Do not repeat distro
restarts, installation, cloud-vault recovery or all prior model tests routinely.

Group 6 must inventory the actual count and launch mechanisms; the earlier
41-bots-plus-controller example is not an installed inventory. Per-profile
checks can run in batches. Shared component evidence can be reused after
verifying the same protected artifact and behavior, while each profile's actual
credential/scope and launch boundary still need admission. One maintained
backend remains the design; there is no need for one backend per bot.

Private credential-review coverage remains a separate owner checkpoint. Preserve
the already completed KeePassXC/key-package recovery evidence; do not restart
that process or claim unknown historical credentials were revoked.

## Historical operator evidence - superseded by current results

Latest owner-run update: clarify_followup passed at
0768a43e0d3e429327b23e108ab5ad4eafe56e30. Verified native prefetch delivery
preceded enhanced_clarify; the record/history/receipts/profile were preserved,
with no edit/write attempt. This closes the single-turn uncertainty gate and
supersedes the diagnostic retry below. It does not qualify a later human answer
or pending-state durability. The owner subsequently returned all eleven API
privacy cases passed at 37cc5d9bd8a25b233fca7f0754d33f035d40269b, with expected
422/409 refusals, unchanged canonical/history/receipts/profile, no OAuth store
read, no chat-model call and no memory write. Preserve both passes.

Owner-run native privacy also passed at
79264eebd2a3a5d99822b45580f496a56b6bc2b1: one GPT-6.1-Sol request using the
explicit secondary account, no tool/edit/write attempt, no full sensitive canary
in the reply and unchanged canonical/history/receipts/settings/credentials.
This is one finite synthetic case; do not replay it or infer universal detection.

Owner-run manual credential renewal passed at
8fb6fca95cf5480830d748134da93b785645820a. New expiry is
2026-10-24T09:15:06+00:00; API acceptance, refusal controls, retained previous
environment and unchanged settings/OAuth passed without a model or memory write.
interrupted_attempts_reconciled=0 does not establish installed crash recovery.

Owner-run recovery inventory passed at
61c272a767f1383acccd9760d782da8c8e127752: 60 files/205571 bytes, no detected
database/sidecar or problematic entries, all required private files/receipts
and protected provider/tool flags passed. No source data was copied then.

Owner-run manual profile recovery now passes at
ca2682c6af3d0c40855e795a1dca9c778629184e: signed ciphertext/decryption,
60 recovered files/205571 bytes, private permissions/provider binding/scoped API
access, with live source and the failed destination preserved. No repeat of
that restore is needed. Owner-run d7c7880c installed the separate daily job
files, but its first run exited 1 and timer enable did not complete. Owner-run 3bd4bf8f verified public artifacts/protections and found the retained
restricted_snapshot failure with no backup created. Owner-run 058b71da then observed PermissionError/errno 1 before a child
result. Next qualify the scheduled external identity-launch candidate with the
updated transient probe before any installed service replacement.
It performs encryption-only snapshots with no model/API, memory write or
recovery-identity read. Keep the pilot idle for its first run. See
HERMES-PILOT-RECOVERY.md. Windows collection, current canonical database
recovery and fresh-machine program rebuild remain separate; no fleet activation.

Latest owner-run 56c0d439: the temporary launcher returned 127 at setresuid;
the root parent has effective CAP_SETGID but lacks CAP_SETUID. No snapshot or
backup completed and installed files/timer remain untouched. The next candidate
retains CAP_SETUID in the root service's ambient set, with the same bounding
set, then explicitly clears ambient/inheritable capabilities for the non-root
reader. Other selected restrictions and the reader's zero-effective/ambient
guard remain. Qualify this finite RAM-only snapshot first. Then prepare the
guarded update of exact known installed artifacts, run an actual encrypted
backup successfully and verify the timer. Do not repeat the initial installer.

### Historical clarification diagnostic, superseded by the passes above

The clarification helper now returns only bounded diagnostic flags/counts and
known tool names for a completed turn missing a clarification condition. No
record IDs, prompts, replies, arguments or credentials are printed. If that
completed turn fails the behavior check, authoritative post-turn reads still
compare canonical content/history, counts, receipts and checked profile state
before reporting whether preservation verified. A failed comparison never
becomes a preservation pass. The original behavior and write guard stay enforced.

One deliberate new run of clarify_followup is needed to confirm matching native
automatic-recall delivery before clarification, which earlier diagnostics did
not observe. This is not a repeat of capture, correction or corrected recall.
Use the explicit secondary account, existing scopes/receipts and the new pinned
hash-verified helper. It may consume existing subscription quota. Stop on an
observed 429; do not rotate accounts automatically or reset statuses.

This single-turn diagnostic does not establish durable clarification across
restarts or a later human-answer turn. Fix the observed condition first, then
complete the remaining group 1 cases and the other groups above.

Latest backup update, 23 October: owner-run 47b20e4d passes the corrected
restricted snapshot (exit 0, snapshot discarded in RAM, no installed change).
Do not repeat it. The next step is the pinned exact-artifact guarded upgrade:
preserve old runner/units, publish the reviewed protected runner and corrected
service, verify one actual signed encrypted backup and then enable/verify the
daily timer. This step is prepared, not owner-run complete. Failed/partial
updates preserve evidence and require review before any retry. Other readiness
and fleet gates above remain open.

Latest owner update at ab8c990b: corrected service replacement succeeded and
originals were preserved. The combined real backup qualification stage failed;
no timer-enable command completed. Do not infer which subcheck failed or whether
ciphertext exists. Next inspect the exact upgraded runner/service and retained
invocation read-only; preserve old/new artifacts, manual recovery and passing
snapshot evidence. Do not rerun the updater. Installed encrypted-job/timer and
all separate collection/release/fleet gates remain pending.

Retained-inspection follow-up: owner-run 6b4453bf stopped in service_state with
no writes and no retained report. Revised read-only diagnostics separate read,
parse and missing-current-ID failures, preserving sanitized partial state. A
latest-journal-ID fallback is diagnostic only and explicitly cannot qualify the
upgraded run. Keep the installed upgrade and previous evidence intact; no
updater rerun, timer activation or repeated model/recovery test is requested.

Latest result: owner-run 3b456aeb retained inspection succeeds with all artifact/
policy checks, success/0/inactive state and one completed 60-file/205571-byte
report. Timer remains inactive/disabled. This fallback report alone does not
qualify a fresh upgraded run or authenticate its files. Next use the pinned
main_resume continuation to bind trusted root/exact-runner/post-publication
journal metadata, verify ciphertext/signature/counts/signed time, then enable
and verify the daily timer. No manual backup, unit replacement, model or restore
replay. A persistent timer may perform a scheduled catch-up. Other gates remain.
