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
