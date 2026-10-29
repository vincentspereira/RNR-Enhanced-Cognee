# V12 native qualification follow-up and reversible Scripts cleanup

Date: 22 October 2026. Historical failure/correction record. Superseding result:
[native Windows qualification passed](WINDOWS-V12-NATIVE-PASS-2026-10-22.md), 45
passed, zero failures/skips, exit 0, all 15 receipt hashes verified. Earlier
pending statements below describe those attempts. First real backup,
provider/recovery review and task transition remain separate.

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

### Selected-file drill completed; console summary corrected

The owner subsequently ran the drill successfully (exit 0) and confirmed that
both Notepad files opened and were readable. The private saved report contains
`complete=true`, `passed=3`, `failed=0`. Independent inspection confirmed exactly
three selected files plus that report: 154,324 bytes of selected file contents,
155,797 bytes including the original report. Each selected file's SHA256 matches
its retained reference. The larger 7-Zip display figures (121,603 files and
9,089,007,814 bytes) are not the files written in this selective run; the folder
inventory was checked directly. The initial commentary concern about excess
extraction was corrected after that inspection.

The blank console fields came from applying Select-Object to a hashtable
without converting it to PSCustomObject. The saved JSON report was unaffected.
The projection is corrected in both the v11 drill and the v12 native test, with
regression tests executing each actual summary projection. The drill now also
checks the actual extracted file count before saving a pass and prints actual
written bytes. Portable qualification passes **44 checks, zero failures and
zero skips**. Native v12 rerun remains required.

Evidence is retained independently under
`%LOCALAPPDATA%\RNR-Backups\recovery-evidence\v11-2026-10-22`, including the raw
report, matched restore manifest and review recording the owner's readability
confirmation. It does not contain the archive password or recovered documents.
The owner explicitly approved deleting the temporary recovery folder. A fresh
checksum check of the retained original base precedes that cleanup; final
cleanup disposition is recorded below after execution.

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

Full checksum, owner-run password/integrity, three selected-file hashes and both
text-file readability checks have passed. Application/database recovery remains
separate. The owner approved removal of the redundant test copy after preserving
the evidence and verifying the retained original archive. Removing it would
reclaim about 47.5 decimal GB / 44.2 GiB;
it must not remove the original generation under `D:\Archive\Snapshots\chains`
or the provider copies. Keep the small verification evidence independently of
any eventual test-copy cleanup. This cleanup does not waive independent
provider-recovery or separate Cognee key-custody requirements.

Final disposition: the full retained original was re-read (47,503,603,481 bytes,
481.8 seconds); its SHA256 matches
`6fbbc9f4e5105d29e9ab7edd44260edb79a014c8a93202a0b03fb09c2b97f5e8`,
and its size, modification time and inode remained unchanged during the check.
Only the six pre-inventoried temporary files were then removed, followed by
their empty directories and `D:\Recovery-Test` itself. No unexpected files or
links were allowed by the cleanup preflight. Removed logical file bytes total
47,503,759,847 (about 47.5 decimal GB / 44.2 GiB). Cleanup completed successfully;
the original archive still exists and no cloud copy was changed.

The independent evidence directory contains the raw selected-file report,
restore manifest, owner-readability review, original-archive verification and
cleanup journal. The manual's general local restore commands now use the
retained original, so recovery does not require retaining the temporary duplicate.
The specific selective-drill command is marked historical after cleanup.

## Further native attempt: policy-fixture location

The next native run exited 1 at `original_geometry_binary_kept`, with 41 preceding
checks passed. Inspection of its retained summary and full exclusion file
identified that its sample files lived under
`RNR-Backups\v12-state\qualification`, an explicitly excluded subtree. Restic
therefore excluded the test root itself. The preceding negative checks for
missing weights/Entertainment were vacuous in this attempt: an empty selected
tree cannot prove that valuable originals are retained. The positive geometry
check correctly prevented qualification from passing.

The production source/exclusion policy was not changed. The native fixture now
lives in a separate owner/SYSTEM-protected
`%LOCALAPPDATA%\RNR-Backups\policy-fixtures\native-<unique-id>` directory outside
that exclusion. Its location is recorded in the private native-run evidence.
It contains only the five tiny synthetic files, not real model weights or work.
A control backup must list all five files before the full production exclusions
are applied. Positive geometry/archive/log checks then precede the negative
model/Entertainment checks. A filtered listing is retained privately for
diagnosis; qualification does not suppress or remove an exclusion to pass.

Portable tests execute the native fixture factory with the actual production
policy and real pinned restic: they reproduce the excluded old fixture root,
confirm all five unfiltered control files, retain mesh/archive/log and exclude
weights/Entertainment in the corrected test location. Latest portable result:
**48 passed, zero failures, zero skips**. This is not native Windows evidence.

The corrected `C:\Scripts\Test-WindowsBackup-v12.ps1` matches maintained source;
its prior version was preserved under
`C:\Scripts\archive\2026-10-22-policy-fixture-fix`. A fresh owner-run native
qualification is required. No real v12 backup, task switch or recreation of
`D:\Recovery-Test` occurred. V11 remains scheduled.
