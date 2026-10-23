# Windows backup v12

Current follow-up, 22 October: the real run passed inventory but stopped at
home capture because a null options array became an empty command argument.
The correction is installed and passes 55 portable checks, zero failures/skips.
The earlier 48-check native pass applies to the prior files. A fresh native
pass is required for the correction, including restic-to-WSL producer checks.
The owner has paused v12 while completing Cognee recovery-key custody and
credential review. Do not start a backup or switch the task from this update.
The older qualification and resume instructions below are historical.

For the currently qualified **v11** routine and its tested 7-Zip recovery copy,
use [Vincent's simple backup and restore manual](BACKUP-AND-RESTORE-SIMPLE-MANUAL.md).
The corrected v12 launcher passed native qualification on 22 October: 48 passed,
zero failures/skips, exit 0, including the actual Windows-to-WSL probe. All 15
qualified installed hashes match. Resume the interrupted normal backup without
-NewRun, then review real backup/recovery before a task switch. Its restic restore
helper does not open the existing v11 `base.7z` archives.

Maintained source for Vincent's Windows/WSL backup. The installed entry point is
`C:\Scripts\backup-all-wsl-v12.ps1`; its `backup-v12` support folder must travel
with it. The real Windows DPAPI password file, private state, native reports,
recovery keys and backup repositories never belong in Git.

Copy the reviewed files to C:\Scripts, preserving the support directory. Run
`Install-BackupV12Tools.ps1` from Windows to obtain the pinned official portable
restic binary if absent. It verifies both the release ZIP and extracted binary.
The binary is already prepared on Vincent's machine; no global installation or
PATH change is needed. Public release hashes are in backup-v12/tool-provenance.json.

Read [the operating/recovery guide](BACKUP-ENCRYPTION-AND-RESTORE-v12.md).
The native test is mandatory before real v12 backup and any task switch.
It does not start the full backup, upload real data or change Task Scheduler.
Existing v11 and all earlier backup generations must remain intact.

Portable source qualification, using independently verified Linux tools:

```bash
RNR_BACKUP_V12_SUPPORT="$PWD/scripts/windows/backup-v12" \
  python3 scripts/qualification/test_backup_v12.py
pwsh -NoProfile -File scripts/qualification/Test-BackupV12-Portable.ps1 \
  -WindowsScriptRoot "$PWD/scripts/windows"
```

These checks prove stream/SQLite/profile handling, real encrypted restic
recovery, producer failure, checkpoint reuse, ciphertext copy/resume and
portable PowerShell parsing. They do not establish native Windows 5.1, VSS,
DPAPI, ACL, real home completeness, real cloud upload/recovery or offline WSL
export/import qualification. Native test evidence must identify exact hashes.

Do not remove a worker account/profile as a folder cleanup. The read-only
Review-WindowsWorkerProfile helper reports its Windows-managed role. The Hermes
reorganisation helper defaults to inventory, refuses active sources/collisions
and preserves original bytes/metadata plus compatibility links on applied moves.

23 October source update: the Cognee collector now requires both recent signed-
manifest-shaped encrypted database and restricted-Hermes-profile generations.
It checks ciphertext hashes, private owner/mode/link/path guards and source
stability; signature authenticity and decryption remain separate key-based
recovery checks. --verify-only is a no-export aggregate inventory. The versioned
cognee-v2-profiles scope prevents an old database-only checkpoint satisfying new
coverage. A completed old online run requires a preserved new run after native
admission; RetryCloudOnly does not add the missing profile generation. No
installed Windows file/task or cloud destination was changed by this source
update. V12 remains paused; native qualification of the updated hashes and
actual collection/downloaded recovery remain pending.

This source revision passes 1174 focused repository checks, 14 portable Python
backup checks and 59 portable PowerShell checks, with zero failures/skips and no
pytest warnings. The new collector has actual age/tar recovery and a real restic
producer refusal/restore test. Root ownership is simulated in these fixtures;
portable PS7 is not native Windows 5.1/DPAPI/VSS/ACL/cloud qualification. Earlier
native hashes/results above remain historical and do not admit these changes.
