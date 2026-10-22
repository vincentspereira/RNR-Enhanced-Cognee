# Restricted Hermes profile - operator checkpoint

Date: 22 October 2026. This records owner-run Ubuntu-Hermes results, not direct
host observation by the Ubuntu-Workspace implementation session.

## Received approval and scope

The owner approved the restricted account and initial profile. After testing,
the objective remains the main Hermes assistant, all 40-plus bots and all other
Hermes profiles using the same protected Cognee backend, with individual scoped
identities and reviewed sharing. See the live-profile account and fleet runbooks.

## Operator results received

- Preflight identified Ubuntu-Hermes and the human user vincentspereira. The
  account, matching group and /var/lib/hermes-runtime home were absent.
- The human user's Hermes launcher is /home/vincentspereira/.local/bin/hermes.
  Its source/interpreter, permissions and accessibility by the restricted user
  have not yet been qualified.
- The protected Cognee Python executable was reported present at
  /opt/enhanced-cognee-memory/runtime/bin/python. Presence is not runtime testing.
- The owner then ran the guarded account-creation step and reported
  hermes-runtime created, home /var/lib/hermes-runtime, home permissions 0700,
  sole group hermes-runtime and password login locked. No profile was configured.
- Further owner-run metadata resolved both ~/.hermes/hermes-agent and
  ~/agent-workspace/hermes-agent to the same directory under agent-workspace.
  Each reported venv/bin/python present; neither interpreter nor the actual
  restricted Hermes tool process has been executed by these checks.
- A fresh probe reported effective_user hermes-runtime and open denial for the
  five selected protected operator/API/worker/backup/age files, the main Hermes
  .env and both preserved synthetic profiles' .env files. It did not read contents.
- The four probed Docker/Podman/LXD/Incus socket paths were MISSING. This is not
  denial evidence for a socket if it appears later or for other socket paths.
- sudo_policy_explicit_denial was false. This is inconclusive: the earlier
  predicate combined an exit code and exact text from a caller-side listing.
  It does not establish either sudo permission or denial. Obtain a sanitized,
  root-issued policy listing before admitting the restricted runtime.
- The subsequent root-issued listing reported exit 0, an explicit denial for
  hermes-runtime, no allowed-commands section and no authentication requirement;
  no_sudo_permission_confirmed was true. This resolves the earlier inconclusive
  sudo result for the policy at this checkpoint. Exit 0 alone was not permission.
  Actual Hermes process confinement and other elevation paths remain separate.
- The owner reports Hermes Desktop is running for current work. Continue these
  read-only checks without interrupting it; coordinate any later changes to a
  shared runtime, active launch path or model before applying them.
- The next static inspection reported source revision
  4d04303818b61bf3aa09278af48356315515965b and declared project version 0.0.0.
  Treat this as source metadata, not an independently verified release version.
  The published inner launcher references the private store interpreter
  ~/.hermes/tools/python-3.14.7+20260901-linux-x64/bin/python3, resolving to
  python3.14. The discovered tools/facts.json is tool metadata, not by itself
  the dependency generation selected for this source installation.
- Source at this newly reported revision differs from the older d923a5eb487a
  qualification. Read-only upstream review of pm/environments.py and
  hermes_cli/_launchers.py confirms per-install selection metadata. Locate the
  actual committed dependency environment before preparing a protected runtime;
  do not silently substitute the older in-tree venv, copy all private .hermes
  state or run a shared launcher under a new home merely to discover its runtime.
- The owner located the committed dependency environment at
  ~/.hermes/installs/cec419d56f3c6da1/environments/1729494fe7834770ba4afd450a636baa/venv.
  Its pyvenv.cfg reports version_info 3.14.7; its site-packages contains 134
  distribution metadata directories and three .pth startup files. Its Python
  symlink resolves to the previously identified managed Python. Startup-file
  inspection and protected-copy preparation remain pending.

## Project folder recommendation

Retain the owner's existing /home/vincentspereira/Projects directory for projects.
agent-workspace is a naming/layout convention, not a requirement for Hermes or
a memory authorization boundary. Moving projects solely to nest them there can
invalidate bot settings, paths and automation without providing isolation.
No folder move is approved or performed by this recommendation. The restricted
account's profile/workspace lives under /var/lib/hermes-runtime; selected project
access and explicit backup coverage require their own verification. Do not grant
whole-home access merely to reuse the administrator's source/runtime.

Also retain agent-workspace at its existing location rather than moving it
under Projects. It holds the active Hermes source and deployment checkouts.
Hermes' current per-install selection key depends on the resolved source path;
moving the active installation can invalidate dependency selection and embedded
launcher paths. No move or compatibility-symlink creation was requested or
performed. The two existing source locations were already reported to resolve
to one installation; they do not establish duplicate maintained source copies.

## Prepared read-only inspector

integrations/hermes/deployment/inspect_restricted_runtime.py inspects only
installation metadata, the selected .pth startup files and program-tree sizes.
It parses startup code without executing it, reports bounded metadata rather
than raw source/settings, and refuses the wrong distro, root execution or a
changed source revision. It checks source/dependency-selection stability across
inspection. Local syntax/ASCII, help and wrong-distro refusal checks passed.
No Ubuntu-Hermes execution or protected runtime installation is claimed here.

## Next qualification and limitations

The owner executed the read-only inspector successfully: the three startup hooks
were the Hermes editable finder, _virtualenv and distutils precedence hooks.
Reported allocation was 420315136 bytes for Python, 860532736 for the environment
and 231421296 committed-source file bytes; there were 20688 tracked files and
no submodules. No program files were copied and Hermes was not launched.

The new protected-copy helper and runbook are prepared in Workspace. Twenty-two
targeted tests passed (20 new snapshot-security cases plus two existing operator
preservation tests), with zero failures/skips or reported warnings. Tests include
archive traversal, hardlink detachment, symlink confinement, special-file/mode
refusal, non-executing AST relocation, changed startup-file denial, unprivileged
Git export, wrong-user launcher refusal and atomic refusal to replace even an
empty destination. Syntax/ASCII and CLI/wrong-environment checks also passed.
These are local helper tests; no native protected snapshot or full-suite/coverage
result is inferred. Follow HERMES-RESTRICTED-RUNTIME-PREPARATION.md for the next
already approved operator step. Existing accounts, runtime, profiles, stores,
keys and backups were not changed by this Workspace preparation.

Inspect the actual Hermes launcher/runtime without executing user-writable code
as root or granting broad access to the administrator's home. Verify the real
restricted agent process, sudo policy, administrative sockets, service secrets
and peer credential access. Group membership and a locked password alone do not
prove operating-system isolation. Prepare only the initial fresh invented-data
profile, its scoped credential/renewal and narrow existing model settings.

Profile backup coverage, provider/model behavior, fresh-session recall, correction,
sharing and access-denial checks remain pending for this account. No actual bot
or main-profile rollout, private-data admission, runtime reinstallation, restart
or backup run is established by the received account result. Existing service
keys, profiles, bots, history and backup generations remain subject to the
preservation requirements; the paused v12 backup workflow remains separate.

## Native preparation stop and read-only follow-up

The owner fetched delivery commit 1fdfe868 and ran the checked preparation helper
inside Ubuntu-Hermes. It reported a reference outside the selected runtime and
stopped, retaining partial new snapshots and leaving originals unchanged. No
snapshot publication, restricted Hermes launch or profile integration success
has been received. The common diagnostic can come from either symlink relocation
or editable-finder AST rebasing; the exact native reference is still unknown.

The inspector now offers --links-only to distinguish these candidates without
root execution, copying, following external targets or importing Hermes/.pth
code. Outside paths are classified instead of printed. Seven new diagnostic
regressions cover non-execution and target redaction, no directory-link traversal,
dangling links, lexical escape normalization, malformed Git object rejection and
missing-tree refusal. Combined with the earlier snapshot/operator preservation
checks, 29 targeted tests passed under Workspace Python 3.12.3, with zero failures,
zero skips and no reported warnings. Full-suite, coverage and native diagnostic
results are not inferred from this test run. No guard relaxation or change to the
privileged builder was made. Partial native snapshots remain retained.

## Received link diagnosis and corrected import-map preparation

The owner ran the exact inspector from delivery commit 33d64135 and supplied
its completed output. It inspected zero source links, 1047 managed-Python links
and four environment links; external_link_count was zero. The generated finder
__editable___hermes_agent_0_0_0_finder.py contained 122 editable path references.
The first 40 displayed were outside the selected runtime under another operator
home area, on line 9; the editable list was explicitly truncated. Do not infer
classifications of the undisplayed references or the hidden source-directory
name. No files were copied and Hermes was not launched by this diagnosis.

This resolves the earlier ambiguity in favor of editable-path rebasing. The
preparer now reconstructs literal MAPPING/NAMESPACES bindings only when their
declared module suffix matches and a corresponding source module/directory is
present and confined inside the exported commit. All bindings must describe
one source layout. It does not read or copy the old mapped source location,
broaden home-directory access or change existing runtime files. Validation runs
before the large interpreter/dependency copy; the copied finder set and bytes
must subsequently equal preflight originals. Original copied finders remain in
private evidence and failed staging generations remain preserved.

Fourteen additional regressions cover source-mirror reconstruction without code
execution, root modules and nested/empty namespaces, unsupported/missing/relative/
traversing/duplicate/mixed-root mappings, symlink escapes and unrelated home paths.
The combined targeted suite reports 43 passed, zero failures, zero skips and no
reported warnings under Workspace Python 3.12.3. Full-suite/coverage results and
native success are not inferred. Native preparation and all subsequent restricted
runtime/profile/provider/model qualifications remain pending. No existing Hermes
installation, profile, service key, backup, launch path or bot was changed here.

## Native import-name stop; preparation remains incomplete

The owner fetched delivery commit 162beb416 and reported the preparation stop
"An editable import table has an unsupported module name." This message combines
nonliteral, nonstandard, duplicate and overlong-key conditions. The exact native
entry is not yet known. No protected publication or Hermes launch is inferred.
The helper reaches this check after committed-source export but before its large
Python/dependency copy. Failed staging generations remain retained; originals
were reported unchanged. The previous local fixture result did not qualify the
installed import-table layout and the repair remains incomplete.

The normal-user inspector now offers --editable-tables to diagnose all table
entries against Git tree metadata without reading mapped source targets or
executing startup code. It discloses module names only when backed by committed
source paths; unknown keys and original home roots remain redacted. It reports
name/shape/path problems, root counts, unbound home-path counts and explicit
truncation instead of silently showing only successful entries. The privileged
builder and its name/copy guards remain unchanged pending this native evidence.

Ten additional diagnostic test cases cover committed nonstandard/flat filenames,
duplicate keys, nonliteral expressions, hidden keys/targets, unrelated private
paths, malformed names, complete issue counts/truncation, linked/missing finders
and non-execution. The combined targeted suite reports 53 passed, zero failures,
zero skips and no reported warnings under Workspace Python 3.12.3. This is not a
full-suite/coverage or native diagnostic/preparation success receipt. Runtime,
profile, model/provider and fleet qualification remain pending.

## Received full table audit and namespace correction

The owner supplied a completed --editable-tables receipt from delivery commit
ed0a530d: 122 entries/paths checked, one source root, no unbound home-path
constants, 17 reported problems and no truncation. All reported problems were in
NAMESPACES. Seven corresponded to committed plugin directories containing
hyphens; ten had no corresponding committed path (two also had nonstandard
names). Unknown names and old mapped source locations stayed redacted. No
MAPPING binding problem was reported. No files were copied or Hermes launched.

The corrected preparer accepts safe hyphenated namespace labels backed by the
selected commit and omits namespace references absent from that copy. It never
omits missing required module bindings. Even omitted namespace targets must
match declared suffixes, normalized paths and the single source root. It records
counts, preserves the original copied finder in restricted evidence, and never
modifies original source/profile files. The omitted references are not proof
that any original folder is unnecessary; no deletion is performed or implied.

A normal-user --preflight checks the same binding logic/catalog directly from
Git metadata with no staging files, copies, root identity or application startup.
It checks startup hashes, selected generation and source/finder stability. The
actual privileged preparation additionally checks the copied source paths and
uses the same catalog/exclusions. Root Git still drops identity/groups; normal
operator Git no longer attempts a privileged supplementary-group change.

Twelve added regression cases cover namespace retention and count reporting,
no-copy/copied validation parity, original-file preservation, name/traversal/
mixed-root denial even for omitted namespaces, strict missing-module denial,
uncommitted working-tree preservation, normal-user Git behavior, no-write
preflight and source-metadata/finder/startup mutation refusal. Combined targeted
results: 65 passed, zero failures, zero skips and no reported warnings under
Workspace Python 3.12.3. Full-suite/coverage results and native corrected
preflight/preparation success remain unclaimed. Protected runtime, initial
profile/provider/model tests and fleet rollout remain pending.

## Native corrected import preflight passed

The owner ran the checked helper from delivery commit
5a0ec3da21d3c802269d770ffeeb4e0cc460127b with --preflight inside Ubuntu-Hermes.
The supplied receipt reports complete=true, read_only=true and
import_preflight_passed=true against Hermes source
4d04303818b61bf3aa09278af48356315515965b. The generated finder validated 91 module
bindings, retained 21 namespace paths and omitted ten namespace paths/entries
absent from the selected committed layout. These totals cover the earlier 122
path references. No files were copied and Hermes was not launched.

This resolves the import-table compatibility blocker at the no-copy preflight
stage. The receipt explicitly reports snapshot_prepared=false and
runtime_qualified=false. It does not prove successful protected copying, final
link confinement, program startup, restricted profile/provider/model behavior,
backup coverage or fleet deployment. Continue the approved protected preparation
using this exact helper with --apply through the checked sudo wrapper; it repeats
validation against the actual committed source copy and retains all original
installations, profiles and previous staging generations. No code change or
additional local test result is implied by recording the owner-run receipt.

## Native protected program copy prepared

The owner ran the checked helper from delivery commit 5a0ec3da with --apply and
supplied complete=true and snapshot_prepared=true. The published snapshot is
/opt/hermes-runtime/releases/4d04303818b6-1729494fe783, with launcher bin/hermes
and Hermes source revision 4d04303818b61bf3aa09278af48356315515965b. The receipt
reports 36797 program files and originals_preserved=true. Import-map counts match
the earlier preflight: 91 module bindings, 21 retained namespace paths and ten
omitted namespace paths/entries. This is owner-reported native preparation
evidence; Workspace cannot independently inspect the isolated installation.

The receipt explicitly states runtime_qualified=false, hermes_launched=false,
profile_configured=false and memory_connected=false. Do not rerun --apply over
this published destination, switch existing launchers or remove earlier staging
generations. Next run only the protected launcher's version command under the
hermes-runtime identity with no-new-privileges, reporting identity/capability
metadata and its exit status. Application code must never run as root. The
launcher clears inherited settings and pins HOME/HERMES_HOME to the restricted
account; startup may create its own fresh state under /var/lib/hermes-runtime.

A successful version check will establish only basic startup from this copy,
not complete process/credential isolation or provider/model/memory behavior.
Protected-file/write denial checks, the fresh profile and scoped credential,
explicit backup/recovery coverage, Desktop/gateway paths and fleet qualification
remain pending. Existing human-owned Desktop profiles/bots remain unchanged.

## Restricted native version startup passed

The owner supplied a successful protected-launcher version probe. The pre-exec
identity was uid 993 (hermes-runtime), gid 985 and only group 985. CapEff/CapAmb
were zero and NoNewPrivs was 1. The launcher returned exit 0, reporting
Hermes vgit.4d04303, upstream 4d043038, Python 3.14.7, OpenAI SDK 2.24.0 and
install directory /opt/hermes-runtime/releases/4d04303818b6-1729494fe783/repo.
It displayed build/version metadata 2026.9.24 and install method unknown. Do not
interpret these as an independently verified release tag or advisory clearance;
external-update handling remains a separate check. The startup has now occurred;
the earlier preparation receipt's hermes_launched=false describes its own stage.

This proves basic CLI startup from the prepared copy under the selected identity
and inherited privilege restrictions. It does not prove full application-process,
Desktop/gateway, peer-profile, provider/model, memory or fleet qualification.
No connected profile/scoped token or private-data activation is established by
the version output. Retain the published copy and previous partial generations.

The next prepared helper, check_restricted_access.py, runs only as the restricted
account with no-new-privileges and zero effective/ambient capabilities. It probes
14 selected protected service/recovery and administrator-profile paths for read
and write opening, nine program files for write opening, eleven root-owned
program directories for ownership/mode/effective write denial and home privacy.
It reads no secret/program data and never writes/truncates/creates a target.
Missing paths, special types and inconclusive errors cannot pass as denials.
Self-process status is read as metadata. This is a system-Python probe, not proof
of every operation of a live Hermes process, all keys or all 40+ bots. Fourteen
new regressions plus earlier targeted suites report 79 passed, zero failures,
zero skips and no reported warnings under Workspace Python 3.12.3. Native access
results, full-suite/coverage and the remaining qualification are still pending.

## Native selected file-access checks passed

The owner executed the checked access helper from delivery commit 12896a8e and
supplied complete=true and selected_access_checks_passed=true under uid 993
(hermes-runtime). Only the primary group was present; no-new-privileges and zero
effective/ambient capabilities passed, as did private home permissions. All 14
selected service/recovery/administrator-profile paths denied both read and write
opening. All nine selected protected program files denied write opening, and
all eleven tested program directories passed root ownership/mode/effective
write checks. The helper read/wrote no secret or program data. Its explicit
runtime_qualified=false and memory_connection_tested=false remain applicable.

This resolves the selected native file-access probe, not every file, socket,
live agent tool process or bot trust boundary. The next approved step is a fresh
profile named enhanced-cognee-pilot under
/var/lib/hermes-runtime/.hermes/profiles/enhanced-cognee-pilot. Use the protected
launcher as hermes-runtime with no-new-privileges and umask 077, through Hermes'
profile create command with --no-alias --no-skills and without clone options.
Refuse any existing target, including a symlink; do not replace or delete it.
This creates the initial profile structure only. No default-profile switch,
provider/token installation, model call, gateway or memory write is established.
The owner has not yet reported profile creation. Existing human profiles/bots,
protected services, keys and backup/staging generations remain preserved.

After creation, prepare the selected provider and a fresh ordinary scoped
credential in this profile. No operator/API/worker/recovery key may enter it.
Token expiry/renewal, narrow existing model configuration, actual provider/model
and cross-scope behavior, recovery coverage and fleet onboarding remain pending.
This is a documentation update; it adds no new local test or full-suite result.

## Fleet review coordination and owner priority

Vincent relayed a review-only Hermes Phase A bundle notice and then directly
instructed this implementation to continue, taking priority if shared work
conflicts. No direct agent message, bundle access or bundle execution occurred.
The sanitised six-part coordination handoff is
docs/runbooks/HERMES-FLEET-COORDINATION-HANDOFF-2026-10-22.md, marker
EC-HERMES-COORD-20261022T154452Z, with integration code anchor 12896a8e.
It pins the public plugin files and native snapshot, states exact profile and
capture limits, separates current/historical tests and proposes a ten-minute
shared-input no-write window before a fleet image/config deployment or rebase.
No window is scheduled and no fleet activation is implied. Disjoint authorised
Cognee/pilot work continues; conflicting fleet writes should hold for
reconciliation through Vincent, preserving both versions and original data.

## Native pilot profile created; managed tools remain incomplete

The owner ran the guarded profile create command and supplied successful
creation at /var/lib/hermes-runtime/.hermes/profiles/enhanced-cognee-pilot.
The command reported no bundled skill seeding with --no-skills and no API keys
in the fresh profile. There was no clone, default switch, provider/token install,
model call or gateway activation in this step. The printed shortcut examples do
not establish an alias; --no-alias was requested. Continue using the protected
launcher under the restricted account rather than a human-shell shortcut.

Before success output, Hermes reported install out of sync for ffmpeg, node,
npm and ripgrep, with the external rnr-operator steward requiring an artifact
rebuild. The prepared snapshot intentionally contains only the copied Python
entry in its managed tool facts; this is an outstanding tool-packaging issue,
not a completed full-runtime qualification. Do not suppress the warning, change
the steward to permit agent writes, fake tool versions, or invoke the original
human installation's updater while it is in use. Preserve the new profile and
published/partial copies.

At the selected public Hermes source commit, pm/lock.json pins ffmpeg 9.0.1,
node 26.7.0, npm 12.0.2 and ripgrep 15.2.0. These are required source metadata,
not proof of available local binaries or advisory clearance. A normal-operator
--managed-tools inspector now reads just these four original tool records and
their entry/binary/link/allocation metadata against that committed lock and the
protected snapshot facts. It never executes a tool, downloads, installs, changes
facts, reads profile credentials or follows a root entry outside the tool store.
Outside targets are redacted; recorded version matches are not execution proof.
Original tool selection/source stability is checked across the inspection.

Seven new regression cases cover non-execution/non-disclosure, absent records,
version and binary drift, outside/linked root rejection, malformed records and
changing metadata. Combined targeted helper suites report 86 passed, zero
failures, zero skips and no reported warnings under Workspace Python 3.12.3.
Native tool inventory/correction and new pilot provider/model/memory tests remain
pending; no full-suite/coverage or full-runtime success is inferred. This delta
supplements, rather than rewrites, the pinned fleet handoff marker. Its review
bundle remains untouched and conflicting work still yields to Cognee priority.

## Native four-tool inventory received; separate artifact repair prepared

Vincent supplied complete=true/read_only=true from the managed-tools inspector
at delivery revision 36b6f72f. All four original program entries are directories,
with present/executable binaries, recorded versions matching the selected
4d043038 Hermes lock, and no links outside the original store. ffmpeg 9.0.1 has
458809344 allocated bytes/zero links; node 26.7.0 has 237559808 bytes/two links;
npm 12.0.2 has 19251200 bytes/eleven links; ripgrep 15.2.0 has 5828608 bytes/zero
links. Total allocation is 721448960 bytes, about 688 MiB. Protected records are
absent for each. No binary was executed and runtime_qualified remains false.

The published preparation helper now supports --apply --with-managed-tools to
build a separate root-owned generation at
/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1. It retains the old
protected release and the already-created pilot, recopies committed source and
the selected Python/dependency trees, and admits only these four tool payloads.
It verifies complete local source facts against exact committed target/artifact
identity, checks realized source fingerprints, confines and fingerprints the
copy, rechecks source bytes/metadata, and records genuine protected fingerprints
in schema 1 facts. The reviewed program PATH is reconstructed; arbitrary human
environment values are not copied. Only stdlib helper code runs as root; no
application/tool binary, updater, package installer or model is executed.

The 28 new security/consistency regressions cover changed identities/versions,
missing fingerprints/schema, file/link hash ordering, escaping or swapped paths,
special/privileged files, copy-time drift, private-file exclusion and refusing
existing payload slots. Combined helper suites: 114 passed, zero failed, zero
skipped, no reported warnings, Workspace Python 3.12.3. Separate unprivileged
compatibility checks used the exact public upstream pm/lock.py reader and the
pm/store.py digest function at 4d043038 against synthetic files: four reader/
identity/env cases and four digest cases passed. These source compatibility
checks did not execute real tool binaries or test a live Hermes process. The
runbook links their primary sources and records the reproduction scope.

The repair requires no downloads beyond the approved public helper delivery and
does not alter the running human Hermes, profile configuration, fleet review
bundle, protected Cognee services/credentials, or Windows backups. It requires
approximately 2.5 GiB additional guest space; the guest-free-space guard remains
4 GiB and host Windows storage is not inferred. The root runner must hash the
exact helper stdin bytes before compilation, eliminating a mutable helper-file
gap. Native publication/tool execution/confinement and warning clearance remain
pending owner output. Existing local recorded fingerprints are consistency
evidence, not fresh publisher authentication or advisory clearance. No complete
runtime/private-data admission or all-bot activation is claimed. This delta
supplements the existing pinned fleet handoff; no shared maintenance window has
been scheduled and no fleet input has been deployed or rebased.

## Native tools1 generation prepared successfully

Vincent ran the pinned bbfa0eea94664d46afa381107b244df59c632465 helper and
reported complete=true/snapshot_prepared=true at
/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1, with 43574 program
files and originals_preserved=true. All four tool source/copy payload checks
passed at the selected versions. The editable import receipt remains 91 module
bindings, 21 retained namespace paths, ten omitted namespace paths/entries.
tool_binaries_executed, hermes_launched, runtime_qualified, profile_configured
and memory_connected are still false in this preparation receipt. The pilot
already exists in its separate restricted home; this builder configures no
provider/model route. The new generation has not yet passed a native version,
tool execution, access or actual memory test. Continue those checks before
private-data admission. No existing profile, bot, backend or review bundle was
reported changed by this step.

The owner also asked to consolidate the GitHub branches into main. Both older
deployment tips are already ancestors of the delivery branch. See
BRANCH-CONSOLIDATION-AND-RELEASE-REVIEW-2026-10-22.md for the remote ancestry,
required security checks and the separate pull-request/merge disposition.

## Native tools1 startup passed

Vincent subsequently reported successful --version execution from the new
tools1 launcher. Effective identity was uid 993/gid 985 hermes-runtime with only
its primary group, CapEff/CapAmb zero and NoNewPrivs=1. The application identified
vgit.4d04303/upstream 4d043038, install directory under the new tools1/repo,
Python 3.14.7 and OpenAI SDK 2.24.0; startup exit was zero. Install method was
again unknown, retained for the separate external-update-policy check. This
qualifies the reported startup only. Four tool executables, new-generation
selected access checks, actual provider/model connection and all-bot admission
remain pending. Do not repeat preparation, recreate the pilot or restart WSL.

PR 85 now consolidates delivery to main. On candidate
68beb6803d6ffad4310be2cfe865a8b84dd0b8d6, required unit CI and canonical-browser
passed; default-stack and both frontend checks failed their security gates.
The additional memory/full-runtime workflows also failed audit/image security
steps. The broader legacy pipeline has separate unit/coverage, auth type-check
and audit failures; these are not cleared by the required unit lane's success.
Its downstream administrative/job skips are not qualification-test successes.
The PR is draft, mergeable without source conflicts, and blocked by checks.
No branch protection, source branch or installed runtime was changed by this
status review. These live results supersede the earlier queued-run status.

## Native copied-tool execution passed; tools1 access probe prepared

The owner reported version execution exit 0 for all four protected tools under
the previously guided restricted identity/empty-environment command: ffmpeg
n9.0.1-11-ge47273f4d9-20260831, Node v26.7.0, npm 12.0.2 and ripgrep 15.2.0
(e89fff89ac). FFmpeg and ripgrep also emitted ordinary build/CPU-feature metadata.
These are actual tool executions, not recorded facts versions. They do not
qualify codec operations, application package-manager recognition, browser/model
routes, the Cognee connection or fleet capacity. No model/gateway/installer was
started by this probe. Historical preparation flags remain preparation receipts.

The selected-access helper now accepts exactly --tools-generation to select the
fixed tools1 release. Its original no-argument release selection is preserved;
no arbitrary path or extra flag is accepted. The new mode repeats the 14 secret
read/write probes and selected original program checks against the new release,
adds its package facts and four resolved tool targets, checks every selected
logical/target ancestor and checks regular-file ownership, hardlink count,
privilege/write bits and effective write ACL. npm's program link must resolve
inside the protected release; outside targets are not opened or printed. It
still never reads/writes secret or program-file contents and uses no create,
truncate or append flags. Only self-process status is read. Selected probes are
not a complete live-tool, socket, peer-profile or OS security qualification.

The expanded focused helper suites pass 130 cases, zero failures/skips and no
reported warnings in the separate Workspace Python 3.12.3 certificate-corrected
test runtime. Sixteen new regressions cover fixed/idempotent generation
selection, npm link/facts/ancestor coverage, outside/broken/missing tools,
ownership/modes/hardlink/ACL failures, false-summary prevention and CLI argument
rejection. No full-suite/coverage or native access pass is claimed. Run the
published helper under hermes-runtime/no-new-privileges with checksum verification
before compilation; sudo only selects this non-admin identity. Keep the pilot,
original/new program generations, protected service and owner keys unchanged.

## Native tools1 selected access passed; pilot connector prepared

The owner's next native result, fetched at ea783b618f530c6dce7ca1d2190c29f17d050ebf,
reports complete=true and selected_access_checks_passed=true for tools1 under
hermes-runtime uid 993. Only the primary group was present, with no-new-privileges,
zero effective/ambient capabilities and a private home. All 14 selected secret
paths denied both read and write; all 14 selected program paths denied write
and passed protected regular-file metadata checks. Every selected ancestor
passed. No secret/program contents were read or written. This receipt still
explicitly reports runtime_qualified=false and memory_connection_tested=false;
it does not establish broader live-tool, socket or peer-profile isolation.

The next prepared step is install_pilot_provider.py. It stages only the three
hash-pinned version 0.1.0 provider files under root-owned /opt/hermes-runtime/
providers/enhanced-cognee-0.1.0-29cb9fa3400a. It drops all supplementary groups,
uid/gid to hermes-runtime and enables no-new-privileges before touching the pilot
or importing Hermes. The child links the existing pilot's plugin directory to
that artifact and checks the actual pinned Hermes MemoryProvider loader and
eight schemas. Application code never runs as root. No model/API request,
token provisioning, active provider selection or existing profile/configuration
rewrite belongs to this step. Native loader success has not yet been received.

The focused helper suites now pass 156 tests, zero failures/skips and no reported
warnings in the separate Workspace test runtime. The 26 new cases cover payload
drift, preserved conflicting artifacts, symlinks/hardlinks/permissions, atomic
non-overwrite publication, process privilege selection and bounded sanitized
receipts. Child execution is mocked in these tests; native Hermes loading and
Ubuntu-Hermes installation remain separate evidence. See the pilot installation
runbook for scope, atomic installation, limitations and rollback. A protected
artifact does not make the agent-owned profile/configuration immutable or prove
isolation between all bots sharing an operating-system account.

## Native pilot provider installation and registration passed

The owner ran the pinned four-file archive at
ab0626632a5f4c271ec6c9c3cac33f099a7d5dee and returned a complete native receipt.
The protected artifact /opt/hermes-runtime/providers/
enhanced-cognee-0.1.0-29cb9fa3400a was created, and the existing restricted pilot
received its plugin link. Version 0.1.0 loaded through the actual Hermes loader
as hermes-runtime; native_loader_passed=true and exactly the eight reviewed tools
were registered. This is actual native registration evidence, superseding the
installation-pending checkpoint above. The Workspace session did not directly
access Ubuntu-Hermes or inspect private host logs.

The receipt explicitly keeps provider_selected, credentials_provisioned,
memory_connected, model_called and runtime_qualified false. Native registration
does not prove authenticated recall, automatic selected capture, a model route,
full process isolation or fleet readiness. The next guided check inventories
only the pilot's credential/settings file presence and protected metadata, and
checks unauthenticated local status denial before any credential is issued.
No existing secret is printed, renewed or replaced by that read-only check.

## Native initial-access preflight passed; issuance prepared

The owner returned complete=true from the next read-only check, effective user
hermes-runtime. The pilot .env is an existing regular file, owned by that
account, mode 0600. Neither enhanced_cognee.json nor config.yaml exists. The
unauthenticated local status request returned HTTP 401. File contents were not
read and no credential was issued by that preflight. This confirms that initial
credential preparation can preserve the existing environment without treating
it as an empty or disposable file.

provision_pilot_access.py now prepares initial 24-hour ordinary access for tenant
qualification, project hermes_pilot, subject hermes_pilot_runtime and agent
hermes_pilot, role api_client and capture_policy selected. Root stdlib reads the
two protected signing configurations through no-follow descriptors and checks
that their persistent keys match; it changes neither file/key. It produces the
same HS256 claim contract as memory_admin.issue_token. Only ordinary tokens and
public claims cross a private process pipe after dropping uid/groups to the
restricted account with no-new-privileges and a clean environment. No application
or dotenv parser is imported as root; no token is placed in command arguments,
the inherited child process environment, logs, source, reports or memories.
The ordinary credential is deliberately stored only in the selected pilot .env.

The child checks the existing pilot/env privacy, refuses an already configured
pilot or existing token assignment, parses without loading ambient settings,
and verifies unauthenticated/expired/altered token HTTP 401 plus the correct
authenticated schema-3, encrypted, empty pilot scope. Status checks can update
operational request counters; no memory record is created or changed. It keeps
an exact private .env-before-cognee-pilot-* copy, creates/fsyncs a private stage,
checks the original file descriptor/name/content for intervening changes, and
atomically replaces only the selected pilot .env with preserved original bytes
plus the ordinary token. Failures retain prepared files. The advisory lock and
checks coordinate ordinary writers; they are not isolation from a malicious
process sharing the same account. All other profiles/services/keys are outside
this change. No model, memory-provider selection or gateway is started.

The expanded focused Workspace suites pass 208 cases, zero failures/skips and
no reported warnings. Fifty-two new cases cover PyJWT compatibility/signatures,
fixed destination, negative status controls, scope/freshness refusal, private
backup/readback, unchanged values including multiline settings, detected
concurrent changes, permissions/links, privilege selection and sanitized output.
API and subprocess behavior use mocks; this is not native issuance evidence.
The guided operator command must verify the exact published helper hash before
execution in no-site/isolated system Python. Await the native receipt before
claiming credential provisioning or authenticated access. The credential expires
after 24 hours; initial issuance is not an unattended renewal mechanism, and
provider/model activation, actual memory tests, profile recovery and fleet
qualification remain pending.

## Native initial pilot credential issued; provider selection prepared

The owner returned a successful initial provisioning receipt at
44a093fc5eb712670bf7464777d840831d47d564. Effective user was hermes-runtime,
credential_installed=true. The exact preserved original environment basename
is .env-before-cognee-pilot-414dafc6ffa24cd58486986bd7091c4e. The signed ordinary
identity is tenant qualification, project hermes_pilot, subject
hermes_pilot_runtime, role api_client, capture_policy selected. Its expiry is
2026-10-23T18:23:15+00:00. Authenticated API status passed; unauthenticated,
expired and altered credentials were denied. No credential value is recorded.
The receipt explicitly keeps provider_selected, model_called,
memory_records_written and runtime_qualified false. This is native initial
issuance evidence, not unattended renewal or model/fleet/private-data admission.

configure_pilot_provider.py prepares the next restricted-only step. It publishes
the previously absent enhanced_cognee.json and minimal memory-only config.yaml
mode 0600 through no-replace atomic publication. Matching interrupted settings
can resume; differing owner/model edits or unsafe files are preserved/refused.
No original configuration file is overwritten and .env remains byte-identical.
The settings select the fixed local API, selected capture and server-reviewed
sharing. They grant no new shared-library membership or cross-project access.

Before native imports the helper requires the correct restricted identity,
no-new-privileges/zero capabilities, only its own group, protected tools1 Python,
private profile and hash-verified protected provider/link. It then uses the
actual pinned Hermes memory loader and native secret-scope API, binding only the
ordinary pilot credential from the native profile parser. No fallback class,
guard bypass or signing/recovery-key access is introduced. It initializes the
actual provider and calls enhanced_status plus enhanced_recall for an invented
query in the empty scope. Only the status/scope and empty-result booleans leave
the process; no raw record, secret or full configuration is printed. Recall can
use the existing local embedding service; no chat-model route/call, memory-record
write, gateway or bot activation belongs to this step. Native configuration
loading can create Hermes' normal local last-known-good settings backup.

The focused Workspace suites pass 234 tests, zero failures/skips and no reported
warnings. Twenty-six new cases cover fixed non-secret settings, private atomic
publication/idempotence, conflicting/concurrent file preservation and exact
status/empty-recall contracts. Provider calls use fixtures; actual native provider
selection and credential-bound status/recall remain pending the owner command.
Empty recall is not proof of saved-record retrieval or automatic model capture.
Settings may already be published if a later check fails; retain them, report
the fixed failure stage, and do not auto-delete/overwrite the profile.

## Native provider selection and authenticated reads passed

The owner returned a successful host receipt at
81f20cf6d81f8b127d7c5c4c1c0fd7b269b317c7. Effective identity was hermes-runtime
in the existing enhanced-cognee-pilot. Both previously absent settings files
were created. provider_selected, native_provider_initialized,
authenticated_provider_status_passed, empty_scope_recall_passed,
credential_file_unchanged, selected capture and reviewed-sharing settings passed.
No new group/library grant is implied by enabling reviewed-sharing searches.
The receipt explicitly keeps chat_model_called, memory_records_written and
runtime_qualified false. This is native connector/credential-bound read evidence,
not proof of saved memory, a chat-model route, automatic capture or full rollout.

The next prepared read-only operator helper is inspect_local_model_routes.py.
It runs as the human owner with protected Python, reads three fixed config.yaml
files, and emits only sanitized loopback model declarations. .env files, external
secret stores and raw chats are not opened; models/network are not called and
no file is changed. Configs may contain inline key values encountered by the
YAML parser in memory; those values, credential-variable names, extra-header
values, source provider names and unrelated config are never output. Unsafe or
credential-bearing URLs and credential-shaped model strings are omitted.
Missing/unsafe/invalid sources receive only fixed reason labels. The output is
bounded and cannot establish the current served model/context or route access.
See the pilot runbook for exact source scope and limitations. The existing
Unsloth route must be reconciled rather than copied from old test evidence.

The focused helper suites now pass 262 tests, zero failures/skips and no reported
warnings, including 28 new route/privacy regressions with invented configurations.
This does not establish native model-route inventory or network/model success.
No main merge, service/model restart, bot activation, backup run, key renewal or
private-data admission was performed by this Workspace preparation.
