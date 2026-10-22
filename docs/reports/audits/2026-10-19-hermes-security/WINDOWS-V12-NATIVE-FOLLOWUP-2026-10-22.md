# V12 native qualification follow-up and reversible Scripts cleanup

Date: 22 October 2026. Native Windows qualification remains incomplete. This
report records a real failure, its correction and portable regression evidence;
it does not admit v12 for a task switch or declare its Windows checks passed.

## Observed Windows result

The owner ran the installed `Test-WindowsBackup-v12.ps1` through Windows
PowerShell 5.1 from an elevated PowerShell 7 console. It exited 1 at
`new_run_cannot_reuse_old_tagged_snapshot`. The matching retained native summary
contains 16 preceding passed checks and one failed check; subsequent checks were
not executed. There is no successful native v12 receipt.

Preceding passes include native parsing, pinned engine verification, synthetic
DPAPI protection and password-command pipe, VSS backup and unchanged-data reuse.
This was a synthetic qualification run, not a failed real v12 backup or evidence
that an existing v11 generation was damaged.

## Cause and correction

Windows PowerShell 5.1 emits a parsed JSON array as a single pipeline object;
PowerShell 7 normally enumerates it. The qualification's array subexpression
could therefore count an empty result as one item. Similar array handling
existed in the real backup's snapshot lookup and unchanged-home confirmation.

The shared engine now normalizes JSON-array results using capability detection
and explicit item iteration. It preserves zero, one and multiple results, and
rejects malformed/non-array/null-item responses. Both production snapshot lookup
paths and native qualification list comparisons use that shared normalization.
The tag policy remains conjunctive: matching a scope alone cannot admit a
snapshot from a different run. No checks were bypassed or made optional.

References: the [PowerShell project's empty-array compatibility discussion](https://github.com/PowerShell/PowerShell/issues/16548)
and [Microsoft's ConvertFrom-Json NoEnumerate documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/convertfrom-json?view=powershell-7.5#-noenumerate).

## Verification and installation

The portable qualification passed **38 checks, zero failures, zero skips**, using
the real pinned Linux restic engine and PowerShell 7. It includes a regression
fixture that deliberately emits arrays using the legacy non-enumerating
behaviour, plus empty/single/multiple/invalid input cases, real scope/run
selection, checkpoint reuse, recovery integrity, ciphertext copy/resume and
preservation on corruption. This simulation is not a native Windows rerun.

The three corrected installed files are:

- `C:\Scripts\backup-v12\engine.ps1`
- `C:\Scripts\backup-all-wsl-v12.ps1`
- `C:\Scripts\Test-WindowsBackup-v12.ps1`

Their previous bytes were checked against the prior Git revision before
replacement, preserved in the dated archive's `runtime-before` subdirectory,
and the replacements matched the maintained source. Prior failed native
qualification evidence remains available. No task, password, provider settings,
real backup repository or backup generation was changed.

Run this next in Administrator PowerShell as the same Windows owner:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\Test-WindowsBackup-v12.ps1"
Write-Host ("Exit code: " + $LASTEXITCODE)
```

This session still cannot launch Windows executables because Windows interop
is unavailable; no isolation/interop change was made to bypass that boundary.
Review the native result before the first real v12 backup. Required real-scope
backup, cloud/recovery checks and task-switch prerequisites remain separate.

### Second native attempt: recovered-file verifier

The subsequent owner-run test exited 1 at `corrected_recovery`, after 21 passed
checks. The two run/scope selection checks now passed. Inspection of the retained
synthetic recovered file established that `change.txt` actually contains
`after-correction` and has the exact same 16-byte length and SHA256 as the source:
`c6da33132deeddc5fd76d700005759c7045724a4eec26dfb1e384e3a9b7f8948`.
The recovered unchanged binary also matches its source hash.

The Windows restored `change.txt` path is 270 characters long. This exceeds the
legacy 260-character API boundary and is a likely reason the PowerShell 5.1
enumeration missed it; the exact native enumeration result was not captured.
Hidden ancestor traversal is also made explicit by the correction. See
[Microsoft's path-length documentation](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation).
Do not call this evidence of failed ciphertext restoration: the actual restored
contents were independently inspected successfully.

The native fixture now uses a shorter GUID-only leaf while retaining uniqueness,
checks that derived recovery paths fit the older verifier, traverses with
`-Force` and requests restic's `--verify` on both recovery passes. No registry,
global path policy, mount, live repository or scheduled task was changed. The
previous installed native test was preserved under
`C:\Scripts\archive\2026-10-22-native-recovery-verifier` before replacement.
Native Windows rerun remains required; shorter paths do not qualify every
possible long filename or application recovery.

Following this correction, portable qualification passed **40 checks, zero
failures and zero skips**, including two added real restic restore/verify tests
for corrected and older file contents. The selective v11 helper passed
PowerShell parsing and read-only preview; its real Windows extraction remains
an owner-run check because it needs the privately retained archive password.

### Selected-file v11 drill prepared

`C:\Scripts\Test-V11RecoveredFiles.ps1 -OpenFiles` is prepared for normal Windows
PowerShell. It targets only the previously checked base and three explicit small
members: distro inventory, backup command text and the Cognee README. Expected
hashes were read from the retained local v11 staging copies. It creates a new
owner/SYSTEM-protected destination, performs selective extraction, checks all
three hashes, writes a private report and opens only two text files in Notepad.
It never runs recovered code or restores into live projects. Existing recovery
copies remain untouched. Owner-run extraction and readability evidence are
pending; script parsing/preview is not that evidence. No real password is read
or stored by the helper; 7-Zip obtains it through its own hidden prompt.

## C:\Scripts cleanup

Fourteen superseded rollback copies were moved, preserving their bytes, into:

```text
C:\Scripts\archive\2026-10-22-v12-qualification-235801\prior-copies
```

These were `.before...` or `.bak` variants, not the active entry points. Their
536,894 bytes were preserved, so this reduces top-level clutter rather than
claiming a disk-space saving. A local manifest records names, sizes and hashes.
No files were permanently deleted. Current manuals, v11/v12 scripts/support,
installation/review/restore/task helpers and legacy v9/v10 scripts remain.
Retain older entry points until task/reference review and the v12 transition
are complete. Do not infer that every scheduled task was inventoried: native
Task Scheduler enumeration was unavailable in this session.

## D:\Recovery-Test disposition

This directory currently contains the copied v11 encrypted archive and manifest.
Full checksum and owner-run password/integrity tests passed; representative
extraction and application recovery have not been demonstrated. It was left
unchanged. Finish a small recovered-file check before removing the redundant
test copy. Removing it later would reclaim about 47.5 decimal GB / 44.2 GiB;
it must not remove the original generation under `D:\Archive\Snapshots\chains`
or the provider copies. Keep the small verification evidence independently of
any eventual test-copy cleanup. This cleanup does not waive independent
provider-recovery or separate Cognee key-custody requirements.
