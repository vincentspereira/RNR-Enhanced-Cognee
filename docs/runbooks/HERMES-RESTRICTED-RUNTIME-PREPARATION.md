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

Other managed tools, native SDK/browser/provider/model checks, source revision
compatibility, remaining credential coverage, advisory/release checks and full
fleet onboarding remain separate. Do not copy entire private .hermes trees,
clear release/security gates, modify the default launcher or start paused v12
backups to make this preparation appear complete.
