# Prepare the approved restricted Hermes program snapshot

Prepared 22 October 2026. Continue the existing account/profile approval in
HERMES-LIVE-PROFILE-ACCOUNT-PLAN.md. This is not another Cognee backend, a new
model installation, private-data activation or a replacement for host tests.

## Verified inputs and purpose

The owner-run inspector reported Hermes source
4d04303818b61bf3aa09278af48356315515965b, managed CPython 3.14.7 and selected
dependency generation 1729494fe7834770ba4afd450a636baa under the human account's
private .hermes directory. The environment contains 134 installed-distribution
metadata directories and three .pth startup hooks. Reported program sizes sum
to about 1.4 GiB; retaining the exported source archive adds about 0.2 GiB.
These are size estimates from the inspection, not a new installation receipt.

The new account cannot borrow private-home paths through broad ACL grants.
Prepare one root-owned snapshot that can later supply protected program files
for admitted runtime identities. Per-profile state/credentials remain separate.
There is no need for a maintained Hermes fork or a full program copy per bot.

## Reviewed preparation helper

integrations/hermes/deployment/prepare_restricted_runtime.py:

- Requires the Ubuntu-Hermes human operator through sudo and the already created
  hermes-runtime account. It refuses changed source/selection/startup hashes.
- Exports committed source through Git running as the human operator, with no
  inherited credentials or root Git execution. Existing checkout files, dirty
  work, private instructions, profile trees and model weights are not exported.
- Copies the inspected Python and dependency program trees into a new protected
  staging directory. It detaches hard links, opens source directories without
  following ancestor symlinks and rejects escaping links, special files and
  privileged file modes. It omits private .env variants, direct_url metadata,
  old bytecode and environment-activation scripts.
- Checks the copied .pth set again, then rebases generated editable-finder AST
  literals and generated launcher paths into the new snapshot. Startup code is
  never executed by the root preparer. Original user files remain unchanged;
  copied originals of changed generated files are retained in private evidence.
- Editable imports can reference a source mirror outside the three inspected
  roots. The corrected helper reconstructs only literal MAPPING/NAMESPACES
  bindings: module names and path suffixes must agree, resolve to files or
  directories inside the exported commit, and describe one source layout.
  It never copies or opens the old mirror. Unexpected tables, missing modules,
  escape links and unrelated home references still stop preparation. This
  preflight runs after source export, before the larger Python/venv copy.
  Copied finder bytes and the finder set must match the preflight originals.
- Generated namespace labels may include hyphens in committed plugin folder
  names. Preserve those entries when backed by committed source directories.
  Omit only namespace references absent from the selected committed copy and
  report counts; do not omit required module bindings or change original files.
  Every old namespace target, including omitted entries, must still match its
  declared suffix, normalized path and single source root. Unknown expressions,
  duplicate keys, traversal and unrelated private references remain errors.
- Uses the source's supported payload/environment metadata and external-update
  steward. The code identity is the actual commit, displayed as git.4d04303;
  no release version or advisory clearance is invented. This is a local operator
  snapshot, not an official packaged Hermes release. Third-party generated
  installation metadata has been rebased; the snapshot hash manifest records
  actual program bytes rather than claiming untouched wheel RECORD hashes.
- Builds a UID-bound launcher with an empty inherited environment and Linux
  no-new-privileges for its future Hermes process. It does not grant sudo/groups,
  copy provider keys, or execute the copied Python/application as root.
- Hashes program files and validates ownership/link confinement, flushes the
  snapshot and atomically publishes without replacing an existing destination.
  Failed/new partial artifacts are retained for review; no cleanup of owner
  files or backup generations occurs. Only Python is provisioned in the copied
  tool-store metadata; other managed tools still need qualification/admission.

Destination:
`/opt/hermes-runtime/releases/4d04303818b6-1729494fe783`

Initial launcher:
`/opt/hermes-runtime/releases/4d04303818b6-1729494fe783/bin/hermes`

## Operator execution

Use one Ubuntu-Hermes deployment operator session. The existing Desktop session
can stay open because this step does not launch Hermes, mutate its current code,
alter profiles or restart services. Avoid updating Hermes during the copy; the
helper rechecks source revision and dependency-selection bytes before publishing.

Obtain the helper through the existing protected Cognee checkout's GitHub remote,
without switching its branch or pulling over working files. Execute an exact
published helper blob using root system Python in isolated, no-site mode after
checking its complete SHA256 against the reviewed file. The source is public
program code; no secret is passed through the pipe. Root needs only the operator's
ordinary local sudo authentication. The guided chat supplies the exact published
commit and checksum; never substitute a moving branch for that checked blob.

Root preserves the verified distro marker explicitly through sudo. The helper
requires --apply; it refuses an existing destination rather than overwrite it.
Allow roughly 2 GB additional storage including source evidence and a few
minutes for copy/hash/flush work. It requires 4 GiB free in the guest filesystem;
this is not a measurement of free Windows host storage. No cloud/model call,
package download, OS restart, existing profile switch or Windows backup is made.

## Result and remaining qualification

### Read-only diagnosis after a link guard stop

The owner reported that preparation stopped with "A program link references
files outside the selected runtime." The snapshot was not reported published;
the helper retains partial staging files and leaves original installations
unchanged. This message can originate from source/Python/environment symlink
relocation or from rebasing an editable-finder path literal. It does not identify
the failing phase, and does not yet establish which reference needs correction.

Run inspect_restricted_runtime.py --links-only as the normal human operator
without sudo, using the exact published blob supplied by the guided chat. This
inspects committed source link blobs, link metadata in the two selected program
trees, and editable-finder AST path literals without executing them. It does not
read external link targets or profiles, copy files, inspect root-only staging,
launch Hermes, call providers, or change the active deployment. External target
paths are classified rather than printed; relative names inside the program
trees are reported. Output is capped at 40 external links and 40 editable paths,
with total counts and explicit truncation flags. Classification follows the
preparer's lexical mapping, not a proof of ultimate link-chain confinement.

Retain the partial staging artifacts and the escaping-link guard. Diagnose the
reported program reference before changing copy/relocation rules; do not blindly
rerun preparation, follow external links into private files, or replace missing
program files with administrator home access. A completed read-only diagnosis
is not successful snapshot preparation or runtime qualification.

The owner subsequently reported complete=true: zero committed source links,
1047 managed-Python links, four environment links and zero external links.
There were 122 editable path references; the first 40 displayed were all outside
the selected runtime in another operator-home area, with truncation explicitly
reported. Do not assert the unseen 82 paths have the same classification or
publish guesses about the hidden original source location. This identifies
editable-path rebasing as the diagnosed blocker rather than symlink relocation.

The corrected preparer uses the exported source layout to reconstruct verified
import bindings instead of adding that other home area to the copy allowlist.
All other copy/publication guards and preservation rules remain. The next native
preparation attempt is still required; local tests do not confirm that every
native binding satisfies the supported layout or that Hermes runs afterward.

Reference: [Hermes packaging at the selected commit](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/setup.py)
derives root Python modules from the source tree. The
[Setuptools editable finder](https://github.com/pypa/setuptools/blob/main/setuptools/command/editable_wheel.py)
uses MAPPING/NAMESPACES to locate modules; that moving upstream template is
structural context, not proof of the exact installed Setuptools version.

### Import-name validation stop

The next native attempt using delivery commit 162beb416 stopped with "An editable
import table has an unsupported module name." This guard includes nonliteral,
nonstandard, duplicate and overlong keys. The message alone does not identify
which case occurred. The committed-source export precedes this check; the large
Python/dependency copy follows it. Retain earlier/new staging artifacts and do
not repeat preparation simply to obtain another ambiguous failure.

Use inspect_restricted_runtime.py --editable-tables without sudo as the normal
Ubuntu-Hermes operator. It parses every generated import-table entry and compares
names to the selected committed Git tree, without executing the finder or
reading its original mapped source locations. It reports name-validation issues,
missing committed modules, suffix mismatches, malformed paths/tables, duplicate
keys, the count of declared source roots and unrelated home-path constants.
Issues display names only when a corresponding path occurs in the committed
source; unknown names and original source roots/paths remain redacted. Counts
include every inspected entry, with detailed issues capped at 40 per finder and
an explicit truncation flag. A root filename containing dots can be public even
when treating the dots as a package hierarchy would produce a suffix mismatch;
the diagnostic reports both interpretations without choosing a relocation rule.

Do not relax the privileged validator until the actual native entry/layout is
known. This diagnostic is additional evidence, not a successful preparation.

### Received namespace layout and no-copy preflight

The completed table audit checked all 122 entries/paths without truncation. It
reported one source root, no unbound home-path constants, and 17 problem entries,
all in NAMESPACES. Seven were backed by committed plugin folders whose names
contain hyphens, such as plugins/hermes-achievements and plugins/model-providers.
Ten had no corresponding path in the selected commit; their identities/origins
remain private and unverified. The audit does not establish that those original
folders are disposable or authorize deleting them.

The corrected helper separates strict Python module names from safe namespace
folder labels. It retains committed namespaces and omits uncommitted namespace
references only from the new generated map. It reports module/namespace counts
and preserves copied originals in restricted operator evidence on preparation.
Missing required modules still fail. A single committed-file catalog, with the
same exclusions, drives both no-copy checks and actual-copy validation; actual
copied paths must also remain confined inside the protected source tree.

Run the exact published prepare_restricted_runtime.py blob with --preflight as
the normal Ubuntu-Hermes operator WITHOUT sudo. This uses system Python in
isolated/no-site mode. It reads Git tree and selected install metadata, parses
finders without executing them, checks startup hashes and source/selection/finder
stability, and creates no files/staging copies. Root execution is refused.
Git under this mode needs no group-changing privileges. It returns sanitized
counts and import_preflight_passed=true only when every binding passes. A changed
revision, selected generation, startup hook or finder fails the check.

This result means only that the corrected import-map logic accepts the current
committed layout. It does not check every copied dependency/link, prove host
permissions or prepare/launch Hermes. snapshot_prepared and runtime_qualified
remain false. After reviewing the native preflight result, use the same checked
helper with --apply through the approved sudo wrapper. Retain earlier partial
copies; no cleanup, existing profile change or private memory activation occurs.

A successful preparation returns snapshot_prepared=true, runtime_qualified=false,
hermes_launched=false, profile_configured=false and memory_connected=false.
Do not change those interpretations to a successful live deployment.

Next, run the new launcher as hermes-runtime, verify UID/groups/no-new-privileges,
imports and protected-file/write denials, and retain private diagnostics if it
fails. Check normal CLI and actual intended Desktop/gateway execution paths.
Prepare the fresh profile, its ordinary scoped Cognee token and controlled renewal,
eight-tool provider, narrow existing model route and explicit profile backup
coverage. Qualify selected capture, fresh-session recall, correction, ambiguity,
secret refusal, scope denial and reviewed sharing before private-data admission.

The owner has reported successful publication of the 36797-file snapshot at the
destination above, with all four launch/profile/memory/qualification flags still
false. Retain it and the earlier staging generations; do not repeat --apply.
For the first startup probe, the human operator uses sudo -H -u hermes-runtime
and /usr/bin/setpriv --no-new-privs before a non-interactive /bin/sh. Change to
/var/lib/hermes-runtime, print id and only CapEff/CapAmb/NoNewPrivs from proc
status, then exec the protected bin/hermes --version. The UID-bound launcher
clears inherited environment/settings before Python loads. This requests version
information, not a chat, gateway or setup session; the running human Desktop can
remain open. Fresh restricted state may be initialized in its own home. Report
the actual exit code and diagnostics; a version success is only a startup check.
The selected source documents --version in
[hermes_cli/main.py](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/hermes_cli/main.py).

The owner has since reported version exit 0 from this protected directory under
uid 993/gid 985, only its primary group, zero CapEff/CapAmb and NoNewPrivs=1.
Python was 3.14.7 and OpenAI SDK 2.24.0. Install method was displayed as unknown;
retain this metadata for the separate external-update-policy check. Basic CLI
startup has passed; no connected profile or complete runtime qualification is
implied. Preparation flags are historical receipts, not live status files.

Next run the exact published check_restricted_access.py blob using system Python
in isolated/no-site mode under sudo -H -u hermes-runtime, setpriv --no-new-privs
and a clean environment, with cwd /var/lib/hermes-runtime. The guided command
checks the blob hash before executing. The human's sudo authentication only
selects the restricted identity; application/probe code never runs as root.
The helper opens selected secret paths with O_RDONLY or O_WRONLY plus
O_NOFOLLOW/O_NONBLOCK and immediately closes any successful descriptor without
reading/writing data. It never uses create/truncate/append flags. It similarly
checks selected program write openings, protected directory metadata/effective
write access and restricted home permissions. Only self-process status data is
read. It emits known paths and status labels, never secret contents. An allowed,
missing or inconclusive result fails the selected checks; retain that evidence.
Even selected_access_checks_passed=true is only selected file-access evidence,
not full live-Hermes, all-profile, admin-socket, model or memory qualification.

The owner subsequently reported selected_access_checks_passed=true for all 14
secret read/write probes, nine program write probes and eleven protected
directory checks. Private home, primary group and confinement checks also passed.
Continue with one fresh profile enhanced-cognee-pilot in the restricted account.
Use the protected launcher as hermes-runtime under no-new-privileges and umask
077. Before invoking profile create, refuse the full target path if it exists
or is a symlink, preserving any collision. Use --no-alias --no-skills and no
clone options. No profile-use/default switch, setup/chat/gateway or provider key
copy is part of this command. The normal upstream profile bootstrap may seed
essential built-in files/skills; do not describe --no-skills as executing no
initialization code. Its result needs native review before provider provisioning.

The selected commit's
[profile parser](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/hermes_cli/subcommands/profile.py)
and [profile implementation](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/hermes_cli/profiles.py)
provide these flags and fresh-profile behavior. Keep the existing sticky default
and human Desktop sessions unchanged. The pilot's ordinary credential and model
route will be configured separately; one pilot is not the final fleet limit.

Vincent has relayed a separate review-only fleet worker/isolation bundle and
directed this Cognee work to continue with priority on conflicts. Keep that
bundle untouched. Use HERMES-FLEET-COORDINATION-HANDOFF-2026-10-22.md for pins,
scope and proposed shared-input reconciliation; no maintenance window has yet
been scheduled. Disjoint pilot preparation remains authorised. Do not deploy,
rebase or overwrite shared fleet integration inputs on the strength of a
review-only bundle or a mere detected hash difference.

The owner has now reported successful enhanced-cognee-pilot creation. Hermes also
reported ffmpeg/node/npm/ripgrep missing or outdated in the protected tool store.
This warning is unresolved; profile creation and Python startup do not qualify
those tools. Use inspect_restricted_runtime.py --managed-tools WITHOUT sudo as
the normal vincentspereira operator to inspect the original four program/tool
records, committed lock pins, entry/bin metadata, links and allocated bytes. It
does not execute tools, inspect profile settings, copy/install files or change
the live human store. Treat matching recorded versions as metadata only. The
snapshot's existing Python facts entry is intentionally incomplete for the
other required tools; do not hide the warning or falsify extra facts entries.
Review the inventory before protected artifact correction and version/permission
qualification. Preserve the already-created pilot; do not repeat profile create.

The fresh profile's generic missing-keys warning is expected before provisioning.
The reviewed launcher clears inherited environment variables and pins the
restricted home; do not transfer all administrator keys to remove that warning.
Configure only a fresh ordinary scoped memory token and the narrow authorised
model route in later steps. Printed setup/chat/gateway shortcuts are not the
protected launcher path and do not supersede --no-alias or the staged workflow.

Other managed tools, native SDK/browser/provider/model checks, source revision
compatibility, remaining credential coverage, advisory/release checks and full
fleet onboarding remain separate. Do not copy entire private .hermes trees,
clear release/security gates, modify the default launcher or start paused v12
backups to make this preparation appear complete.

## Separate generation with the four required tools

The owner has now reported the read-only inventory from delivery revision
36b6f72f: all four original entries are directories, their binaries are present
and executable, their recorded versions match the inspected lock, and no links
leave the original tool store. ffmpeg/node/npm/ripgrep respectively occupy
458809344/237559808/19251200/5828608 allocated bytes (721448960 total, about
688 MiB). None of these binaries was executed. These are metadata observations,
not proof of actual versions, authentic upstream archives or complete runtime
qualification.

The helper's --apply --with-managed-tools mode prepares a NEW release at:

`/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1`

It exports the same committed source and recopies the selected Python/dependency
program files with the existing import/ownership/startup guards, then copies only
the four selected original tool entries. This is a protected local artifact
rebuild, not a runtime/package download or a modification of the original human
installation. Allow approximately 2.5 GiB additional guest storage including
program/evidence files and filesystem overhead; the 4 GiB guest-free guard stays
enforced. Windows host free space is not measured from this isolated operator
step. The earlier protected release, pilot profile, original store, partial
artifacts, backend keys/services and fleet review bundle remain untouched.

Tool admission requires schema 1 records, the exact inspected version/entry,
linux-x64 target, matching committed lock artifact hashes and a well-formed
realized payload digest. Existing tool bytes must match that recorded digest
before preparation. Metadata and tree reads reject symlink ancestors, special
files and privileged file bits; copying detaches hardlinks. Copy/link confinement
uses only the four admitted entries. The clone is checked against the predicted
relocation hash, and source bytes/selection are checked again. No selected tool
or copied application code executes as root. These checks verify consistency
with locally recorded program state; they do not independently reauthenticate
the original publisher or rerun a dependency/advisory audit.

The new schema 1 facts contain real target/artifact identities and fingerprints
of the actual protected payloads, including relocated link text. Only reviewed
program PATH entries are constructed; arbitrary environment keys from the human
facts are not transferred. The selected upstream
[facts reader](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/pm/lock.py)
and [payload digest format](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/pm/store.py)
were checked directly against synthetic directories: four reader/identity/env
cases and four digest cases passed in Workspace. No real tool was executed in
those compatibility checks. The external update steward is preserved.

Execute only the exact published helper bytes, verified by SHA256 INSIDE the
privileged system-Python process before compilation. Use git show through stdin,
not a mutable checked-out helper imported as root. Root's isolated/no-site
interpreter runs only this reviewed stdlib helper. Validate the distro/user and
authenticate sudo first; --with-managed-tools requires --apply. No branch switch,
checkout overwrite, profile recreation, chat, provider/model call or default
launcher change is involved. The guided chat supplies the immutable revision and
helper checksum. A pre-existing tools1 destination is preserved and refused.

Workspace targeted helper suites report 114 passed, zero failures, zero skips
and no reported warnings under Python 3.12.3. This includes 28 new tool-admission
cases, alongside the existing 86. Coverage and the full release suite were not
measured in this delta. Preparation and tool versions are still UNVERIFIED on
Ubuntu-Hermes until the owner runs the published command and supplies its result.
Expected tool receipt flags are source_payload_verified/copy_payload_verified;
tool_version_verified_by_execution, hermes_launched and runtime_qualified remain
false. The existing pilot directory remains present; profile_configured=false
means this builder supplies no provider/model configuration.

After publication, use the NEW launcher's absolute path for restricted-account
startup/version and tool execution checks. Recheck confinement against that new
generation; the earlier access checker selects the old release and does not
qualify the new one. Do not assume the four-tool warning is cleared before the
actual Hermes startup check. Keep the next provider/token/model/selected-memory,
cross-scope, backup and fleet admission tests separate. No native tool repair,
model success or complete Cognee integration has been reported by this change.

Native follow-up: the owner has now successfully prepared the tools1 generation
from the pinned bbfa0eea helper, reporting 43574 program files, all four source/
copy fingerprints verified and originals preserved. The other execution and
integration flags remain false. Do not repeat preparation or recreate the pilot.
The next operator step uses the new generation's absolute bin/hermes path under
hermes-runtime/no-new-privileges for --version, printing only identity and the
three self-process confinement fields. After reviewing actual startup output,
check tool versions/confinement and then configure the selected provider/model
route. Source branch consolidation does not require changing this deployed
Hermes source revision, running the original updater or restarting the distro.

The owner has now reported tools1 startup exit 0 under uid 993/gid 985 with
only its primary group, zero effective/ambient capabilities and NoNewPrivs=1.
The displayed application source, Python 3.14.7 and SDK 2.24.0 agree with the
selected inputs. Record install method unknown rather than inventing a packaged
release identity. Next run just the four copied executables' version flags as
hermes-runtime under no-new-privileges and an empty inherited environment.
Use absolute paths for every executable, especially npm: Node's bin directory
also contains its bundled npm, which is not the separately selected npm 12.0.2.
Put only the selected protected Node directory and /usr/bin:/bin on PATH so the
npm shebang selects the copied Node. Ignore ambient user/global npm config and
disable its network/update/audit/scripts settings for this version-only probe.
ffmpeg takes -version; Node/npm/ripgrep take --version. Do not invoke npm install,
npx, the original human updater, a gateway or a model. Inspect actual output and
exit status before claiming tool versions, PM readiness or complete runtime
qualification. Ordinary version output is public program/build metadata; no
profile file, credential, shell history or full environment dump is requested.

The owner has now reported all four copied executables' version commands exit
zero: ffmpeg n9.0.1-11-ge47273f4d9-20260831, Node v26.7.0, npm 12.0.2 and
ripgrep 15.2.0 (e89fff89ac). Preserve these actual results without modifying the
historical preparation receipt's flags. This proves version-command execution,
not package-manager readiness or a connected model/provider.

Continue with check_restricted_access.py --tools-generation. The mode selects
only the fixed tools1 release, checks the original protected secret paths and
selected new program paths, and adds package facts plus the four resolved tool
targets and all selected ancestors. It refuses escaping or missing links and
checks leaf ownership, privilege/write modes, detached hardlinks and effective
write ACL alongside permission-open denials. The no-argument earlier-generation
behavior remains available; it does not qualify tools1. Neither mode accepts an
arbitrary release path. No secret or program content is read/written and no
create/truncate/append flags are used. Verify the exact published blob's SHA256
in isolated/no-site system Python as the restricted account before compilation;
use cwd /var/lib/hermes-runtime, a clean environment and no-new-privileges.
The guided command fetches public source through the operator checkout, without
switching branches, importing that checkout or running probe/application code
as root. The focused helper suites now pass 130 with zero failures/skips and no
reported warnings; the new mode still awaits native results. No installation,
credential generation, profile recreation, service restart or private-data
activation belongs to this access-only operator step.

The owner has subsequently reported that the tools1 selected-access check
passed: all 14 secret read/write probes, 14 program write/metadata probes and
all selected ancestors passed under the restricted identity. Full runtime and
memory connection qualification remain incomplete. Continue with
[pilot provider installation](HERMES-PILOT-PROVIDER-INSTALLATION.md), reusing
tools1 and the existing pilot. Do not rebuild the runtime or recreate profiles.
