# First real v12 backup: Workspace inventory follow-up

Superseding follow-up: [home capture correction](WINDOWS-V12-HOME-CAPTURE-2026-10-22.md).
The 48-check pass remains historical after the next real run exposed null
capture options. The installed correction passes 55 portable checks and needs
fresh native qualification. V12 is paused for guided owner custody/credential
review; do not execute the older resume command below yet.

Date: 22 October 2026. Current result: the WSL launcher correction passed
48 native Windows checks, zero failures/skips, exit 0. All 15 installed hashes
match the receipt. See [current qualification](WINDOWS-V12-NATIVE-PASS-2026-10-22.md).
Resume the normal backup without -NewRun; no new qualification run is required.

The first real normal backup stopped with exit 1 at
`Home inventory failed for Ubuntu-Workspace`. Its partial checkpoint remains
preserved. The investigation and earlier qualification requirements below are
historical; the first real backup still needs to complete.

## Confirmed retained progress

The private checkpoint for run `20261022T011910Z-65be90bc` has only `cognee`
in its completed scopes, `local_complete=false`, no cloud results and
`export_distros=false`. Encrypted repository initialization and the Cognee
scope completed. Preserve that run and repository; a normal retry can reuse
its committed Cognee scope. No Linux home or Windows/D: scope is admitted as
complete. No full backup or cloud upload completed in this attempt.

The main script did not retain the inventory subprocess's stdout/stderr because
its process helper was called without a log prefix. The generic error alone
does not identify whether the failure was WSL launch, system package inventory,
home traversal, permissions, a transient file change or another condition.

## Read-only investigation

In the current Ubuntu-Workspace session, the package recovery inventory passed
(packages, pip and native npm OK; no user crontab). The complete home metadata
fingerprint scan also passed in 140.2 seconds. The exact encoded helper invocation
using `/usr/bin/python3 -I -c ... --inventory-only` from `/` subsequently passed
in 86.7 seconds. Its raw output/error is retained privately, not published.
These checks do not reproduce the Windows-launch failure and do not establish
its cause. No environment settings, permissions, isolation or mounts changed.

## Windows diagnostic without invalidating qualification

Installed `C:\Scripts\Diagnose-V12HomeInventory.ps1` runs the existing qualified
helper through the same Windows WSL command and retains stdout/stderr under a
new owner/SYSTEM-protected private diagnostics directory. It first checks the
native pass receipt and all qualified file hashes. Only the small result and
private evidence location are printed; raw diagnostics should not be pasted
into chat. No backup, cloud copy, provider call or task change is started.

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\Diagnose-V12HomeInventory.ps1" -Distro "Ubuntu-Workspace"
Write-Host ("Exit code: " + $LASTEXITCODE)
```

Normal PowerShell under the backup owner is sufficient; the existing owner
administrator window also works. It may take several minutes to inventory a
large home. Parsing and read-only preview passed locally. The owner Windows
execution and detailed error evidence are pending.

All 15 previously qualified file hashes still match the installed files. The
new diagnostic is a separate tool, not a modification to the qualified runtime;
no native qualification rerun is required for this addition. The scheduled task
remains v11. Do not reset the repository/checkpoint, use NewRun, weaken inventory
failures or claim the real backup passed while investigating.

## Captured Windows error and launcher correction

The owner-run diagnostic returned `inventory_exit=127`; its protected stderr
contains `/bin/bash: line 1: -d: command not found`. Python never reached the
inventory: the WSL launcher treated the quoted distro-selection flag as a Linux
command. The direct process serializer quoted every token, including `-d`,
while the working Cognee stream is launched by restic's own process handling.
This explains why the separate Linux inventory succeeded and the Cognee scope
could complete. [Microsoft documents the WSL launcher's command-line parsing
role](https://github.com/microsoft/WSL/blob/master/doc/docs/technical-documentation/wsl.exe.md).

The shared process helper now leaves only a conservative set of safe WSL
tokens bare. Python payloads, spaces, quotes and empty values remain escaped;
ordinary executables and password-command construction retain their previous
quoting. Before/after home-inventory stdout/stderr now have private run-log
prefixes, so a later failure retains diagnostics without console disclosure.
No restart, mount, interop setting, package install or permissions change was
used to address the launcher defect.

Portable verification passed **52 checks, zero failures, zero skips**, including
WSL command-line serialization and a real subprocess argument roundtrip through
the WSL-specific branch. That Linux proxy is not a native WSL parser test. The
native suite now includes an actual Windows-to-Ubuntu-Workspace Python probe,
with a helper-sized encoded payload, owner/cwd checks and synthetic arguments.
It starts no backup/model and reads no home contents. A fresh native pass must
validate this path before the real retry.

Three corrected installed files (engine, main backup and native test) match
maintained source; their originals are under
`C:\Scripts\archive\2026-10-22-wsl-launcher-fix`. The prior native receipt was
preserved as historical evidence. Its three changed file hashes correctly
prevent reuse until the new native suite passes. The completed Cognee checkpoint
is byte-for-byte unchanged; no repository or backup generation was removed.

Next action in Administrator PowerShell as the same owner:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\Test-WindowsBackup-v12.ps1"
Write-Host ("Exit code: " + $LASTEXITCODE)
```

After a verified native pass, retry the normal v12 command without NewRun so it
can reuse the completed Cognee scope. First real home/Windows capture, provider
upload/recovery and task transition remain pending.
