# Windows backup v12

For the currently qualified **v11** routine and its tested 7-Zip recovery copy,
use [Vincent's simple backup and restore manual](BACKUP-AND-RESTORE-SIMPLE-MANUAL.md).
V12 passed native qualification on 22 October (45 passed, zero failures/skips),
for the earlier candidate. The subsequent WSL launcher correction requires a
fresh native pass, followed by real backup/recovery review before a task switch. Its
restic restore helper does not open the existing v11 `base.7z` archives.

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
