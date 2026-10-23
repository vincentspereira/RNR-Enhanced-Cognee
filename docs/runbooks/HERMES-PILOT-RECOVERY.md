# Restricted Hermes profile recovery coverage

Reviewed in Workspace on 23 October 2026. Ubuntu-Hermes operator results are
relayed by the owner; this session has no direct access to that isolated host.

## Current position

The owner-run fresh restore at ca2682c6 passed on 23 October: 60 files,
205571 bytes, private permissions, provider binding and scoped access verified,
with live source preserved. Retain both failed and successful destinations.
Recurring profile backup installation/operation and Windows collection remain
separate pending gates; the earlier failure/inspection steps below are history.

The owner tested custody of the encrypted Cognee key package and its password
manager recovery copy. Earlier service database backup/restore evidence remains
valid only for its recorded generation, source, identity and scope. Preserve it.
Manual renewal of the restricted pilot access token now passes at 8fb6fca9,
with expiry 2026-10-24T09:15:06+00:00. No repeat of those successful steps is needed.

The newer /var/lib/hermes-runtime home is outside the original user's home
backup. It contains the pilot profile, private OAuth/access credentials,
retained private generations, test receipts and potentially original workspace
work. A database dump does not include these files. The existing daily database
timer and Windows collector do not establish their backup coverage.

## Read-only inventory: passed; preserve this evidence

Run the published pinned/hash-verified inspect_pilot_recovery.py command from a
normal Ubuntu-Hermes terminal as vincentspereira. Starting in ~ is fine. The
command selects the fixed restricted account and protected tools1 interpreter.
Keep the selected pilot idle while it inspects. Everyday Hermes and bot profiles
can continue. Enter the Linux sudo password privately if requested; no vault
password, browser login or API key is required.

The helper walks the fixed restricted HOME using pinned directory descriptors.
It reports aggregate file counts/sizes, required-file protection flags, known
provider binding, unknown link/special-file counts and SQLite-header/WAL/SHM
candidates. It includes retained credentials/receipts/workspace in the scan;
it does not silently exclude unfamiliar folders. Unknown symlinks are counted,
never followed. Nested mounts, unreadable or changing entries and traversal
budgets prevent a complete scan. Missing/unsafe required-file flags remain
visible for review even if the scan itself completes.

It reads at most 16 bytes per regular source file to identify a SQLite header,
without returning those bytes, decoding credentials or opening a SQLite
connection. This avoids inspection-side WAL/SHM changes. Protected public
provider code is read separately to check known hashes. The age/age-keygen probes
check root-owned regular executable metadata; the tools are not executed.
No private filenames, contents, link targets, hashes of private contents, token
values or raw exception messages appear in the report.

Send only the resulting JSON. complete=true means the bounded scan completed,
not that a backup or recovery succeeded. profile_recovery_qualified=false,
encrypted_profile_backup_created=false and runtime_qualified=false are expected.
Missing protection/binding/tool flags or unknown entries need reconciliation
before designing the actual snapshot; do not loosen permissions or delete data.

## Work after the inventory

Use the measured sizes/database/sidecar/link results to prepare the encrypted
profile/workspace/receipt snapshot. SQLite needs a supported consistent backup;
do not copy live database/WAL files independently or assume a short scan freezes
them. Preserve source state and keep plaintext credentials inside protected
processes or the reviewed private recovery destination. Do not read operator
keys in the ordinary agent process or import agent-owned code as root.

Completed encrypted generations belong under the approved
/var/backups/enhanced-cognee location, with distinct format/names and signed
completion metadata. A future profile format must be admitted explicitly by the
collector; placing a file beside database dumps alone does not make Windows,
OneDrive or Google Drive collect it. V12 and existing Windows schedules remain
unchanged by this work. Do not start an upload to close a documentation gap.

Restore only into a fresh restricted disposable destination, with permissions,
checksums, SQLite integrity and protected provider binding verified before any
use. Do not execute recovered hooks/code, overwrite the live profile, reuse an
expired token by bypassing expiry or turn on every bot from a recovery test.
Qualify scope/access using ordinary credentials and the reviewed renewal path.
Keep database generation consistency and trusted program-artifact rebuild or
recovery as separate checks. Preserve all existing backup generations.

Recurring profile backup and completion collection still need implementation/
installed evidence. A manual snapshot/restore is now prepared as described below;
its installed restore stopped and needs retained-evidence inspection. This inventory installs no service,
creates no archive/restored directory and performs no cleanup. Full fleet
inventory and staged admission remain in HERMES-REMAINING-ROLLOUT-CHECKLIST.md.

## Installed inventory result received on 23 October

At 61c272a767f1383acccd9760d782da8c8e127752, the owner returned a complete
restricted-HOME scan: 104 entries, 43 directories, 60 regular files, 205571
logical bytes, largest file 38499 bytes and one expected provider link. No
SQLite-header/WAL/SHM candidates, unknown links, sockets/special files, hardlinks,
nested mounts, unreadable or changing entries were observed. All four required
private-file flags and all three receipt flags passed, as did protected provider
payload and age/age-keygen metadata checks. No backup or restore happened in
that inspection. Do not repeat it as a separate operator step.

## Next operator step: encrypted snapshot and disposable restore

Use the new pinned/hash-verified three-file bundle: the unchanged issuer file
for protected-file/loopback helpers, the unchanged inventory file for fixed
identity/provider checks, and backup_pilot_profile.py. Root executes reviewed
standard-library definitions only; it never imports code from the writable
checkout or walks/extracts the agent-owned source tree. A clean restricted
child reads that fixed HOME, holding the existing renewal lock while producing
a bounded in-memory tar snapshot. Required private files and receipts must be
present/private and the only link must be the reviewed provider binding.

This finite file-only method is based on the installed inventory. It refuses
SQLite/WAL/SHM files rather than making an inconsistent copy; any future database
requires a supported database snapshot implementation. It also refuses unknown
links, hardlinks, special files, changed source state, over 2048 entries or over
16 MiB of file data. No unfamiliar source folder is silently excluded. Source
bytes, modes and directory membership are checked again; keep the pilot idle.

Root encrypts the in-memory archive using the existing public age recipient,
records an HMAC-signed completion manifest using the existing protected backup
signing key, then verifies the signature/ciphertext and decrypts with the existing
protected recovery identity. These keys stay in root processes and are not
passed to the restricted child. A plaintext archive is never written to disk.
The manifest's format is hermes-home-tar+age; private source filenames and
hashes stay inside encryption. Completed files are root-owned mode 0600 at:

```text
/var/backups/enhanced-cognee/hermes_profile_<UTC>_<id>.tar.age
/var/backups/enhanced-cognee/hermes_profile_<UTC>_<id>.tar.age.json
```

A fresh private recovery copy is created outside the source home at:

```text
/var/lib/hermes-runtime-recovery/check-<generation>/home/
```

The root-controlled parent permits traversal but no listing/write by ordinary
users. The generation belongs to hermes-runtime with mode 0700; recovered
directories are 0700 and files 0600. Original source modes remain in the encrypted
manifest for reviewed recovery, but recovered files are not made executable.
No prior folder or file is overwritten. The copy includes credential files;
retain its private permissions and use the authorised operator for inspection.
No recovery copy or existing backup generation is automatically deleted.

The restricted child validates exact archive membership, hashes, safe paths and
parent types without extractall, writes only in the fresh destination, rereads
all recovered files, checks provider link/settings against the protected
artifact, then uses the recovered ordinary token for one local API status check.
The live source is compared again afterward. No recovered hook or program is
executed and no recovered Hermes chat/model is launched. An expired recovered
token is refused; this check does not renew it or weaken expiry.

Expect complete=true/stage profile_backup_restore, verified signature,
decryption, files/private permissions, provider binding and scoped API status,
with live_source_preserved=true and runtime_qualified=false. Relay only the
sanitized JSON. If the command stops, preserve all evidence and send its result
before retrying. A completed encrypted generation or partial private recovery
may already exist after a later failure. No rollback or automatic cleanup runs.

This is a manual pilot snapshot/recovery qualification. It does not install a
recurring profile backup, update Windows collection, upload a cloud copy, restore
a PostgreSQL generation, prove a fresh-machine program rebuild or admit the
fleet. The existing database timer, v11 task and paused v12 remain unchanged.
Owner recovery custody is reused; no new password or key rotation is needed.

## 23 October restore stop: preserve and inspect existing evidence

The owner ran b53b32326f0376171946c983211dde3682da1f78. It reported an
encrypted generation at:

```text
/var/backups/enhanced-cognee/hermes_profile_20261023T104510Z_419749ed.tar.age
/var/lib/hermes-runtime-recovery/check-419749ed55f9406785961263f74b1304
```

The second path is the retained disposable destination. The report stopped at
`disposable_restore`; it does not establish successful extraction, restored
file integrity or recovered access. Preserve both paths and the signed sidecar.
Do not rerun the original full backup command or overwrite the destination.

Workspace reproduced a defect in the recovery path checker: O_RDONLY on every
ancestor requires directory listing permission, but the intentionally protected
root-owned 0711 recovery parent grants the runtime only traversal permission.
The old checker fails on an equivalent real traversal-only parent. The corrected
checker uses O_PATH for pinned ancestors, still checks ownership, rejects
writable ancestors, symlinks and traversal, and opens only the final directory
for reading. Parent permissions are not relaxed. A real filesystem regression
also restores and verifies synthetic files through that unlistable parent.
This is a reproduced possible cause, not yet the installed failure diagnosis.

The next published operator bundle calls `main(..., inspect_existing=True)`.
It selects ONLY the fixed generation/destination above. Root revalidates the
signed manifest, ciphertext hash and protected recovery identity, decrypts in
memory, and sends only the authenticated archive to the clean restricted child.
It creates no directory, archive or manifest and never re-extracts or repairs
retained files. The restricted child validates archive paths/membership/hashes,
compares the current live snapshot, and reads the existing recovery copy. A
partial/empty copy stops with a fixed membership category. If all recovered
files pass it checks settings/provider binding and recovered ordinary scoped
API access. No model, OAuth login/refresh, memory write, upload, cleanup, timer
change or live profile activation occurs. Filesystem reads may update access
times according to host mount policy; contents and permissions are not changed.

Failure details are an allowlisted phase/category and boolean/null checks,
with an optional numeric HTTP status. Arbitrary exception text, filenames,
content, credentials and private hashes are suppressed. A missing/expired
recovered token is not silently renewed. A live-source mismatch is reported
without overwriting either historical backup or newer live state; preservation
checks still compare the live source before/after this inspection.

Run the new pinned/hash-verified bundle in a normal Ubuntu-Hermes terminal as
vincentspereira, starting in ~ if preferred. Keep only the restricted pilot idle;
main Hermes and other bots can continue. Authenticate sudo privately if asked.
Send only the JSON, including a failure report. Inspection success still is not
a fresh restore, recurring backup, Windows collection or full runtime admission.
If the retained copy is incomplete, the next step will use the authenticated
existing archive and a fresh private destination, preserving the failed one.

## Retained inspection result and fresh restore from the existing generation

The owner ran 6a7c5ee4ee936a4913700d2d659c11ef4e551067. Signed ciphertext
verification passed; restricted archive validation and exact comparison with the
live source both passed. Existing recovered membership did not match the archive
(`restore_verify` / `restored_membership_mismatch`). This does not identify which
entries are missing or extra. Recovered settings and API status were not reached.
The inspection reported no file or memory writes and no model call. Preserve
that report and both original paths; installed profile recovery is still open.

The next bundle calls `main(..., restore_existing=True)`. It reauthenticates and
decrypts ONLY the existing fixed generation. It creates one new random check-*
leaf under the existing protected recovery parent; it never reuses the failed
leaf, replaces files, changes source settings or writes a new backup/manifest.
Root-only signing/recovery keys remain outside the restricted process. The
restricted child validates the archive and current source equality before
extracting, checks every copied file and its private permissions, validates the
protected provider binding/settings, checks recovered ordinary API access, and
compares the live source again. Unknown/changed source state, archive problems,
collisions and wrong parent permissions stop the command without cleanup.

Keep the restricted pilot idle. Run the published pinned/hash-verified command
in a normal Ubuntu-Hermes terminal as vincentspereira, starting at ~ if preferred.
Only the Linux sudo password may be requested privately. No OAuth login, model
call, credential renewal, memory write, service restart, upload, timer change or
cleanup occurs. Restored private credential files remain only under the new
0700 generation; they are not activated as a live profile. An expired restored
token remains refused; the test does not bypass or silently renew its expiry.

Expect stage `profile_restore_existing`, reused_existing_encrypted_backup=true,
encrypted_backup_created=false and verified copied-file/provider/scoped-access
flags. A failure report retains the attempted new path and sanitized child
phase/checks when available. Relay either JSON result before another attempt.
A pass qualifies this manual file-only generation restore; it does not establish
recurring backup/collection, a PostgreSQL restore, native restored Hermes startup,
fresh-machine program rebuild, full release qualification or fleet admission.


## Owner-run fresh restore: passed on 23 October

The owner ran ca2682c6af3d0c40855e795a1dca9c778629184e and returned
complete=true/stage profile_restore_existing. It reused the original signed
encrypted generation, authenticated/decrypted it and restored all 60 files
(205571 bytes) at:

```text
/var/lib/hermes-runtime-recovery/check-22bf4ef6ac48438ebc4970fabe2ae8a5
```

Copied file content/private permissions, protected provider binding and scoped
ordinary API access passed. Live source was preserved, the failed destination
was not reused, and no plaintext archive, model call or memory write occurred.
This qualifies that manual generation's file recovery. It did not launch
restored Hermes or install recurring backup/Windows coverage. Preserve the
successful and failed copies until a separately approved cleanup.

## Prepared daily encrypted profile backup

The next reviewed operator bundle calls install_schedule, requiring the human
operator, root authentication and host PID 1 systemd. No distro restart or
runtime reinstall is requested. It refuses existing profile schedule files or
loaded units rather than overwriting them. It installs a content-addressed,
root-owned runner containing only the three hash-verified public sources under
/opt/enhanced-cognee-profile-backup. No writable-checkout import or private key
is embedded. Main/system model defaults and all live profiles remain unchanged.

The new enhanced-cognee-profile-backup.service performs a backup-only run. Root
reads the protected backup configuration, encrypts the restricted child's bounded
in-memory file snapshot with the public recipient, signs completion metadata
and authenticates the resulting ciphertext. It does not read the age recovery
identity, decrypt, make a disposable restore, connect to a model/API or write
memories. The root service's network is disabled and its recovery/operator/API/
worker key files are inaccessible. Persistent writes are limited to the approved backup destination; a private
temporary directory is available and the restricted HOME is read-only. CAP_SETUID/CAP_SETGID
permit the ordinary child identity with no extra groups/capabilities. No other
service or database timer is modified.

The installer validates the two new units, starts the backup service once,
requires its successful exit, then enables the separate daily persistent timer
with up to 15 minutes of randomized delay. It verifies timer enabled/active state and a scheduled next run. This first installed run and timer state still require an owner result.
A persistent timer runs only while WSL/systemd is running; it catches a missed
scheduled event when the distro next starts, not while the laptop is off.

The bounded file-only method still refuses SQLite/WAL/SHM, unknown links,
changing source state and budget overruns rather than recording a false success.
Keep the pilot idle for initial qualification. Concurrent writers outside the
shared renewal lock can make a later run fail; successful operation under a
busy fleet and consistent database capture require their own implementation.
Each successful scheduled run retains a distinct encrypted generation; there
is no deletion/retention cleanup. This is daily recovery coverage, not file-level
cloud deduplication. Existing Windows/restic deduplication remains separate.

If installation or its first run fails, preserve files/logs and relay only the
sanitized report before retrying. A partial install is not automatically rolled
back. The existing database timer remains unchanged. To pause this new timer
using an authorized operator terminal, use sudo systemctl disable --now
enhanced-cognee-profile-backup.timer; this retains units, runner and backups.
Disabling the timer does not interrupt an already running backup; let it finish.
No Windows collector, scheduled Windows task, v12 resumption or cloud upload is
performed. The new hermes-home-tar+age format still needs explicit collection
and remote recovery qualification before any off-machine coverage claim.

## Daily job first run: failed; preserve installed evidence

Owner-run d7c7880c692f9c90c1a4c84974835abf0fcb3e3a published the new service
files and protected runner at:

```text
/opt/enhanced-cognee-profile-backup/57b8a79716f67331/run.py
```

The first service run failed (Result=exit-code, ExecMainStatus=1,
ActiveState=failed) at service_qualification. The timer-enable command was not
completed. Existing database scheduling was unchanged. No model call occurred.
This is not a working installed recurring backup; the earlier manual recovery
pass remains valid. Do not repeat install_schedule, restart the job, remove
files, weaken permissions or enable the timer to bypass this failed gate.

The next pinned/hash-verified inspect_profile_schedule.py step is read-only.
It validates the fixed public runner/service/timer against their exact published
bytes and reports effective protection flags. It reads only the failed service's
retained invocation using systemctl/journalctl. The parser accepts a bounded
whole or split JSON backup report and returns only allowlisted phase/category,
booleans and counts. Arbitrary message/exception text, source content, credential
values, private paths and raw logs are never emitted. No credential file is
opened and no service, timer, file, memory or model operation is started/changed.
Filesystem/journal reads may update access metadata according to host policy.

Run that diagnostic in a normal Ubuntu-Hermes operator terminal as
vincentspereira and authenticate sudo privately. Relay only the resulting JSON.
complete=true here means the diagnostic ran, not that the failed job succeeded.
If the journal lacks an accepted retained report, that absence is explicit;
it does not establish a cause or authorize a repeat. Apply a correction only
after reconciling the retained failure stage and effective configuration.

## Retained job inspection: launch-stage failure, no backup created

Owner-run 3bd4bf8f38565dc272d0ab02a14ab679a3b93137 completed the read-only
inspection. Exact published runner/service/timer hashes and selected effective
protections passed, with no service drop-ins. The retained backup-only report
stopped at restricted_snapshot with encrypted_backup_created=false. No child
report was retained. Timer active/enabled were both false. No files, credentials,
models or memory were touched by that inspection. This rules out observed
public-artifact drift; it does not identify the underlying launch exception.

The next probe verifies the same fixed public runner, parses only its literal
source table and validates all three pinned source hashes. It never executes the
installed runner's main entry point. A unique collected transient systemd unit
uses the same identity-switching/process/network/home protections, with stricter
persistent filesystem access: it has no backup write exception. Environment
expansion of the public program argument is disabled. The temporary unit gets
no service backup/signing/recovery configuration or keys and never changes the
installed job, timer, runner, profiles or backup generations.

Within that temporary boundary, the reviewed parent observes the existing
restricted snapshot launcher. It returns only launch flags, known exception
types and bounded numeric errors/statuses. Any successful ordinary profile
snapshot (including its ordinary credentials) stays in memory and is discarded;
no archive/manifest/file is created, no root key is read and no model/memory/API
request occurs. Raw stdout/stderr/paths/tracebacks are never relayed. This is a
new finite launch diagnostic, not a repeat of manual recovery or the failed
installed backup job. WSL/systemd may retain normal transient-unit journal
metadata; no existing logs or files are removed.

Run the pinned/hash-verified probe in the normal Ubuntu-Hermes operator terminal
as vincentspereira, with the restricted pilot idle; other Hermes sessions/bots
can continue. Authenticate sudo privately and relay only its JSON. A completed
diagnostic can describe a failed launch; it does not qualify recurring backups
or authorize weakening the installed service. Preserve the disabled timer and
existing manual recovery evidence until the concrete cause is reconciled.

## Launch probe result: EPERM; external identity launcher candidate

Owner-run 058b71da8b6542ee528d6d24fd1ea3cf24f410f1 returned an observed
PermissionError with errno 1 during the Python subprocess launch. The launch
attempt did not return a child result or child stderr/receipt. No snapshot or
backup completed, root signing/recovery keys were not read and original units/
timer remained unchanged. This establishes a refused launch, not the exact
failed kernel call; errno 1 alone does not prove which policy caused it.

The candidate scheduled launcher delegates the same positive non-root UID/GID,
empty supplementary groups and no-new-privileges transition to /usr/bin/setpriv.
Python creates the process without pre-exec user/group arguments; the external
launcher changes identity before executing the same clean restricted program.
All original child identity/capability/provider/source guards stay enforced.
Manual operator recovery paths retain their previously tested launcher. No
additional capability, group, namespace access, writable path or relaxed service
setting is introduced. Source bundle serialization is also made deterministic
across dictionary insertion order for stable future protected runner identities.

The next pinned probe verifies the same old public runner/source table and tests
this external transition inside a fresh collected transient unit with the same
selected protections and no backup write exception. It reports parent identity-
switch capability/no-new-privileges flags, bounded launch errors and an allowlisted
setpriv failure operation if present. A successful ordinary profile snapshot
stays in RAM and is discarded. It reads no service signing/recovery configuration,
creates no backup and does not replace/rerun the installed service or enable its
timer. Keep the pilot idle and relay only its JSON. The installed job remains
failed/disabled until this candidate passes and a separately guarded upgrade
qualifies an actual backup run. Do not repeat the initial installer.
