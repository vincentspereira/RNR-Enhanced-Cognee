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
