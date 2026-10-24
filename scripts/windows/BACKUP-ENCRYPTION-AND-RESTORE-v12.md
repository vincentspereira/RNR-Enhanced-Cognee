# Backup v12 - operating and recovery guide

Current checkpoint, 23 October: Ubuntu-Hermes source-side collection inventory
passes for six database and two restricted-profile encrypted backup pairs.
The v12 collector requires both recent families and verifies ciphertext hashes;
it does not read keys, authenticate signatures or decrypt. The checkpoint and
task-switch guards require the new cognee-v2-profiles scope, preventing reuse of
old database-only success as profile coverage. V12 remains paused; the v11
scheduled task must stay unchanged. Owner-run native Windows qualification of
the updated files is the next step. This synthetic test does not run a full
backup, copy real data to the cloud or switch the task. Actual collection,
downloaded recovery and the real v12 backup remain separate unfinished checks.

Earlier operating/status paragraphs below are dated history. Instructions to
resume a backup or switch its task do not override the current pause.

Current follow-up, 22 October: the real run passed inventory but stopped at
home capture because a null options array became an empty command argument.
The correction is installed and passes 55 portable checks, zero failures/skips.
The earlier 48-check native pass applies to the prior files. A fresh native
pass is required for the correction, including restic-to-WSL producer checks.
The owner has paused v12 while completing Cognee recovery-key custody and
credential review. Do not start a backup or switch the task from this update.
The older qualification and resume instructions below are historical.

Updated 22 October 2026. The corrected launcher passed 48 native Windows checks,
with zero failures/skips and exit code 0, including the actual Windows-to-WSL
launch probe. All 15 qualified file hashes match the installed version.
The first real v12 backup must now resume and complete, followed by recovery
review. V11 generations remain available.
The scheduled task still uses v11; nothing starts or switches it automatically.
Preserve the incomplete run; the completed Cognee scope can be reused on retry.

## What changed and why

V12 uses restic 0.19.1, a free, open-source encrypted backup tool. One complete
first backup is necessary. Later backups reuse stored content blocks and save
only new/changed content plus small recovery metadata. Every recovery point
describes its own complete selected scope; you do not manually stack differences.
Repeated content can share stored blocks even between different original files.

The existing password in KeePassXC's `Windows - Backup archive encryption`
entry is reused. It passes from the Windows-protected file into a private child
pipe. It is never a command-line password, plaintext password file or uploaded
DPAPI-only recovery method. Keep your written vault passphrase separately.
The repository password is needed to recover; losing it makes recovery impossible.

Local repository: `D:\Archive\Snapshots\restic-v12`.
Cloud copy folders (separate from existing v11 generations):

- `C:\Users\vince\OneDrive\Vincent\WSL_Backups\restic-v12`
- `G:\My Drive\WSL_Backups\restic-v12`

Saved file contents and filenames are encrypted. Some key-envelope metadata,
including machine/account labels, remains readable; secret repository keys
remain encrypted. Existing verified objects
are reused. Interrupted copies resume a matching prefix, verify the completed
object and publish recovery snapshots last. Existing mismatched files are
preserved and stop the copy. Neither old backups nor old recovery points are
automatically deleted. No cloud data is purged or automatically dehydrated.

This saves storage and upload traffic. It does not make checking for changes
free. Linux homes get a metadata inventory first: an entirely unchanged home
can reuse its prior snapshot without streaming again. When a home changes,
its native tar stream is read again; existing data blocks still reuse storage.
If the source changes while it is being collected, the next run captures it
again rather than claiming it is unchanged. File backups are not one atomic
snapshot of every database and every live Linux home at the same instant.

## Included and separate coverage

Included: the Windows owner profile, the isolated worker profile, C:\Scripts,
D:\Vincent except Entertainment, reviewed RNR release/recovery/worker folders,
WSL docs/logs, original AI model-related work products, studio outputs and assets,
review/edit/distribution fixtures, worker sources, worker evidence/fixtures,
and local model metadata/revision/licence information. Normal work product
archives, logs and geometry binaries are retained. Model weight exclusions
are scoped to AI-Models, rather than globally excluding original geometry/data.

All three reviewed Linux user homes are included with Linux filenames, modes
and links preserved. Rebuildable caches/environments are excluded. Hermes'
native database/profile images are merged into the Linux home stream, avoiding
the previous ZIP plus duplicate raw profile mirror. Profiles, custom skills,
plugins, bot configuration, sessions, selected memory and retained per-profile
backup history are included. Generated `.hermes/backups` is excluded to prevent
backing up backups repeatedly. The per-home coverage manifest is inside its tar.
SQLite snapshots use SQLite's backup mechanism; test fixtures retain exact bytes.
Linux recovery manifests also retain local package versions, native global npm
and system-Python pip inventories, owner crontab, OS/isolation and fstab settings.
These contents go into the encrypted tar, not the console. Inventory failures
stop capture; an absent optional tool/empty crontab is recorded honestly.
System-inventory changes also prevent an unchanged-home snapshot from being
reused. Windows registered-program and OS-build metadata travels with the
encrypted Windows snapshot; it is not an inventory of every portable/Store app.

Completed encrypted Cognee service backups from `/var/backups/enhanced-cognee`
are a required separate scope. Ciphertext hashes/freshness are checked. This
does not verify the service manifest signature or prove decryption: recovery
requires the separate Cognee keys and tested service recovery procedure.

Explicit gaps/limits:

- OneDrive personal originals are separate by your choice. V12 does not download
  online-only personal originals. Other online-only cloud files are excluded too.
- Entertainment is excluded by your choice.
- Downloadable model weights and rebuildable installed runtimes/environments are
  excluded; you confirmed no custom/trained weights. Licence/config/revision
  metadata is retained. Download availability/licensing is not guaranteed forever.
- A preserved link records a target; it does not copy external target contents.
- User-home copies are not full WSL images or a Windows operating-system image.
  Live Docker/WSL disks under AppData are excluded rather than copied as if
  they were consistent offline images. Other active VM/application images need
  their own application-consistent recovery procedure.
- System directories such as `/etc`, `/opt`, `/var/lib` are covered by separate
  full WSL exports, not by calling a home backup a whole-distro backup.
- Cloud sync folders are not proof that OneDrive/Google uploaded the objects.
  Their clients and an independent downloaded recovery still need checking.

## First native test - do this first

Allow your current v11 backup to finish. Open Administrator PowerShell as your
usual Windows account. The test uses synthetic data only, no full real backup,
no upload and no scheduled-task changes:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\Test-WindowsBackup-v12.ps1"
Write-Host ("Exit code: " + $LASTEXITCODE)
```

Send the small result and any error, never passwords or recovery keys.
This separately tests Windows PowerShell 5.1 syntax, DPAPI child-pipe unlocking,
VSS backup, unchanged-content reuse, correction/deletion/older-version recovery,
interrupted-copy recovery, recursion rejection and a decrypted copied repository.
The real backup and task-switch helper require this test to pass for the exact
installed backup files. Changed files require a fresh native qualification.

## First real backup and retries

After native qualification passes, run the first backup in elevated PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\backup-all-wsl-v12.ps1" -RequireCogneeBackup
Write-Host ("Exit code: " + $LASTEXITCODE)
```

The first v12 repository needs additional disk/cloud quota; it cannot reuse
encrypted v11 7-Zip blocks. Keep v11 generations until v12 downloaded recovery
is proved. The script refuses overlapping v9/v10/v11/v12 backup processes.
Read the coverage warnings and check that all three homes and Cognee succeeded.

For an interrupted local run, repeat the same command: completed scopes are
reused and unfinished scopes retried. The completed scopes reflect their
original collection times. Use `-NewRun` deliberately if you want a fresh run
instead; prior snapshots/partial data are retained. Interrupted data collection
must not turn a truncated stream into a successful snapshot.

For a completed local backup but interrupted/unavailable cloud copy:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\backup-all-wsl-v12.ps1" -RetryCloudOnly
```

This reuses the completed local recovery points and resumes object copying.
Wait for both sync clients to report completion. An offline internet connection
can leave locally completed cloud copies pending provider upload; the script
reports folder-copy completion, never remote-server completion.

If a power loss left a stale repository lock, first confirm no backup/restic
process is active. Repeat the original command with `-RecoverStaleLock` only
for that recovery. It refuses any running restic process and uses restic's
normal stale-lock check. Never force `unlock --remove-all`, remove lock files
by hand, or write to cloud repository copies with another backup program.

Run a periodic full local integrity read with `-CheckData`. This takes longer
because it reads stored encrypted data. It is separate from quick metadata
checks and the cloud clients' upload status.

## Verify and recover from a downloaded cloud copy

Download the ENTIRE `restic-v12` repository to a separate private recovery
location. It needs `config`, `keys`, `data`, `index` and `snapshots`, with the
directory structure intact; downloading one pack file is not a full backup.
Do not combine objects from different repositories. Do not restore over live
files, profiles, stores or the original repository.

List the downloaded recovery points (Destination must be a new unused path):

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\Restore-Backup-v12.ps1" -Repository "D:\Recovery-Test\Downloaded-restic-v12" -Destination "D:\Recovery-Test\Unused-Listing" -ListSnapshots -PromptForRecoveryPassword
```

Enter the archive password from KeePassXC locally in the hidden prompt. Do not
use the vault master passphrase here. This tests password recovery independent
of the original machine-bound DPAPI file. A restricted encrypted DPAPI test
artifact is retained locally; no plaintext password file is made.

Then fully read and verify that downloaded repository:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\Restore-Backup-v12.ps1" -Repository "D:\Recovery-Test\Downloaded-restic-v12" -Destination "D:\Recovery-Test\Unused-Verify" -VerifyOnly -PromptForRecoveryPassword
```

Choose an explicit snapshot ID from the list for each scope you want to test
(Windows-D, a Linux home, encrypted Cognee, or an offline full distro). Restore:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\Restore-Backup-v12.ps1" -Repository "D:\Recovery-Test\Downloaded-restic-v12" -Destination "D:\Recovery-Test\Restored-Selected-Scope" -Snapshot "REPLACE_WITH_SELECTED_ID" -PromptForRecoveryPassword
```

Open known documents and compare known file hashes. Linux home recovery yields
a tar; extract only into an empty disposable Linux directory, never over your
live home. Confirm representative bot configs, custom skill/plugin files and
database `PRAGMA quick_check` there. Do not start restored bots, login sessions
or providers. Service recovery needs its separate keys/runbook and disposable
database environment. Repeat recovery from Google separately; a OneDrive test
does not qualify Google.

## Separate full WSL recovery images

Full images require an agreed maintenance window with the selected distros
already stopped. This cannot be run from a Codex session inside a selected
distro while claiming it is stopped. The script never stops/restarts a distro
or changes isolation. Normal daily/weekly home backups do not qualify this.

From Windows PowerShell during that window, after all required sessions and
services have been shut down deliberately, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\backup-all-wsl-v12.ps1" -ExportDistros -NewRun
```

It checks stopped status before exporting and streams each full export directly
into encryption. There is no plaintext live ext4.vhdx copy or giant plaintext
staging tar. This offline mode takes full-image scopes plus Windows/D: files;
it does not launch Linux home collectors or the Cognee collector. Service keys
inside a whole distro are therefore protected by the outer archive password.

After recovery, restore the chosen full-distro tar to a private disposable path
and use `wsl --import` with a NEW distro name and NEW empty install directory.
Do not replace/unregister the original distro. Verify isolation and disable
restored agents/timers/network clients before first test startup. A native
offline export plus an isolated full import test remains outstanding.

## Switch the weekly scheduled task only after qualification/recovery

`Update-WSLBackupTask-v12.ps1` previews by default and refuses Apply until exact
native qualification and a real local plus both cloud-folder copies complete.
Review downloaded recovery before switching. Then use its Apply and local
credential prompt; use your Microsoft Windows sign-in password, not your PIN,
vault passphrase or backup password. Schedule, account, logon and overlap settings
are retained, old task XML preserved, and the helper does not start a backup.

No task has been switched by preparing these files. Existing v11 7-Zip archives
still use the v11 recovery guide; v12 restic recovery instructions apply only
to the new restic repositories.

## Tool provenance

- https://github.com/restic/restic/releases/tag/v0.19.1
- https://restic.readthedocs.io/en/stable/040_backup.html
- https://learn.microsoft.com/en-us/windows/wsl/basic-commands

The portable Windows binary and official ZIP SHA256 are pinned in the installer.
Restic is BSD-2-Clause software. No account subscription, paid application, cloud
API credential or machine-wide installation is required. Cloud storage quota
and your existing provider account costs are separate.

## 23 October source change: encrypted profile collection

The separate Cognee scope now includes BOTH memory_*.dump.age database and
hermes_profile_*.tar.age restricted-profile generations, with their completion
manifests. Each family must have a recent valid encrypted generation. Partial,
unsafe, stale or hash-mismatched families stop the producer before a successful
snapshot can be admitted. The collector never selects keys or plaintext; it
does not claim to authenticate signatures or decrypt the inner age files.

Scope cognee-v2-profiles intentionally differs from old scope cognee. An
interrupted older online run can collect the new scope without reusing its old
database-only checkpoint. A completed old online run remains historical; use a
NewRun only after native qualification, preserving earlier snapshots. Retrying
cloud copies cannot retroactively add the missing coverage. Unchanged ciphertext
remains deduplicable; no repository pruning/deletion or automatic task switch is
introduced. --verify-only checks source-side aggregate coverage without export.

These changes are repository source only. V12 remains paused and the qualified
v11 task is unchanged. Requalify the updated Windows hashes/ACL/producer/restore
and actual cloud recovery before using v12 as the scheduled replacement.
