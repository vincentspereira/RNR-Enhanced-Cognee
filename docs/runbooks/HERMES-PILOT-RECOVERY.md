# Restricted Hermes profile recovery coverage

Reviewed in Workspace on 23 October 2026. Ubuntu-Hermes operator results are
relayed by the owner; this session has no direct access to that isolated host.

## Current position

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

## Next operator step: read-only inventory

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

Recurring profile backup, completion collection and disposable restoration still
need implementation/installed evidence. This inventory installs no service,
creates no archive/restored directory and performs no cleanup. Full fleet
inventory and staged admission remain in HERMES-REMAINING-ROLLOUT-CHECKLIST.md.
