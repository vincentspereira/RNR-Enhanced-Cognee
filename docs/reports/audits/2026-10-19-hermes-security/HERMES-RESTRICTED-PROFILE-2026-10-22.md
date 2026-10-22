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
