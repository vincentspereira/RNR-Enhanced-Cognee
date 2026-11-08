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

## Received local declarations; owner selected Z.ai for tests only

The owner ran the pinned local inventory at
de771c38d7838c699c865ca0611a7cb78b237505. Main config read successfully: custom_1
and provider_2 both declare http://localhost:8888/v1 with the expected seven
local model names, without configured context sizes. No request/model call or
file change occurred. Neither row establishes the active default or current
served model. The two earlier test config files returned the fixed
unreadable_unsafe_or_invalid label; no reason was invented and no permissions,
old profiles or credentials were changed to read them.

The owner subsequently authorized GLM-5.3-Flash from the existing Z.ai GLM Pro
Coding Plan for tests/checks, with local chat reserved for offline/cloud-failure
use. Their latest explicit clarification is to preserve the default models
setup in Hermes. It supersedes their prior conditional default-change request.
Use test-run overrides only; leave main/default and existing bot/profile model
settings intact. This delivery has changed no model defaults or called a chat
model. The already configured local embedding/index service remains separate
from the chat-model choice. No global provider policy, private-data admission
or hosted extraction is inferred.

The next prepared inspector mode reads only main config and reports sanitized
Z.ai declaration metadata, including distinct Coding Plan/general API endpoint
kinds. No .env, credential values, pool/secret stores, model calls or network
requests are involved. Builtin provider names without an explicit URL remain
unresolved; no quota/entitlement/access claim is made. The official Z.ai tool
guide lists Hermes support and the Coding Plan Chat Completions endpoint, and
the model guide documents glm-5.3-flash. See the runbook for direct sources and
the guarded operator scope. General pay-as-you-go routing is not the requested
plan route and must not be substituted during testing.

Focused Workspace suites pass 282 tests, zero failures/skips and no reported
warnings, including 20 new main-only Z.ai privacy/endpoint regressions. Native
Z.ai inventory and GLM test/capture evidence remain pending. Current defaults,
live Desktop work, bots, service keys/stores and backup generations are preserved.

## Received Z.ai inspection; bounded SDK test prepared

Native receipt at 681247e71554e80c91df5de1de7c168ceff69908 reports the current
main default GLM-5.3-Flash, builtin Z.ai selected, no explicit endpoint and no
additional Z.ai routes. No network/model request, secret-store read or file
change occurred. The false model-match flag was a case-sensitive comparison
bug; it is corrected without editing any model defaults. An implicit builtin
route is still not proof of Coding Plan routing, account entitlement or quota.

check_zai_pilot_connectivity.py prepares one authorized invented-data request
using the existing ordinary Z.ai client key, selected by the human owner from
fixed protected-permission main files. Only that selected key crosses stdin to
hermes-runtime. The SDK request runs under that restricted identity, existing
protected tools1 Python, no-new-privileges and zero capabilities. No application
code runs as root. Main/profile model settings and secret files are not written.
The helper bypasses native auto-detection/auth migration and fixes the exact
Coding Plan Chat Completions URL, glm-5.3-flash, low reasoning effort, enabled
thinking and 512 maximum completion tokens. TLS stays verified; proxy discovery,
redirects, automatic retries and general/local fallbacks are disabled. See the
pilot runbook for source scope, official references and output limits.

No reply text, reasoning or credentials are printed. A successful receipt proves
only the bounded restricted SDK request and acknowledgement; it does not start
Hermes chat, qualify context, exercise automatic memory capture or admit private
data. Runtime/capture qualification and memory_records_written remain false.
Native SDK evidence is pending. The focused fixture suites pass 325 tests,
zero failures/skips and no reported warnings (42 new connectivity checks and
one model-name case regression); this is not a full release/coverage result.
Existing Desktop/bot work, model defaults, service keys/stores, backups and the
separate fleet review bundle remain untouched by this preparation.

## Native SDK attempt did not pass; cause unresolved

Owner receipt at 01617e5e182090d23a0eb1b54bd531a07db54528: restricted check
failed at coding_plan_request with no HTTP status, no defaults changed. That
phase includes dependency/client setup, transport and response validation; no
successful network/model request or key rejection is established by the terse
receipt. The initial helper suppressed the failure category too aggressively.

The revised helper adds only reconstructed fixed diagnostic categories, bounded
usage, completion presence, allowlisted finish reason and content/reasoning
presence booleans. It never prints raw errors, reply/reasoning text, credential
values or arbitrary exception names. It keeps the existing exact Coding Plan
route, synthetic prompt, model, 512-token limit and at-most-one SDK request with
no retries/fallbacks. Truncation remains a failure, not a passed model check.
No credential/default/profile file is written by the diagnostic. See the pilot
runbook for interpretation and limits. Focused fixture suites pass 343 tests,
zero failures/skips and no reported warnings, including 18 new regressions.
Native failure diagnosis, successful GLM access and Hermes capture/fresh-session
recall qualification remain pending. No new account/recovery action or rollout
is inferred from this failure.

## Restricted SDK diagnostic reports DNS failure

Owner receipt at d301ad52f03ea0717c3d315f1967eceb7a203957 reports dns_error at
coding_plan_request, no HTTP status and no SDK completion or token counts.
No model defaults, credential files or memory records were written. The
restricted process reached the request stage and its exception chain contains
a DNS resolution failure. This is not evidence of a rejected key or exhausted
model allowance. Successful model access and memory qualification remain open.

The next read-only step compares api.z.ai and a public control hostname under
vincentspereira and hermes-runtime using the same protected Python, clean
environment and no-new-privileges. It reports fixed resolver-file readability
flags and DNS categories, never file contents, resolved IPs or raw errors. It
uses no credential, model/HTTP call, Git fetch or configuration change. Each
account has a 20-second bound. See docs/runbooks/HERMES-ZAI-DNS-CHECK.md.
Host comparison remains pending; do not change resolver, WSL, firewall or
identity settings, restart services, or retry the cloud request without first
reconciling that comparison. Existing 343 passing fixture tests do not establish
native DNS/model success; no additional full-suite claim is made here.

## Owner relayed normal-account DNS results and OpenAI fallback request

Two relayed Hermes reports show EAI_AGAIN for api.z.ai under vincentspereira
while GitHub resolved; the second also resolved api.openai.com and chatgpt.com.
Resolver-file readability passed under that account. Restricted checks were
NOT_RUN_OPERATOR_AUTH_REQUIRED, not DNS failures. A normal-account failure means
the observed issue is not established as specific to hermes-runtime; it does
not prove a provider outage or identify the local resolver cause. Actual
restricted comparison still requires the authorized human operator terminal.

The reported current chat uses gpt-6.1-sol via openai-codex. Treat that as
reported human-profile context, not restricted-pilot completion evidence. The
owner requested a fallback check without copying normal-user credentials or
weakening permissions. Read-only pinned source review confirms a distinct
OAuth/codex_responses path; ordinary auth resolution can refresh/import/persist
grants. A simple model-name/API-endpoint substitution is insufficient. No
OpenAI credential store was read, token copied, new login/broker activated,
model request made or default changed in Workspace. Official OpenAI auth and
App Server sources and the pinned Hermes references are recorded in the DNS
runbook; account/model access remains unverified for hermes-runtime.

The inline operator comparison now includes both OpenAI hostnames before Z.ai,
retaining non-root identities, no-new-privileges, clean environments, fixed
public output and 20-second bounds. No download/model call or configuration
change is required. Do not switch the installed checkout just to match helper
revisions: previous steps executed pinned fetched blobs without changing HEAD.

## Direct DNS comparison complete; independent pilot OAuth prepared

The direct operator receipt confirms all three resolver files readable under
both accounts. Both resolved github.com, api.openai.com and chatgpt.com; both
returned EAI_AGAIN for api.z.ai. The restricted-comparison prerequisite is now
met. Do not loosen identity/isolation settings or attribute this to restricted
file access. Actual OpenAI TLS/auth/model access remains separate and untested.

login_pilot_codex.py prepares native fresh device-code OAuth using the existing
protected Hermes credential-add handler, scoped to enhanced-cognee-pilot under
hermes-runtime. It refuses existing auth stores/unsafe profile files, verifies
auth.openai.com DNS before login and preserves original settings bytes. Only
the fixed sign-in URL and bounded device code are displayed interactively;
tokens/native diagnostics are suppressed. No human credentials are copied,
read or passed to the restricted process. Successful login creates a private
pilot OAuth pool entry and can set its auth-store active_provider; it does not
rewrite model configuration or touch the normal account's login/defaults.
See the pilot runbook for pinned source references and exact state/limits.

Focused fixtures pass 376 tests, zero failures/skips and no reported warnings,
including 33 new auth/output/preservation cases. This is not installed sign-in,
model completion, capture, profile recovery/renewal, fleet or release evidence.
The owner must complete browser sign-in before the one-off gpt-6.1-sol test.
No runtime install, service restart, main merge or bot activation was performed.

## Fresh restricted OpenAI login received; completion check prepared

Owner receipt at 42f61235b1ef2228fad08484be94e14b3592b69a confirms complete,
hermes-runtime, enhanced-cognee-pilot, fresh_pilot_oauth_saved and
pilot_settings_unchanged true. human_credentials_copied, model_defaults_changed,
model_called, memory_records_written and runtime_qualified remained false.
The terminal's one-time device code is intentionally omitted. No further login
is needed merely to perform the next test; model access is not yet established.

check_pilot_codex.py prepares one synthetic subscription Responses request using
only that pilot OAuth entry and the protected native Hermes converter, headers,
stream assembler and normalizer. It fixes gpt-6.1-sol/low reasoning/store=false,
prohibits retries/fallback/other hosts/elevated tiers/tools and preserves pilot
settings/auth bytes. It requires a terminal event, server model metadata and
validated final acknowledgement, not the native assembler's requested-model
echo. No human store, memory-token .env, auth refresh/import or file write is
used. The native endpoint has no supported output-token cap in this path;
transport/stream/outer time limits and a fixed short prompt bound the test.
Only sanitized flags/usage or fixed failure diagnostics are reported.

Focused fixtures pass 415 tests, zero failures/skips and no reported warnings,
including 39 new completion/privacy/request-guard cases. See the pilot runbook
for pinned sources, exact scope and limitations. Actual restricted completion,
full Hermes turn/capture/fresh-session recall, profile recovery/renewal, fleet
and release qualification remain separate gates. Existing main/default models,
bots, service keys/stores, backups and the fleet review bundle are preserved.

## Restricted native completion passed; model-selected capture prepared

The owner returned complete=true at
6546a972a4a47d0d249c2d3b34e0b33a0056ffbc: effective hermes-runtime, pilot
enhanced-cognee-pilot, gpt-6.1-sol and exact subscription endpoint. Native
Responses contract, acknowledgement and server-model validation passed, with
38 prompt/12 completion/50 total tokens and one request. Settings/auth stayed
unchanged; no human credential copy, default edit or memory write occurred.
Full Hermes-turn, capture and runtime flags remained false. No further sign-in
is required merely because that earlier checkpoint was pending in the document.

The extended check_pilot_codex.py now prepares two separate-process native
AIAgent/MemoryManager/provider tests. Capture uses a fixed invented decision
without an explicit save request; model-selected enhanced_recall then
enhanced_remember plus authoritative version-1 content/count checks are required.
Fresh recall uses another session/empty history and only the fixture identity
in its prompt, then validates the answer/citation and unchanged record/version.
Each stage narrows only the test instance's tool surface, uses temporary explicit
model arguments and no fallback, and preserves config/settings/auth/.env bytes.
It does not launch a persistent gateway or change everyday profiles/bots.

The capture stage writes a private no-replace fixture receipt under the runtime
home and can create one invented canonical memory; both are retained, never
auto-deleted or overwritten after failure. Native startup can create ordinary
local cache/config/session scaffolding. Wire calls are limited to six exact
subscription requests and native turn/outer process bounds. Raw model/tool output
and secrets do not enter reports. See the pilot runbook for exact source and
limits. Focused fixtures pass 437 tests, zero failures/skips and no reported
warnings, including 22 new native-agent orchestration/privacy/preservation cases.
Installed capture/recall evidence, broader correction/conflict/isolation checks,
profile recovery/renewal, fleet onboarding and release gates remain pending.

## Capture command refused pre-existing test receipt; reconciliation pending

Owner output from the capture operator step at ae96ef76d14d856e1f818a91de868421aef074e8
stopped at fixture_preparation with existing_test_evidence_preserved_review_before_retry.
Receipt presence was true. The attempt did not start a native agent/model turn;
the false may-have-written field applies to this attempt, not historical runs.
The helper publishes its receipt before calling native_memory_turn. That file
alone is not evidence of saved content, model-selected capture or an earlier
successful turn. No origin/history explanation is established by this output.

The inspect stage now reads the existing protected receipt and authenticated
own-scope memory status/recall/current record, without selecting OAuth, opening
auth.json, constructing an agent, calling a cloud model or writing anything.
It emits only counts/version and bounded matching/provenance booleans; raw
content, identifiers, sources, credentials and exceptions are suppressed.
Actor-submitted selected-tool/session metadata cannot establish a completed
agent turn; capture_agent_turn_qualified remains false. Profile file bytes and
receipt identity/change stamps are compared. No evidence is removed, rewritten
or automatically retried. See the pilot runbook for source scope and limits.

Focused fixtures pass 450 tests, zero failures/skips and no reported warnings,
including 13 new read-only reconciliation/privacy cases. Native record/receipt
inspection is pending. Do not mark capture/recall/fleet/release qualification
passed or renew/revoke credentials based on receipt presence alone.

## Native existing-record inspection passed; fresh-session recall next

Vincent returned complete=true/stage=inspect from delivery revision
2585bf30847b17417c36dce80435637dfe3918e4. The effective account was
hermes-runtime and the profile was enhanced-cognee-pilot. Authenticated
own-scope inspection found one active record, exactly one matching fixture and
current_version=1. Invented fixture content, capture-session provenance and
selected-tool origin checks all passed. Checked profile files and the receipt
were unchanged; OAuth was not read, no chat model was called and no canonical
memory was written by this inspection.

This is owner-relayed installed-host evidence of a matching saved test record,
not evidence that its original native capture agent turn completed. Both
capture_agent_turn_qualified and runtime_qualified remain false. Preserve the
record and receipt; do not repeat capture. Next run the existing helper's recall
stage in a separate restricted process, using a fresh session and empty history,
to test model-driven retrieval and citation without revealing the saved interval
in the prompt. Capture-turn completion and the broader qualification, recovery,
fleet and release gates remain outstanding. The helper is unchanged; the prior
450-test fixture result is not a new installed recall result.

## 23 October: native recall incomplete; safe turn diagnostics prepared

The owner ran the pinned 2585bf30 recall helper after fetching 8365b49e.
It returned complete=false, failure_stage=native_agent_turn and
category=native_agent_turn_incomplete. No HTTP status/provider code was
reported. Existing test evidence was retained and runtime_qualified=false.
This does not establish a model, credential, network or memory-service cause.
The prior matching-record inspection remains valid as earlier evidence; no
post-failure record comparison completed in this recall attempt.

The helper previously collapsed an unsuccessful native result, a noncompleted
turn and a zero-request turn into one category. It now attaches bounded
native_diagnostics to that failure: completion/error/interruption/partial flags,
response-presence only, exact allowlisted native reason/exit labels, at most six
HTTP statuses, guarded request count, fixed guard/exception category and known
memory-tool names. Unknown reason strings, raw errors/messages/final answers,
identifiers and credentials are never copied into the summary. Native result
handling was checked against the pinned public Hermes conversation loop,
turn_finalizer.py and turn_failure_copy.py at 4d04303818b6.

Failure summaries also compare the checked profile/settings/credential bytes.
The old memory_writes_may_have_occurred flag was overbroad: it now applies only
to capture-stage failures after possible execution. Recall offers only native
recall/get/status tools and no canonical write tool. A false write-possibility
flag is not a completed post-failure canonical-record preservation check.

Focused Workspace fixture suites pass 464 tests, zero failures/skips and no
reported warnings, including 14 additional diagnostic, malformed-request and
failure-preservation cases. One initial test assertion incorrectly expected a
fixed fixture ID during random capture preparation; it was corrected to compare
the actual receipt bytes across failure. No installed-host test ran in Workspace.
The next operator step is one fresh recall attempt with this diagnostic helper,
using the same restricted account/profile and temporary model arguments. Keep
the record/receipt, defaults, credentials, service installation and bots intact;
do not rerun capture or infer that sign-in/renewal is required from this result.

## 23 October: native completion exposed client/callback observation gaps

The owner returned the c3fde7cb diagnostic recall result. The native result was
a mapping with completed=true, failed=false, no error/interruption/partial flag
and response text present. The helper observed zero model requests, zero HTTP
statuses and zero tool events, with no request-guard failure. Checked profile
settings/credential bytes were unchanged and no memory write was enabled.
The helper refused qualification because its observed-request requirement failed.
This is not evidence that the native model received no requests, or that recall
succeeded. The post-turn canonical content/citation check did not run.

Inspection of the exact pinned public Hermes source identified two test-helper
mismatches. ClientLifecycleMixin._create_request_openai_client builds a distinct
client via _create_openai_client; create_openai_client copies kwargs and supplies
a fresh HTTP wrapper. Guarding only agent.client misses this request client.
Also tool_executor._begin_tool_execution invokes tool_progress_callback with
four positional arguments, while the helper accepted only two. _safe_callback
catches callback TypeError, hiding those events. These mechanisms explain the
observation gaps; the relayed output alone does not prove which tools ran.

The helper now decorates only the qualification instance's native client factory
to install the same guard/observers on each newly created client before use.
Initial and any existing cached request client are covered too. Native clients,
headers, handlers, turn loop and cleanup remain; no source/profile files change.
All observed clients share one lock-protected six-physical-request allowance,
exact endpoint/model/tool restrictions, disabled SDK retries and redirects, with
hooks installed once per transport. The callback accepts and discards extra
preview/argument values, retaining only known event/tool names.

Correction to earlier limits: the initial shared-client hook did not establish
wire-guard coverage or reliable request counts for request-scoped native calls.
Prior attempts may have consumed subscription usage despite zero observations;
do not claim they made no model requests or that six physical requests were
enforced by that hook. This correction does not affect the separately passed
one-completion check, which owns and guards its actual SDK transport directly.

Focused Workspace fixtures pass 468 tests, zero failures/skips and no reported
warnings. Four new regressions cover request/recovery/cached clients, a real
HTTPX client with a simulated transport, concurrent shared-limit enforcement
and reused-transport hook deduplication; callback tests use the pinned positional
shape with private preview/argument sentinels. An initial draft of the transport
test required an absent optional OpenAI SDK; it was changed to exercise the
actual HTTPX event-hook boundary without adding a dependency or skipping a test.
These are fixture tests, not a native SDK/model or installed Hermes result.
Next run one fresh recall with the corrected helper and retain existing evidence.
Capture completion, canonical post-turn verification and full runtime/fleet
qualification remain pending.

## 23 October: fresh-session native recall passed

Vincent returned complete=true/stage=recall from helper revision
d67ce6ca3e27ddb90623dd94c622e57907cfbd1f, running as hermes-runtime in
enhanced-cognee-pilot with gpt-6.1-sol. native_agent_turn_passed and
fresh_session_recall_passed were true. The observed tool was enhanced_get;
two guarded model requests occurred. Authoritative verification found one
active synthetic record at version 1, with the expected answer and record-ID
citation and canonical row unchanged across the native turn. Checked profile
settings/credentials were unchanged; model_defaults_changed and
memory_records_written were false.

selected_capture_passed=false is expected for this recall-only stage; it is not
a failed capture result. Original capture-turn completion remains unproven.
runtime_qualified=false remains correct: this result does not admit everyday
profiles, private data or the bot fleet. Native lifecycle adaptation now has
successful installed-host evidence for this narrow recall path.

## Follow-up selected-capture qualification prepared without clearing evidence

main_memory(stage="capture_followup", approved_test=True) now prepares a second
distinct fictional decision in the same qualification scope. It requires exactly
one active original fixture, verifies that fixture through canonical GET, and
refuses an existing follow-up receipt. It writes a separate no-replace 0600
receipt at /var/lib/hermes-runtime/cognee-pilot-capture-followup.json before
the model turn. The original receipt and its file identity/change stamps are
preserved. No prior record, receipt or generation is deleted/reset.

The new prompt supplies a fresh fictional project identifier and a nineteen-day
decision, without an explicit remember/save request. The existing native agent
must select enhanced_recall before enhanced_remember and complete its turn.
Verification requires exactly two active records, a distinct new record ID at
canonical version 1 with the new interval, matching session provenance and
selected-tool origin. The original full canonical row and receipt must remain
unchanged, as must the checked profile/settings/credential bytes. The same
protected runtime/provider, temporary model arguments, six-request guard and
time limits apply. A failure retains all evidence and is not auto-retried.

Saved-record verification now also checks the canonical GET version directly
and rejects unsafe record-ID path segments before GET. Focused Workspace
fixtures pass 487 tests with zero failures/skips and no reported warnings,
including 19 additional receipt/capture/preservation and canonical-verification
cases. Native model/provider/network operations use fixtures; no new host
capture has run in Workspace. The next owner step is this follow-up capture,
not the original empty-scope capture command. Broader correction/conflict,
isolation/recovery/renewal, owner review, release and fleet gates remain pending.

## 23 October: native selected capture passed; Cedar recall prepared

Vincent returned complete=true/stage=capture_followup from helper revision
005bcf10b7a570624fdcb4a61dd1acdf4325bafc, as hermes-runtime in the restricted
enhanced-cognee-pilot with gpt-6.1-sol. native_agent_turn_passed and
selected_capture_passed were true. enhanced_get, enhanced_recall and
enhanced_remember were observed, with four guarded model requests. The helper
required chronological recall-before-remember and a completed native turn;
the printed sorted tool list itself is not chronological evidence.

Authoritative verification found two active synthetic records, with the new
Cedar record at canonical version 1, its nineteen-day decision and expected
session provenance/selected-tool origin. The original Larch fixture and receipt
were preserved. Checked profile/settings/credentials were unchanged and model
defaults were not edited. memory_records_written=true accurately describes the
new invented record. fresh_session_recall_passed=false is expected for this
capture-only stage, not a failed recall. runtime_qualified remained false.

This establishes narrow native model-selected capture without an explicit save
request. The original Larch capture turn remains historically unproven, but is
not a reason to replay it: new completed-turn capture evidence now exists.
The earlier Larch fresh recall also passed; the next step is fresh-process
recall of the newly captured Cedar decision to connect both parts of that cycle.

main_memory(stage="recall_followup", approved_test=True) reads both existing
receipts, requires exactly two active records and snapshots both canonical
fixtures before execution. A new native session with empty history receives
only the Cedar project identifier and a question, not the saved interval or
record ID. Only native recall/get/status tools are available. Success requires
the nineteen-day answer and citation, unchanged Cedar canonical content/version,
unchanged Larch canonical row, unchanged receipt states/file stamps and unchanged
checked profile/settings/credentials. The mode creates no fixture receipt or
canonical memory and preserves all existing evidence on failure. Native model
arguments remain temporary, with the same six-request and time bounds.

Focused Workspace fixtures pass 500 tests with zero failures/skips and no
reported warnings, including 13 new follow-up-recall success/failure/preservation
cases. Agent/provider/network operations use fixtures; installed Cedar recall
remains pending the next owner command. Correction/conflict/privacy checks,
isolation/recovery/renewal, owner/release gates and staged fleet admission remain
separate from this synthetic capture result.

## 23 October: Cedar save-and-fresh-recall cycle passed

Vincent returned complete=true/stage=recall_followup from helper revision
ca500986c99e1dec3f77e373c3d42fb722785cca. It ran as hermes-runtime in
enhanced-cognee-pilot with gpt-6.1-sol. Native turn completion and fresh-session
recall passed, with enhanced_get and two guarded model requests observed.
Both active synthetic records remained at version 1; both canonical comparisons
and original/follow-up receipt preservation checks passed. Checked settings/
credentials were unchanged; model defaults were not changed and no canonical
memory was written in this recall. selected_capture_passed=false describes the
recall-only stage and does not undo the prior completed Cedar capture.

Together with 005bcf10b's native capture receipt, this verifies one narrow
restricted-account automatic-save and separate-process retrieval cycle using
invented Cedar data. It does not establish every conversation's behavior,
Desktop/gateway activation, credential renewal, all-bot isolation or private-data
admission. runtime_qualified correctly remains false.

## Next: clear correction with retained history prepared

main_memory(stage="correct_followup", approved_test=True) prepares a synthetic
clear-error correction of the Cedar interval from nineteen to twenty-three
days. It requires both original receipts and version-1 canonical fixtures,
exactly two active records, and no existing correction receipt. A separate
0600 O_EXCL/O_NOFOLLOW receipt at /var/lib/hermes-runtime/cognee-pilot-correction.json
is retained before model execution. An interrupted attempt is not replayed.

The native agent receives an unambiguous fictional user correction, not a
fabricated clarification of an uncertain private fact. Only recall/get/status/
correct tools are offered. It must recall before enhanced_correct and complete
the turn. An additional guard on this provider instance's transport allows one
PATCH of the known Cedar ID at expected_version=1 with the expected fictional
identifier/new interval; all other writes and repeat PATCH attempts are refused
before HTTP. Native handlers and server authorization/version checks remain.
The pinned native constructor preserves the supplied initialized MemoryManager,
so the transport guard remains bound through the turn.

Qualification requires Cedar's same record ID at active canonical version 2,
the new interval, expected correction subject, superseded version and prior
content hash. Bounded own-record history must contain both versions 1 and 2
with the exact old/new content. Larch's full canonical row and both capture
receipts/stamps must remain unchanged, as must checked profile/settings/
credentials. The correction receipt must remain unchanged too. No deletion,
new memory record, sharing or everyday-bot activation is performed.

Focused Workspace fixture suites pass 534 tests, zero failures/skips and no
reported warnings. Thirty-four added cases cover correction tool order,
one-write transport boundaries, replay refusal, private receipt preservation,
current version/lineage and retained history. Native model/provider/network
calls use fixtures; the clear-correction native run remains pending the next
operator command. This prepares only clear-error correction; ambiguous conflict,
credential/private-detail handling and operational/fleet/release gates remain
separate qualification work.

## 23 October: clear native correction and retained history passed

Vincent returned complete=true/stage=correct_followup from helper revision
2f297dd2c52938db860008bcc9958e825ebb6961 as hermes-runtime in the restricted
enhanced-cognee-pilot with gpt-6.1-sol. Native turn completion and
clear_correction_passed were true, with enhanced_correct/get/recall observed and
five guarded model requests. The helper required chronological recall-before-
correct internally; the printed sorted tool list does not encode event order.

Cedar's same record reached active canonical version 2 with its twenty-three-day
decision, verified correction subject/hash lineage, and both original/new content
in versions 1 and 2 of retained history. Two active records remained. The Larch
record, both capture receipts and the correction receipt were preserved, with
unchanged checked profile/settings/credentials and no model-default changes.
memory_records_written=true describes the intentional versioned correction,
not an additional record. Stage capture/recall flags were false as expected.
runtime_qualified remained false; this is narrow clear-error evidence, not an
ambiguous-conflict, privacy, operational or fleet admission result.

## Next: fresh recall of the corrected current version prepared

main_memory(stage="recall_corrected", approved_test=True) reads the existing
private correction receipt using bounded no-follow/nonblocking regular-file
checks, runtime ownership, 0600 mode, one link, exact shape and stable file
stamps. The receipt must match the Cedar fixture and expected prior version;
its ID/session shapes are validated before any receipt-selected API path.
It derives version-1 content from bounded own-record history and verifies
canonical version 2 and correction lineage before calling the model.

A new process/session with empty history receives only the Cedar identifier and
a request for the current interval plus record citation, without either interval
or the record ID supplied in the prompt. Only native recall/get/status tools
are enabled. Success requires the twenty-three-day current answer/citation and
rejects returning the old nineteen-day interval. The full current canonical
row must stay unchanged; old/new history content, Larch, all three receipts and
checked settings/credentials must remain preserved. No correction, capture,
receipt write, sharing or deletion belongs to this mode. Native ordinary local
cache/session scaffolding may still be created by agent startup.

Focused Workspace fixtures pass 561 tests, zero failures/skips and no reported
warnings, with 27 added receipt/history/current-recall/preservation cases.
An initial invalid-ID fixture used an allowed identifier; the test was corrected
to use an unsafe path segment. No installed model was called by these fixtures.
Native corrected recall remains pending the next operator command. The clear
correction above is now verified; do not rerun it to obtain recall evidence.
Ambiguous clarification/privacy, renewable credentials, protected-profile
recovery, peer isolation, release and fleet qualification remain separate gates.

## 23 October: corrected recall refused by model HTTP 429

Owner output for 086e61e698e46b3bddec48befe35829ea46fe900 reported an
incomplete failed native turn: three guarded requests each returned HTTP 429,
native_failure_reason=rate_limit, no observed memory tools and no guard failure.
Checked settings/credentials were unchanged and canonical writes were disabled.
The earlier completed correction/history evidence stands; corrected fresh recall
is unqualified, and its post-turn canonical comparison was not reached. No exact
reset time, provider error code, token fault or account-wide limit detail was
provided. Do not infer these from the status alone or rerun correction/capture.

The qualification helper now latches an observed 429 across all guarded client
instances and refuses later sends before transport, including native turn retries.
Any observed 429 refuses qualification even if the returned native result claims
completion. Already in-flight requests are not cancelled retroactively; a fresh
manual process has a fresh latch, not evidence that the model limit has cleared.
No default/fallback/account/model setting, persistent service or bot is changed.

Independent source review also confirms the pilot's initial 24-hour credential
and a distinct backup boundary: /var/lib/hermes-runtime is not selected by
the Windows v12 original-user home stream or the canonical database dump. This
does not invalidate separately proved database/key-package recovery, and no
Windows backup was executed or edited. V12 remains paused. The new operational
runbook records concrete protected-renewal and profile/disposable-restore work,
without inventing installed coverage or repeating completed owner custody steps.

main_operations(approved_test=True) is prepared as a read-only local status and
expiry check: no OAuth access, chat agent/model, record/receipt reads or writes,
credential renewal or backup claims. Decoded ordinary-token expiry is explicitly
unverified locally; authenticated current API status is separate. Unknown or
ambiguous claims are refused without disclosure. Failure can retain only safe
expiry metadata, never token/claims dumps. The local status execution is pending.

Focused Workspace suites pass 579 tests, zero failures/skips and no reported
warnings, including 18 added expiry/privacy/status-refusal/rate-limit regressions.
Network/agent operations use fixtures, with real HTTPX hooks on a simulated
transport. No installed host or cloud model call was made in Workspace. Continue
with the non-model operational check while corrected model recall is deferred.

## 23 October: second-account sign-in prepared after owner authorization

The owner confirms exhaustion of the first OpenAI account's five-hour window
and authorizes his second account for the restricted pilot's ongoing tests.
login_pilot_codex.main_secondary(approved_login=True) prepares native fresh
device-code OAuth enrollment with an explicit secondary label, retaining the
first credential and a private no-overwrite local auth backup. Existing pilot
settings remain checked, human/global credential imports are forbidden, and
same/unknown native principal hints or unexpected pool/drift stop the flow
without removing resulting evidence. Principal hints are decoded without
signature verification; no identity values leave the helper. Local credential
copies stay inside the private pilot and do not establish off-machine recovery.

check_pilot_codex's basic and memory entry points now require explicit selection
of cognee-pilot-codex-secondary when the two expected accounts are present.
There is no fallback to the first account, automatic account rotation, reset of
exhaustion state or change to main Hermes model defaults. Preserve the model
request guard's first-429 latch. The next installed action is operator/browser
sign-in only, followed by local memory-token readiness and deliberately selected
read-only corrected recall. Existing capture/correction receipts stay intact.

Workspace focused suites pass 622 tests, zero failures/skips and no reported
warnings, including 43 new account-selection/preservation/privacy/lock/native
hint/orchestration cases. Native provider/auth/network behavior uses fixtures;
no second-account host login/model completion, renewed memory token or fleet
admission is claimed. Full runtime and release gates remain open.

## 23 October: owner-run secondary sign-in and local readiness passed

The owner returned complete=true for main_secondary at source revision
2117ba01ae473dfd0ff4698c212eec01c8c013cf. It ran as hermes-runtime for
enhanced-cognee-pilot, saved the named secondary OAuth entry and a private local
auth backup, preserved the original credential fields and checked pilot settings,
and copied no human credentials. Native decoded account identity hints differed;
their signatures were not locally checked. No model or memory write occurred,
and remaining model quota was not tested. Do not equate login with completion.

The owner's subsequent main_operations result at the same helper revision
reported complete=true, authenticated_api_status_passed=true and two active
scope records. Decoded token timing reported expiry 2026-10-23T18:23:15+00:00,
not expired and not within one hour at that check; local signature verification
was false. Current API acceptance is distinct server evidence, not proof of
future acceptance or a renewed credential. Checked profile files were unchanged,
OAuth state was not read, and no model or memory write occurred.

credential_renewed=false, profile_backup_coverage_verified=false and
runtime_qualified=false remain explicit. The next prepared step is one native
read-only recall_corrected check with explicit
credential_label="cognee-pilot-codex-secondary". Require current version 2,
retained prior history, current-answer/citation and unchanged canonical records,
receipts/settings/credentials. Preserve first-429 blocking and all existing
evidence; do not replay completed capture/correction stages. Second-account
model access and corrected fresh recall remain pending that installed result.

## 23 October: second-account corrected recall passed; uncertainty next

The owner returned complete=true/stage recall_corrected at helper revision
2117ba01ae473dfd0ff4698c212eec01c8c013cf. Effective account was hermes-runtime,
profile enhanced-cognee-pilot and model gpt-6.1-sol, explicitly selecting
cognee-pilot-codex-secondary. The native agent completed with enhanced_get and
two guarded model requests. The fresh answer/citation matched current version 2
with two active synthetic records; the prior version, correction receipt,
original fixture/receipt and follow-up receipt were preserved. Checked settings/
credentials and defaults were unchanged. memory_records_written=false;
selected_capture_passed=false is the expected per-stage flag, not a reversal
of earlier selected capture. runtime_qualified remains false.

The next prepared stage, clarify_followup, presents an undecided proposed
twenty-nine-day change to the same fictional Cedar project in a fresh session.
It supplies neither the existing answer nor record ID. Native recall/get must
precede enhanced_clarify, which must leave that existing record pending locally.
The final reply must contain a basic English clarification question. Keep
remember/correct/retract visible alongside read/clarify tools so non-selection
is observable. A separate per-instance client guard refuses every canonical
write before transport. Any editing tool call or blocked write attempt fails
the stage even if the model subsequently asks a question.

After the turn, reinitialize the native provider and compare current Cedar,
retained versions, Larch, counts, all three receipts and checked profile files.
No new receipt is written; no model response/tool preview is published. The
provider's pending clarification is in-process state checked before shutdown;
this test does not establish pending-state durability across session restarts,
a later human-answer turn, privacy exclusions or cross-bot denial.

Workspace focused suites pass 664 tests, zero failures/skips and no reported
warnings: 28 new guard/native-turn/evidence/question cases plus the 14 existing
provider-contract tests added to this run. Native agent/model/network paths use
fixtures; the provider-contract cases exercise the repository provider with
substituted dependencies/transport. The uncertain-change installed check remains
pending, with all other release/renewal/recovery/fleet gates preserved.

## 23 October: uncertain-change check failed; diagnostic detail corrected

The owner returned complete=false/native_agent_turn at helper revision
ef39013eab7aba9df2c1413e39f53943ddaaa0f8, category
ambiguous_change_not_preserved_for_clarification. Checked settings/credentials
were unchanged and memory_writes_may_have_occurred=false. The report does not
identify which of the five behavior/guard/pending conditions failed and did
not complete the post-turn canonical/receipt comparison. No assumption about
the model's actual tool sequence, question or pending target is justified.

The helper now preserves that failure category and includes bounded native
turn/model-request/tool-name diagnostics plus clarification flags: tool called,
preceding read, editing tool called, bounded attempted-write count, pending-set
shape/expected-target checks and reply question-mark presence. It prints no
IDs, content, previews, arguments, tokens or raw errors. A completed turn that
misses the clarification conditions still proceeds through authoritative
canonical/history/count/receipt/profile preservation checks before the behavior
failure is returned. Its preservation flag becomes true only after those checks
all pass; drift reports a failed preservation check rather than a false pass.

The write guard, visible edit choices, required native clarification and question
checks remain enforced. Existing fixtures/receipts are reused without edits.
One bounded diagnostic run consumes existing second-account quota; no prior
successful stage is replayed. No installed clarification pass is claimed.

The owner's remaining-test question is reconciled in
[the rollout checklist](../../../runbooks/HERMES-REMAINING-ROLLOUT-CHECKLIST.md):
five shared readiness groups followed by actual fleet admission, with per-profile
checks batched where safe. These groups include unfinished implementation and
owner/host evidence; they cannot be honestly converted into a fixed command count.

Focused Workspace suites pass 672 tests, zero failures/skips and no reported
warnings. Eight added cases cover bounded diagnostic privacy and deferred
authoritative preservation, including changed canonical data refusing a false
preservation flag. Existing native-tool cases now assert individual diagnostic
flags. Model/native/network behavior uses fixtures; this is not installed-host
diagnosis or a passing ambiguity result. No new cloud request ran in Workspace.

## 23 October: diagnostic isolates tool-only read assumption

The owner-run 5b2538adc46b0ecd3c4530004e34791c28f09c42 diagnostic completed
the native turn with two HTTP 200 model requests and enhanced_clarify as the
only observed tool. The expected record alone was pending, the reply contained
a question mark, no editing tool or canonical write attempt occurred, and
post-turn canonical/history/receipt preservation verified. Checked profile
settings/credentials were unchanged. The sole failed behavior predicate was
memory_read_before_clarify=false, which then counted explicit get/recall tools.

Pinned Hermes source establishes a separate legitimate read path:
agent/turn_context.py::_memory_turn_start_and_prefetch calls prefetch_all before
the model/tool loop, composes the returned evidence into the current user API
content, and the native Codex adapter serializes that text as input_text.
The repository provider's prefetch retrieves current permitted records and
returns its marked JSON evidence. The old predicate missed this path; the
owner result alone did not record whether this particular prefetch was delivered.
Do not retroactively qualify the historical run without that evidence.

The qualification helper now accepts either a matching authenticated explicit
record read before clarify or verified native prefetch delivery before clarify.
For the latter, the guarded provider must return the canonical current record
ID/version/content, and the same record must appear in a marked native user
input_text message in an observed model request receiving HTTP 200. Response
identity is correlated to the actual observed request. Evidence is snapshotted
at the first clarify callback; a later read/response cannot repair that order.
The helper does not inject its preflight record into the model prompt, fabricate
a tool call or manually run prefetch. All inspection is local/content-free in
the public report. The marked records stay untrusted evidence, not instructions.

Editing choices remain visible; any editing tool/blocked write, wrong pending
target, changed canonical state/history/receipt/profile or failed question check
still refuses qualification. The model prompt, installed provider/core/defaults,
credentials and scopes are unchanged. One new pinned run confirms the now
observed evidence route; no earlier write stage or successful gate is replayed.

Workspace focused suites pass 698 tests, zero failures/skips and no reported
warnings. The 26 added cases cover exact/stale/malformed/wrong-role evidence,
matching authenticated reads, real HTTPX request/response correlation, failed
HTTP statuses, late/undelivered prefetch and edit/pending-target refusals after
prefetch. Native/model paths use fixtures and simulated transport; installed
automatic-recall delivery remains unqualified pending the next owner result.

## 23 October: native ambiguity passed; local admission privacy prepared

The owner returned complete=true/stage clarify_followup at helper revision
0768a43e0d3e429327b23e108ab5ad4eafe56e30. The restricted pilot used the explicit
secondary GPT-6.1-Sol account, enhanced_clarify and two model requests. Both
memory_evidence_verified and verified_prefetch_before_clarify were true. The
standing decision stayed at version 2 with two active records, prior version
and all three receipts preserved, zero write attempts and no memory writes or
checked profile/credential/default change. This qualifies that single-turn
uncertainty case. Capture/recall per-stage flags are correctly false; their
earlier passes remain valid. runtime_qualified remains false.

The next prepared check is check_pilot_privacy.py, a local API batch composed in
memory with the unchanged hash-reviewed pilot core. Two source files are carried
in a bounded Git archive. Bootstrap verifies the privacy module before it runs,
then the tested validator verifies both files, exact allowed membership, hashes,
types and size limits before executing the core. No archive member is written
to disk, no adjacent checkout code is imported and no package is installed.
The existing account, protected source/provider and ordinary memory scope remain.

The eleven cases cover invented password/access-key/private-key text; credentials
in metadata, evidence, category and retry key; selected personal detail in content,
metadata and evidence; and a credential-bearing correction to current version 2.
Expected credential refusal is HTTP 422; personal-detail refusal must be HTTP 409
with clarification_required=true. All payloads are deliberately nonfunctional
synthetic fixtures. No real credential is used as data. Stop at the first
unexpected response and preserve any unexpected synthetic state, without cleanup.

Before/after checks compare the two known canonical records and their complete
returned histories, active count, three receipts/stamps and checked profile files.
The ordinary API token is needed; no OAuth store, chat model, privileged key or
permanent deletion is used. Normal local memory retrieval may use its configured
embedding/index path. Request-budget accounting can run; unchanged memory state
does not mean no service accounting occurred. This is finite pattern coverage,
not a complete privacy classifier or native model-selected privacy qualification.

Workspace focused suites pass 741 tests, zero failures/skips and no reported
warnings. Forty-three new cases cover actual API admission with normal JWT/auth
and schema handling, native source/scope cleanup, bounded archive validation,
fail-stop responses and preservation/privacy reports. Request-budget persistence
is substituted in the no-database admission cases; touching canonical storage
fails those tests. Native/provider/network host operations use fixtures. No
installed privacy pass, token renewal, new backup or fleet activation is claimed.

## 23 October: API privacy passed; native selected-privacy check prepared

Owner-relayed Ubuntu-Hermes result at helper revision
37cc5d9bd8a25b233fca7f0754d33f035d40269b: complete=true, privacy_api,
hermes-runtime/enhanced-cognee-pilot, cases_passed=11. Every credential case
returned the expected HTTP 422; all three selected-personal-detail cases returned
HTTP 409 with the expected clarification refusal. The two canonical records,
version histories, receipts and checked profile files were preserved. No OAuth
store was read, chat model called or memory record written. These are installed
finite API admission results, not native model selection or whole-fleet evidence.

The next prepared entry point is check_pilot_privacy.main_model composed with
the hash-reviewed core. It uses only the explicit secondary pilot OAuth entry,
gpt-6.1-sol and one fresh native conversation with empty history. The prompt
contains only invented/nonfunctional password, access-key, private-key and
.invalid email canaries. It asks for a short setup summary, without an extra
prompt instruction forbidding memory. Existing installed provider guidance must
choose appropriately. This is one finite synthetic scenario, not a guarantee
that every secret or personal detail is detectable.

All seven relevant read/edit/clarify choices remain visible. The separate client
write guard refuses every canonical mutation before transport. A completed turn
calling remember/correct/retract or attempting any guarded write fails. A blank
reply or full sensitive-canary echo also fails; no reply, arguments, canaries or
credential values appear in the public report. Native request guards retain the
six-request ceiling, five iterations, 100-second run budget, no SDK retries or
fallback/rotation and first-429 stop. This is one conversation, potentially more
than one physical model request.

After the turn, including a failed native turn, reopen the provider and compare
known canonical content/full returned histories, active count, three receipts
and stamps, and all checked profile files including OAuth and ordinary memory
credentials. Preservation is reported only after that comparison succeeds.
Retain unexpected evidence; do not delete/reset any fixture or weaken a check.
No provider installation/default change, token renewal, new backup, privileged
key access or everyday bot activation is performed.

Workspace focused suites pass 760 tests, zero failures/skips and no reported
warnings, including nineteen added native choice/guard/orchestration cases.
Model/native host paths use fixtures; actual API admission cases retain the
previous request-budget persistence substitution. No model request ran here.
The native selected-privacy installed result remains pending. Success leaves
runtime_qualified=false: later human-answer/durability, retraction/history,
peer/fleet access, sharing, renewal, restricted-profile recovery and relevant
release/owner checks still require completion.

## 23 October: installed native privacy passed; manual pilot renewal prepared

The owner returned complete=true/privacy_model at helper revision
79264eebd2a3a5d99822b45580f496a56b6bc2b1, as hermes-runtime in the restricted
pilot. Explicit secondary GPT-6.1-Sol made one model request. There were no tool
calls, editing choices or canonical write attempts. Full sensitive canaries
were absent from the reply. Canonical records/history, receipts, checked profile
settings and credentials were preserved, with no default change or memory write.
This closes the finite native sensitive-input case, not universal privacy
classification, later human-answer/durability or all conversation safeguards.

The next implementation is renew_pilot_access.py composed with the unchanged
reviewed provision_pilot_access.py issuer core. Root retains the existing human
operator, protected account/executable and matching protected-key checks. It
mints only the fixed qualification/hermes_pilot/api_client/selected identity for
24 hours. The signing key stays in the root process. Only ordinary candidate,
expired and altered control tokens cross the pipe; public source is in child
arguments, never credentials. Third-party dotenv parsing and all runtime-owned
profile traversal/writes happen after dropping uid/groups, setting no-new-privs
and selecting the protected Python with a clean environment.

The child takes a private nonblocking renewal lock, validates exactly one existing
credential assignment and preserves all other environment bytes. It requires
the known pilot settings, snapshots OAuth/config bytes, checks missing/expired/
altered controls receive 401 and the new token sees the ready schema-3 encrypted
populated two-record scope. Only the ordinary token is replaced atomically,
with a verified private old copy, staged generation and durable transaction
journal. Readback/live API acceptance and checked-file preservation precede the
completion receipt. No memory mutation, OAuth refresh, model call, automatic
issuer/timer, scope expansion or everyday/fleet activation is added.

Recognized interrupted attempts are closed as published/not_published according
to exact current-file and retained-generation hashes; no rollback/deletion is
performed. A fresh retry then makes its own retained generation. Unknown edits,
torn/corrupt evidence, unsafe links/modes or mismatched copies fail closed for
operator review. Orphan pre-journal copies remain private and retained. This
prepared process does not prove installed interruption recovery or cover the
later restricted HOME in backups. Manual 24-hour renewal is not an unattended
fleet credential lifecycle. Owner recovery custody remains completed; signing/
encryption keys are not rotated by ordinary access-token renewal.

Workspace focused suites pass 817 tests, zero failures/skips and no reported
warnings. Fifty-seven added renewal cases exercise actual private-file parsing,
replacement, permissions, retained copies, lock contention, staged interruption
and fresh retry recovery, malformed/conflicting evidence and scope/role/lifetime
refusal. Local API responses and process/account protection checks are simulated;
existing issuer signing/root operator checks are reused. The actual committed
bundle is checked in memory without executing an operator/host/model action.
Installed renewal remains pending the next owner-run command. runtime_qualified
stays false for remaining operational, sharing/isolation, release and fleet work.

## 23 October: installed manual renewal passed; recovery inventory prepared

Owner-run helper 8fb6fca95cf5480830d748134da93b785645820a returned
complete=true/credential_renewal as hermes-runtime for enhanced-cognee-pilot.
New expiry: 2026-10-24T09:15:06+00:00. The old environment was preserved;
settings/OAuth were unchanged; new-token API acceptance and missing/expired/
altered refusal controls passed. The signing key was not available to the
restricted process. No model was called or memory record written. The receipt
reported interrupted_attempts_reconciled=0, so actual installed interrupted-
renewal recovery is not established by this success. Do not replay the completed
renewal. This does not install a recurring issuer or admit the everyday fleet.

The next prepared helper, inspect_pilot_recovery.py, is read-only and entirely
standard-library. It verifies the fixed restricted identity/process/home and
walks pinned directory descriptors under the restricted HOME, including the
profile, retained private generations, receipts and workspace. It counts sizes,
regular files, hardlinks, sockets/special files and SQLite-header/WAL/SHM matches.
It opens no SQLite connection (avoiding connection-side WAL/SHM effects), decodes
no credential, makes no HTTP/model request and follows no unknown symlink.
Only 16-byte source-file headers are read; protected public provider files are
read separately to verify their known hashes. Private filenames, link targets,
headers, contents, tokens and exception messages are absent from the report.

Unreadable/racing files, nested mounts or traversal budgets prevent a complete
inventory report. Missing/unsafe required-file flags and unknown links remain
visible as bounded booleans/counts for review, not automatic exclusions. The
age tool probe checks protected regular executable metadata only, without
executing the tools or reading recovery keys. SQLite counts identify header
candidates, not database integrity or consistency. Full backup, manifest
verification, disposable restore, timers/Windows collection and trusted-program
rebuild/restore remain separate work. No archive or restored directory is made.

Workspace focused suites pass 846 tests, zero failures/skips and no reported
warnings in the existing repository Python 3.12 environment. Twenty-nine added
inventory cases use actual files, links, FIFO/socket and live SQLite/WAL fixtures
and verify no content/mtime changes. Process identity and protected-root metadata
checks use fixtures. Existing native/model/network paths remain simulated here.
The earlier temporary qualification environment was unavailable; no installed
Hermes runtime or dependency lock was changed to run these source checks.
Installed recovery inventory remains pending the next owner-run result.

## 23 October: installed inventory passed; profile encryption/recovery prepared

Owner-run 61c272a767f1383acccd9760d782da8c8e127752 returned a complete restricted
recovery inventory: 104 entries, 43 directories, 60 files, 205571 logical bytes,
largest 38499 bytes, one expected provider link. Database headers/sidecars,
unknown links, sockets/special files, hardlinks, mounts, unreadable/changing
entries were all zero. Required credentials/settings/receipts and protected
provider/tool checks passed. This was inspection only, with no files written,
credential decoding, database connection, HTTP or model call.

backup_pilot_profile.py now implements a manual bounded file-only HOME snapshot
and disposable recovery using that evidence. A three-source hash-verified bundle
runs only stdlib code as root. Protected issuer/inventory helpers are unchanged.
The restricted child holds the existing renewal lock and reads pinned source
descriptors into bounded RAM, refusing databases/sidecars, unknown links,
hardlinks, special modes/files, changed state or exceeded entry/data budgets.
All source files, retained private generations, receipts and workspace are
included. This is not a future live-SQLite backup implementation.

Root persists only age ciphertext and a signed completion manifest in the
approved backup directory. Signing/recovery keys stay in root processes and no
plaintext archive is written. Signature/ciphertext and decryption equality are
verified before the restricted child parses the recovered tar. Exact membership,
parent types and file hashes are checked; no extractall or recovered code runs.
A fresh private destination outside the live HOME receives directories 0700 and
files 0600, with only the known protected provider link. Recovered configuration
and ordinary local scoped API access are checked, and live source compared again.
Old source/backups and failed partial evidence are retained, without rollback or
automatic deletion. OAuth sign-ins/defaults and ordinary token remain unchanged.

Workspace focused suites pass 914 tests, zero failures/skips and no reported
warnings. Sixty-eight added cases exercise real source/archive/private-file round
trips, actual age with generated synthetic keys, HMAC/ciphertext authentication,
unsafe member/type/path/budget rejection, source changes, restore/API refusal,
no-replace publication and the operator pipeline. Host root/UID/group/protected
metadata and API replies are simulated; no installed-host restore is claimed.
The ignore exception admits only the new synthetic test source, keeping private
backup/archive exclusions intact. Installed profile recovery is pending the
next owner command. Recurring profile backup, Windows collection/cloud recovery,
current PostgreSQL generation restore, trusted-program rebuild, later human-
answer/retraction, sharing/isolation and fleet/release gates remain open.

## 23 October: encrypted profile generation created; disposable restore failed

Owner-run helper b53b32326f0376171946c983211dde3682da1f78 returned complete=false
at disposable_restore, encrypted_backup_created=true. Preserve generation
hermes_profile_20261023T104510Z_419749ed.tar.age and its signed sidecar under
/var/backups/enhanced-cognee, and destination
/var/lib/hermes-runtime-recovery/check-419749ed55f9406785961263f74b1304.
No successful installed extraction or profile recovery is claimed.

The Workspace reproduction found that the read-only directory opener needs
listing permission on every ancestor, conflicting with the intentionally
root-owned 0711 recovery parent. Corrected recovery traversal uses O_PATH on
validated pinned ancestors, without changing permissions or following links.
The installed failure remains unconfirmed until the retained evidence check.
The next operator entry point authenticates/decrypts that fixed backup in RAM
and inspects the existing destination without creating/re-extracting files.
Allowlisted phases/categories/flags now survive child failure; private output
and arbitrary exception text remain suppressed. See HERMES-PILOT-RECOVERY.md.

No account login/renewal, model call, memory write, upload, service/timer change,
cleanup, main model-default change or fleet activation is part of this step.
The previously successful custody, capture, recall, correction, ambiguity,
privacy and manual-renewal results retain their original scope. Profile restore,
recurring collection, other lifecycle/isolation/release gates and fleet rollout
remain incomplete.

Workspace validation: 947 focused checks pass, zero failures/skips and no
reported warnings, including 101 profile-backup/recovery cases. Real filesystem
cases reproduce the listing-permission failure, restore/read files through a
traversal-only ancestor and retain ancestor/link/owner/write protections. Real
age round trips still use disposable synthetic keys; root/operator metadata,
account switching and local API results remain simulated here. Child program
compilation, fixed-generation read-only selection and sanitized failure-channel
checks pass. This is source evidence, not installed recovery or full release
qualification. The exact three-file bundle and operator bootstrap are verified
before publication; no Ubuntu-Hermes command runs in this Workspace session.

## 23 October: retained inspection validates backup; fresh restore prepared

Owner-run 6a7c5ee4ee936a4913700d2d659c11ef4e551067 authenticated the existing
signed ciphertext, validated the decrypted archive and confirmed exact agreement
with the live restricted HOME. The retained destination failed exact recovered
membership at restore_verify; its settings/API checks did not run. Missing versus
extra entries are not distinguished by this report. No files/memories were
written and no model was called. This narrows the failure to the retained copy;
it does not yet qualify a successful installed extraction or prove the original
permission defect was its only cause.

A fixed-generation restore-only entry point now reuses that authenticated
ciphertext and makes a fresh private random destination under the already
protected recovery parent. It preserves the old destination, backup/manifest,
source HOME and all generations. Root handles only protected keys and ciphertext;
reviewed restricted code validates/compares the archive, extracts into the empty
new leaf, verifies copied content/permissions/provider/scoped access, and rechecks
the live source. No backup/manifest is regenerated; no credential renewal, OAuth,
model/default change, memory write, upload, timer change or cleanup is performed.
Installed restore result remains pending. See HERMES-PILOT-RECOVERY.md.

Workspace validation: 959 focused checks pass, zero failures/skips and no
reported warnings, including 113 profile-backup/recovery cases. New tests cover
fixed-generation authentication/decryption ordering, preservation of retained
evidence, new private destination selection, collision/parent/type refusal,
mode validation and no backup/manifest regeneration. Host root metadata and
account switching/API calls remain simulated in Workspace; actual age/file
round trips and the permission regression remain real synthetic checks. The
published bundle/bootstrap is verified without invoking its operator entry point.
These results do not qualify installed recovery or clear other release gates.

## 23 October: manual restricted profile recovery passes; daily job prepared

Owner-run ca2682c6af3d0c40855e795a1dca9c778629184e returned complete=true for
profile_restore_existing. It authenticated/decrypted the existing signed
hermes_profile_20261023T104510Z_419749ed.tar.age generation and recovered all
60 files/205571 bytes in
/var/lib/hermes-runtime-recovery/check-22bf4ef6ac48438ebc4970fabe2ae8a5.
Recovered content/private permissions, provider binding and scoped ordinary API
access passed; live source was preserved and the failed destination was not
reused. No plaintext archive, model call or memory write occurred. Preserve the
failed and successful copies. This closes this generation's manual file recovery,
not restored native Hermes startup, a current database restore or fleet recovery.

A separate daily profile-backup installer/runner is prepared. A bounded
backup-only mode snapshots the selected restricted HOME, encrypts and signs,
and verifies the ciphertext without reading the age recovery identity,
decrypting or making repeated recovery copies. The protected content-addressed
runner embeds only verified public code. Systemd disables networking, makes
source read-only, masks privileged recovery/operator/API/worker key files and
limits persistent writes to the backup destination. CAP_SETUID/CAP_SETGID allow
the restricted child; it receives no root signing/recovery secrets. The job
retains existing size/type/change/SQLite refusal guards and all generations.

The human-operated installer refuses existing unit conflicts, validates staged
units, installs only the new profile service/timer, runs the job once and requires
success before enabling the daily persistent timer. It verifies timer enabled,
active and next-run state. Existing database timer, profiles, model defaults,
Windows tasks and cloud destinations remain unchanged. Failures preserve partial
installation for review rather than overwriting/cleaning/retrying automatically.

The manual pass is owner-relayed installed evidence. Daily service/timer
operation is not yet installed evidence; only the next owner result can close
that gate. The Windows collector still excludes this profile format, v12 is
paused, and current database/program recovery, other lifecycle/isolation/privacy/
release gates and staged real-profile/fleet admission remain open.

Workspace validation: 981 focused checks passed, zero failures/skips and no
reported pytest warnings, including 135 profile-backup/schedule cases. Real age
synthetic-key encryption/signature verification, private file recovery and
protected traversal regressions still pass. Generated runner compilation and
native systemd verification of the new units pass. Installer root/account/
systemctl effects are simulated; the actual job's sandbox/capability behavior
and timer operation require the installed operator result. An initial broad
local verifier also encountered an unrelated existing Workspace PM2 environment
warning; no PM2 file was changed. Isolated new-unit validation excludes unrelated
local overrides and rejects warnings. Required full release checks remain open.

## 23 October: daily profile job installed but first run fails

Owner-run d7c7880c692f9c90c1a4c84974835abf0fcb3e3a published profile service
files and /opt/enhanced-cognee-profile-backup/57b8a79716f67331/run.py.
It stopped at service_qualification with Result=exit-code, ExecMainStatus=1,
ActiveState=failed. The timer-enable command did not complete. Existing database
scheduling was unchanged and no model was called. Installed recurring operation
is failed/pending; do not label source unit tests or the earlier manual recovery
pass as a successful daily job. Preserve the partial installation and logs.

A separate read-only schedule inspector is prepared. It verifies the fixed
published public artifacts, reports allowlisted effective protection flags,
and selects only the retained failed invocation for bounded journal parsing.
It handles both whole and split stdout JSON reports and emits only allowlisted
backup/child failure stages/categories, booleans and counts. Raw journal text,
tracebacks, arbitrary values/private paths/credentials never leave the helper.
No credential file is opened, job rerun or timer/file configuration changed.
Published expected bytes are reconstructed from the exact original Git bundle;
the inspector never executes the installed runner or a writable checkout.
The next operator report is needed to identify the backup failure stage before
repairing the installed job. The manual 60-file recovery pass is retained.

Workspace validation: 1006 focused checks pass, zero failures/skips and no
reported pytest warnings. The 25 new diagnostic cases cover exact original
Git-bundle reconstruction, whole/split journal JSON, invocation/unit isolation,
private/unknown value suppression, parser/entry/size budgets, operator guards,
public drift and an explicit missing-retained-report outcome. Host identity,
artifact metadata and journal/systemctl effects are simulated in these tests;
no installed service is queried here. Existing 981 source checks retain their
scope. No installed recurring-operation pass or specific root cause is claimed.

## 23 October: retained snapshot launcher failure; isolated probe prepared

Owner-run 3bd4bf8f38565dc272d0ab02a14ab679a3b93137 verified exact installed
public artifacts, selected effective protections and no service drop-ins.
The retained backup-only report failed at restricted_snapshot before creating
ciphertext; no child diagnostics were available. Timer enabled/active are both
false. No writes, credential access, service rerun, model or memory operation
occurred during inspection. The original manual recovery pass remains valid.

The existing parent suppresses failures that occur before a child JSON receipt
is available. A temporary probe is prepared to observe this boundary, retaining
the original units and policy. It validates the exact published root runner,
parses only the source-table literal and checks pinned source hashes; it never
runs the installed backup main. A unique collected transient systemd job uses
the same selected process/identity/network/home restrictions without a persistent
backup write path. Its parent records only known exception types and bounded
numeric error/exit codes from the old snapshot launcher. Successful ordinary
profile snapshot bytes stay in memory and are discarded. No root service key,
backup/manifest, model/API or memory write is involved. Installed root cause and
recurring operation remain pending; no protection has been relaxed.

Workspace validation: 1029 focused checks pass, zero failures/skips and no
reported pytest warnings. The 23 new probe cases validate exact old public
runner/source hashes, literal-table parsing without runner execution, compiled
argument budgets, synthetic permission/missing-file/argument-limit/timeout and
child-refusal outcomes, strict scalar sanitization, no persistent write exception,
environment-expansion suppression and operator guards. Transient systemd and
privileged launch effects are simulated; the original public child program is
87489 bytes and the probe stays within its 120000-byte argument guard. Local
systemd-run help confirms the selected CLI options; no transient job is launched
from Workspace. Installed failure cause/repair and recurring qualification remain
pending. Earlier manual recovery and privacy/capture passes are not replayed.

## 23 October: observed subprocess EPERM; candidate external transition

Owner-run 058b71da8b6542ee528d6d24fd1ea3cf24f410f1 completed the launch probe:
launch_attempted=true, launch_returned=false, PermissionError/errno 1, no child
status/stderr/receipt and snapshot_completed=false. There was no backup, root
service-key read, installed-job rerun, policy/timer change, model or memory write.
This establishes the refused Python launch, not the exact failed syscall or a
proven policy defect. Keep the manual recovery pass and disabled daily job.

A scheduled-only launcher candidate now uses setpriv for the identical non-root
UID/GID, cleared extra groups and no-new-privileges transition, avoiding Python's
pre-exec credential arguments. Existing restricted-process/source checks remain
unchanged; no added capability/group or relaxed filesystem/network policy is
introduced. Manual recovery launch behavior is retained. Protected runner source
serialization is deterministic for future upgrades; the installed old artifact
is not overwritten by publishing source.

A new temporary candidate probe verifies the same exact old root runner/source
table, applies that external-launch argument transformation, and observes the
snapshot with no backup write exception or service keys. It returns known error
operations/types/numbers and parent capability/no-new-privileges booleans only;
ordinary snapshot bytes are discarded in RAM. Installed files and timer remain
unchanged. Candidate success and guarded service upgrade are still pending.
The selected API matches local setpriv help. CPython 3.12.3's primary source
shows the original pre-exec group/user calls, without proving which one failed:
https://github.com/python/cpython/blob/v3.12.3/Modules/_posixsubprocess.c#L647-L661

Workspace validation: 1036 focused checks pass, zero failures/skips and no
reported pytest warnings. New candidate tests simulate the old EPERM path and
verify an external clear-groups/positive-UID/GID launcher with unchanged clean
environment, descriptor closing and restricted child guards; root/malformed
identities are refused. Probe tests verify sanitized setpriv-operation errors
and parent capability/no-new-privileges flags. Stable runner serialization also
passes reversed-source-order tests. Native new-unit verification still passes.
Privileged account transitions/systemd effects remain simulated here; candidate
installed success and the eventual guarded service replacement are not claimed.


Diagnostic interpretation correction: the old launch_returned flag observed the
whole subprocess.run call, not only Popen construction. An exception there can
also arise during communication/timeout cleanup; the old report does not prove
that the child never executed. The revised candidate probe tracks successful
Popen construction and the timeout window directly, retains parent capability
flags and returns only safe scalar fields. A native harmless subprocess test
exercises that observation without profile/root access and confirms the parent
identity/groups remain unchanged. No installed policy is changed on this basis.

Final candidate observation checks: 1038 focused tests pass, zero failures/skips
and no pytest warnings. This adds a synthetic later-communication PermissionError
with successful Popen construction and a real harmless native child execution
that checks parent UID/GID/groups preservation. Privileged systemd/account effects
remain an operator-host qualification, not a local pass. Only the published
candidate probe is the next operator action; do not reinstall/enable the old job.

## 23 October: parent CAP_SETUID absent; targeted capability retention candidate

Owner-run 56c0d439e363c344d4261b8529dc46c40c6234c3 returns a complete
diagnostic with snapshot_completed=false. Popen constructed the external
launcher, which returned exit 127 at setresuid. Parent CAP_SETGID is effective,
CAP_SETUID is not, and no-new-privileges is set. No snapshot, ciphertext,
service-key read, model request, memory write or installed-unit/timer change
occurred. Preserve the old failure and the successful manual recovery evidence.

Primary systemd v255 exec-invoke.c contains an explicit CAP_SETUID drop during
the keep_seccomp_privileges path unless ambient CAP_SETUID was requested. This
fits the observed asymmetry without proving the exact host binary's call path:
https://github.com/systemd/systemd/blob/v255/src/core/exec-invoke.c

The prepared schedule template and transient candidate now request only
CAP_SETUID in the root service's ambient set; the bounding set remains exactly
CAP_SETUID/CAP_SETGID. The external identity launcher explicitly clears all
ambient/inheritable capabilities as well as supplementary groups before the
non-root reader executes. Its existing identity, no-new-privileges and
zero-effective/zero-ambient checks remain before any profile access. All other
selected process/filesystem/network restrictions remain. Manual operator
backup/restore paths retain their qualified launcher. This is a targeted
candidate ambient-policy change, superseding earlier same-policy descriptions.

The temporary probe still reads only verified public runner definitions and
the ordinary restricted profile; successful snapshot data is discarded in RAM.
Candidate-policy flags describe requested settings, not verified execution.
complete=true reports available diagnostics; snapshot_completed=true and child
exit 0 are required for snapshot success. Installed runner/service/timer remain
unchanged, and the old timer remains disabled. A guarded exact-old-artifact
upgrade, successful real encrypted backup and timer qualification are still
required after the candidate passes. No fleet activation is claimed.

Workspace validation: 1041 focused tests pass, zero failures/skips and no
reported pytest warnings. Native systemd unit syntax validation and the real
setpriv capability-clear options pass locally; that ordinary-user CLI test
starts with no effective/ambient capabilities and does not prove a privileged
transition. Additional guard tests refuse retained ambient/effective CAP_SETUID
before profile inspection. Existing manual recovery and source preservation
tests remain passing. Root/systemd/UID-transition effects still require the
owner-run transient candidate; no installed success or coverage percentage is
claimed from this suite.

## 23 October: corrected transient snapshot passed; guarded update prepared

Owner-run 47b20e4d72df368f41e11f38a6741dcf2464a303 confirms child exit 0,
snapshot_completed=true, both parent identity-switch capabilities effective and
no-new-privileges. The actual restricted snapshot's identity/capability/source
checks passed. Ordinary snapshot data was discarded in RAM. No signing/recovery
key, installed job rerun/change, timer change, backup creation, model request or
memory write occurred. This supersedes the failed launcher candidates; preserve
manual encrypted recovery evidence and do not repeat either successful check.

The new upgrade_profile_schedule.py accepts only the exact qualified public
three-source bundle. It refuses unknown old runner/units, drop-ins, wrong unit
paths, active jobs or an active/enabled timer. It serializes operator updates,
creates a protected runner edition, validates units, preserves old public files
privately and atomically replaces only the service after rechecking originals.
It leaves all profiles, old runners/generations and the database schedule intact.
An interrupted/conflicting run is preserved for review, never automatically
retried, cleaned or rolled back.

Actual service start must yield a new successful invocation, whose bounded
journal contains one valid encryption-only completed report. Root independently
verifies that generation's ciphertext, signed manifest and counts using only
backup.json. The recovery identity is never opened and no decryption occurs.
Only then can timer enable occur; active/enabled/next-run checks are required.
A later enable-stage failure can leave partial timer state, which is reported
without a false rollback claim. Persistent timers can run catch-up generations.
The operator command remains unexecuted here; installed success, Windows
collection, full runtime qualification and fleet activation remain unclaimed.

Workspace validation: 1078 focused tests pass, zero failures/skips and no
reported pytest warnings. The 37 new upgrade cases cover exact historical and
qualified-candidate hashes, source tampering, active/enabled/overridden jobs,
file drift, validation/start/result/report/signature failures, fresh invocation
binding, staged file preservation, real HMAC/ciphertext tampering and permission/
symlink/hardlink guards. Native age recovery and systemd unit syntax tests in
the existing suite still pass. Root metadata/host systemctl actions are simulated
here; the actual installed upgrade/backup/timer result must come from the owner.

## 23 October: guarded service replacement completed; backup qualification incomplete

Owner-run ab8c990b105d2ab3bb234f53d62f11b1d6120d35 returned complete=false at
real_encrypted_backup_qualification with service_replaced=true and
timer_enable_command_completed=false. Original public files were preserved at
/opt/enhanced-cognee-profile-backup/before-upgrade-3facdc095f4b49e6ba6c00b000c7e1e7.
The published candidate runner is a1ffd4c258238847 (177098 bytes); the corrected
service is 923 bytes and the timer file remains the original 213 bytes. The
existing database schedule, model settings and memory records were unchanged.
This returned phase encompasses service start/state, fresh-invocation journal
admission and ciphertext/manifest authentication. It does not identify the
failing subcheck or establish that no backup was created. Do not infer a new
capability defect, rerun the updater or overwrite preserved/installed evidence.

The read-only inspector now has an explicit boolean upgraded mode with fixed
new runner/service hashes and the unchanged timer hash. Original mode remains
available for historical artifacts. It inspects selected unit status/policy,
latest retained invocation and only bounded/sanitized backup reports, adding
message/report counts and the exact success-report contract flag. This can
distinguish a failed service from an absent, duplicated or incomplete completion
report without replaying execution. It reads no signing/recovery configuration,
returns no report paths/private values, makes no API/model request and changes
no files, services, timer or memories. A complete diagnostic is not operational
backup qualification. Actual daily encrypted-job success, timer/collector/fleet
readiness remain open; earlier manual restore and transient passes are retained.

Workspace validation for this continuation: 1096 focused checks pass, zero
failures/skips and no pytest warnings. Eighteen added inspection cases verify
the exact qualified candidate hashes, upgraded read-only command selection,
drift/status/policy/timer reporting, missing/duplicate completed reports,
completion-contract failures and suppression of private paths/values. The
original-mode inspector and guarded upgrade tests remain passing. Root/host
systemctl/journal behavior is simulated here; the returned host result is still
needed and no new installed backup success is claimed.

## 23 October: inspector stopped before retained report; bounded diagnostic repair

Owner-run 6b4453bf3ae3ce74890aa64d5dc35c2401e2e9d0 returned complete=false,
failure_stage=service_state. It reports no file write, service restart, timer
change, credential read or model call. That grouped phase covered two command
reads/decodes and a current-invocation requirement; the result does not identify
the failed operation or establish a new backup failure. No destructive retry,
rollback, model call or configuration change is justified by this diagnostic.

The inspector now splits status read/parse, policy read/parse, invocation
discovery and timer read/parse. Its failure result preserves verified public
artifact flags and any already sanitized state/policy, with allowlisted
exception names, bounded errno/exit status and fixed output-budget/presence
flags. Private exception text/arguments/filenames/stdout/stderr remain excluded.

If current InvocationID is missing/zero, a bounded selected-unit journal read
can discover the latest retained trusted _SYSTEMD_INVOCATION_ID, ignoring ID
claims inside MESSAGE. It is explicitly labeled diagnostic-only; a complete
retained report, including one satisfying the upgrade report shape, is not
proof of a fresh upgraded run or independently authenticated ciphertext. The
helper does not enable the timer, read keys or relax any admission condition.
Systemd v255's unit_may_gc/free paths permit inactive unit collection; this
supports the missing-ID possibility without proving that cause on this host:
https://github.com/systemd/systemd/blob/v255/src/core/unit.c

The helper input budget is deliberately raised to 24576 bytes in the new pinned
bootstrap; old commands/hashes remain historical. The installed runner/service,
originals, backups, profiles and previous passing tests remain unchanged. Actual
encrypted-job/timer qualification, Windows coverage and fleet rollout stay open.

Workspace validation: 1121 focused tests pass, zero failures/skips and no
reported pytest warnings. Twenty-five new cases cover private exception/argument
suppression, bounded command failures, partial state on status/policy read/decode
errors, missing-ID journal fallback, trusted-metadata selection versus MESSAGE
spoofing, no-ID/malformed/oversized journal refusal and diagnostic-only labeling.
All original/upgraded inspector and guarded updater tests still pass. Host
systemctl/journal effects remain simulated here; no installed backup or timer
success is inferred from this source suite.

## 23 October: retained completion found; guarded timer continuation prepared

Owner-run 3b456aeb42fba557c311eba1269e7df79846ea8b returns complete=true:
all candidate runner/service/timer hash flags and selected protection flags pass,
state reports success/0/inactive, timer inactive/disabled. Fifteen matching
retained messages contain one completed encryption-only report for 60 files/
205571 bytes; no decryption, recovery-key read, plaintext archive, model or memory
write was reported. No usable current invocation ID was present; journal fallback
is diagnostic-only and retained_report_proves_upgraded_run=false is retained.
No operator ciphertext authentication or upgraded-run freshness is inferred yet.

A new main_resume entry accepts only the exact qualified three-source bundle,
verifies stable installed candidate and private preserved originals, takes the
existing upgrade lock and refuses active/enabled/overridden schedules. It never
calls the original updater or manually starts a service/backup. Bounded retained
journal admission requires latest trusted unit invocation, root UID, exact
protected runner command line and timestamp after service-file publication.
MESSAGE fields cannot claim identity. Root then verifies ciphertext/HMAC/counts
and signed creation time using only backup.json, followed by candidate/schedule
rechecks. Only then may timer enable/active/enabled/next-run checks occur.
Trusted journal field documentation:
https://www.freedesktop.org/software/systemd/man/latest/systemd.journal-fields.html

No installed file is replaced, no recovery identity/decryption/model/private
profile read occurs and previous generations/database schedule stay intact.
Persistent timer enable can trigger an ordinary catch-up generation; no claim
of zero scheduled jobs is made. The new helper bootstrap budget is deliberately
24576 bytes. Failures preserve evidence and report stage/known category plus
binding/authentication/enable flags without raw errors or secrets. The owner-run
continuation is still pending, and no recurring operation/fleet/Windows admission
is claimed. Earlier manual recovery and passing snapshot tests are not replayed.

Workspace validation: 1144 focused tests pass, zero failures/skips and no
reported pytest warnings. Twenty-three new cases cover root/exact-runner/time
journal binding, MESSAGE spoofing, stale/conflicting/duplicate/incomplete reports,
preserved/installed drift and permissions, policy/enabled-timer refusal, signature
failure, signed old/future generation times, post-authentication drift and timer
enable ordering. Resume tests assert no service start/restart/reload or file
replacement. Existing actual HMAC/ciphertext tamper checks and native age/unit
syntax checks pass. Privileged root metadata, journal and systemctl effects in
the new continuation are simulated; installed-host confirmation remains pending.

## 23 October: protected profile ciphertext/timer qualification passed

Owner-run df79510b51b913826886aad61149054f4e972bf8 returns complete=true:
trusted journal binding to exact /opt runner a1ffd4c258238847 and independent
signed ciphertext verification passed for
/var/backups/enhanced-cognee/hermes_profile_20261023T200722Z_93a199ce.tar.age,
60 files/205571 bytes. Daily timer enabled/active/next run passed. No manual
backup, recovery identity read, decryption, model or memory write occurred;
old generations and the database schedule were preserved. Normal persistent
scheduled catch-up is possible. Preserve this pass; no updater/restore replay.

This closes the bounded pilot's installed encrypted-profile-job/timer gate.
It does not establish every future unattended firing, new-generation decryption,
current canonical database generation restore, future full-fleet/SQLite homes,
Windows/remote collection, full runtime or private fleet admission. The prior
manual restore retains its exact tested generation and identity.

Independent source work now extends v12 collection to both recent encrypted
families with strict manifest shape, owner/mode/link/ancestor guards, descriptor
stability, hash/envelope verification and mutation rejection while streaming.
Only ciphertext/sidecars plus explicit aggregate coverage schema 2 are exported;
key/config files are never selected. Signature/decryption remain explicitly
unverified by collection. Read-only verify-only mode returns aggregate JSON.
Unchanged input produces identical tar bytes; no duplicate family entries or
recursive collection occur. A versioned cognee-v2-profiles scope prevents reuse
of old interrupted database-only checkpoints; completed old online runs cannot
be cloud-retried as new coverage. Originals/repositories/generations are kept.

These Windows source changes have not been installed or activated. V12 remains
paused, the existing v11 scheduled task is unchanged and no cloud upload/full
backup was initiated. The next prepared source-side verify-only operator check
is not native Windows admission, real service recovery or remote collection.

Validation for collection source work: 1174 focused checks pass, zero failures/
skips and no reported pytest warnings; 14 real portable Python backup checks
and 59 portable PowerShell checks pass separately with zero failures/skips.
Thirty new collection cases use real age-encrypted fixtures and tar
recovery, deterministic repeated output, required-family freshness/refusal,
strict manifest/private path/link/mode guards and stream mutation rejection.
A real restic producer test commits no snapshot when the profile family is
missing, then restores both families and passes read-data checking once present.
Synthetic ownership is simulated, not evidence of host root permissions. Four
PowerShell coverage cases verify the old-run/cloud-retry gate; PS7 execution/
parsing does not qualify native Windows 5.1, DPAPI, VSS, ACLs or real cloud.
No installed Windows or scheduled-task hashes were changed. The public original
collector is preserved locally under .archive/2026-10-23_profile_collector.

CI source support is also prepared: memory-qualification fetches full history
for existing exact historical artifact tests and obtains restic 0.19.1 using the
existing provenance file's compressed/binary SHA256 pins before collection
producer tests. RNR_RESTIC selects that reviewed executable; a missing tool is
not converted into a skip. The workflow YAML/embedded bootstrap parses and the
local pinned binary hash matches provenance. The explicit engine route passes
all 30 collection tests. This is preparation, not a hosted CI success claim.

## 23 October: source collection inventory passed; Windows files updated

Owner-run ea6f2438 returned complete=true, coverage_schema=2 and eight completed
pairs: six database and two restricted-profile generations. Both required
families and ciphertext hashes passed. No backup/export/file write, credential
read or cloud upload occurred. Signature authenticity/decryption were explicitly
not tested by this keyless inventory. Preserve the passed manual encrypted
restore, owner custody and daily profile timer evidence; do not replay them.

Workspace found a remaining task-admission mismatch: the v12 updater still
required the old cognee scope. It now requires cognee-v2-profiles and the three
home/Windows-D scopes after local and both cloud-folder copies complete. Six
actual extracted-function cases execute in portable/native qualification,
including rejection of legacy, missing-home, offline-only and incomplete runs.

Current focused verification: 30 collector pytest cases, 14 portable Python
backup tests and 65 portable PowerShell checks pass with zero failures/skips;
pytest reports no warnings. These include real encrypted restic restore and
actual age fixtures. The earlier broad 1174-pass source result remains recorded;
it was not rerun or relabeled as a Windows result.

Five reviewed files were placed in C:\Scripts: the v12 launcher, native test,
task-update helper, dual-family collector and v12 guide. Each previous installed
file matched a known Git blob, was preserved before replacement, and each new
copy matches source SHA-256. The local source-verification manifest was refreshed
and its original preserved. No keys/passwords/private settings were read, no
scheduled task was changed, and no backup/upload was started. V12 remains paused.
This session's attempt to invoke Windows PowerShell failed with Exec format
error; therefore no native Windows test or live scheduled-task read is claimed.
The owner must run the updated synthetic qualification from elevated Windows
PowerShell under vince. Real Windows encrypted-service collection/restore,
cloud recovery, full v12 completion and task switching remain separate gates.
