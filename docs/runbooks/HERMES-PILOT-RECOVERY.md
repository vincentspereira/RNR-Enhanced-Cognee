# Restricted Hermes profile recovery coverage

Reviewed in Workspace on 23 October 2026. Ubuntu-Hermes operator results are
relayed by the owner; this session has no direct access to that isolated host.

## Current position

The 23 October manual profile run created an encrypted generation but stopped
during disposable restore. Preserve both outputs; use the fixed-generation
read-only inspection described at the end of this runbook before retrying.

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
