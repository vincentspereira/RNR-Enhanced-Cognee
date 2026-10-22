# First real v12 backup: Workspace inventory follow-up

Date: 22 October 2026. Native synthetic qualification passed 45 checks and
remains valid. The first real normal backup stopped with exit 1 at
`Home inventory failed for Ubuntu-Workspace`. This is not a complete backup.

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
