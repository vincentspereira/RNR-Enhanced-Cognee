# V12 native Windows qualification passed

Superseding follow-up: [home capture correction](WINDOWS-V12-HOME-CAPTURE-2026-10-22.md).
The 48-check pass remains historical after the next real run exposed null
capture options. The installed correction passes 55 portable checks and needs
fresh native qualification. V12 is paused for guided owner custody/credential
review; do not execute the older resume command below yet.

Date: 22 October 2026. This supersedes the earlier native-pending/failure status.
First real backup, provider/recovery review and task transition remain separate.

## Current result: corrected launcher qualified

The corrected executable/source candidate `8d5fb23f9` passed **48 native Windows
checks, zero failures, zero skips, exit code 0**. The owner supplied the result,
and the retained native receipt confirms it. Artifact leaf:
`native-7769a18e4da14426826359ee609028ac`.

All 15 receipt hashes match the installed files. The three added checks passed:
actual WSL distro execution, owner/working-directory identity, and a helper-sized
encoded payload with synthetic argument roundtrips. Portable qualification
separately passed 52 checks with zero failures/skips. These are separate suites.
This documentation update changes no qualified runtime files.

The existing real run `20261022T011910Z-65be90bc` remains incomplete: only `cognee`
is committed, local completion is false and cloud results are empty. Resume the
normal backup command below **without -NewRun** to reuse that progress. First real
home/profile/Windows capture, provider upload/recovery review and task transition
remain pending. The scheduled task remains v11. No backup or upload was started
by recording this result.

## Historical receipt: earlier 45-check candidate

Later update: this is the prior candidate's pass. The subsequent real run exposed
a WSL launcher serialization defect, and its correction changes three qualified
files. A fresh native pass is required; see
[the first-real follow-up](WINDOWS-V12-FIRST-REAL-FOLLOWUP-2026-10-22.md).
The historical receipt below was preserved, not relabeled as a pass for new code.

The owner supplied: complete true, **45 passed, zero failed, zero skipped,
exit code 0**. The retained `latest-pass.json` and matching native run report
confirm all 45 checks. Artifact leaf:
`native-dd39e7c11e6f4ee7bac70ddd50716a91`.

All **15 qualified file hashes** were independently checked against the installed
files with no mismatch. All 16 maintained runtime/provenance files also match
the repository. The executable/source candidate is `9d5964a59`; this documentation
update changes none of those qualified files and requires no repeat test.

Passed native checks include parsing/pinned engine, JSON list handling, DPAPI
and the private password pipe, VSS, unchanged-content reuse, scope/run separation,
corrected/deleted/older-file recovery, producer failure without a false snapshot,
source/destination recursion rejection, encrypted copy/reuse/resume, corruption
preservation, local/copied-repository integrity, Windows recovery inventory,
actual source-policy boundaries, five-file exclusion control and original
geometry/archive/log retention. The main read-only preview also passed.
Portable qualification separately passed 48 checks with zero failures/skips.

No real v12 repository or active-run checkpoint existed at verification. D: had
about 1,004.8 GiB free and C: about 487.6 GiB free; these observations do not
verify cloud quota. G: is not visible in this WSL session, which does not prove
its availability or absence in Windows.

## Resume the current backup

For the current qualified candidate, resume in Administrator PowerShell as the
same Windows owner:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\backup-all-wsl-v12.ps1" -RequireCogneeBackup
Write-Host ("Exit code: " + $LASTEXITCODE)
```

The first real attempt already initialized `D:\Archive\Snapshots\restic-v12`.
Its normal retry uses the saved owner DPAPI archive password and retained run.
It captures reviewed homes, Windows/D: and
completed encrypted Cognee backups while preserving v11 generations. Initial
v12 content cannot reuse v11 encrypted 7-Zip blocks; later v12 backups reuse
stored content. Leave both provider clients running and check actual uploads.

The successful receipt retains false for actual home/profile qualification,
real cloud upload and offline WSL restore. Review real scope completion and
warnings, then prove selected real v12 recovery before task transition. The
scheduled task remains v11. No backup, upload, task/credential change or runtime
installation was started by recording this result. Prior failures remain in
`WINDOWS-V12-NATIVE-FOLLOWUP-2026-10-22.md` as historical evidence.
