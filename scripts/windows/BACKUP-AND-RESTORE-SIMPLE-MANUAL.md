# Vincent's simple backup and restore manual

Current follow-up, 22 October: the real run passed inventory but stopped at
home capture because a null options array became an empty command argument.
The correction is installed and passes 55 portable checks, zero failures/skips.
The earlier 48-check native pass applies to the prior files. A fresh native
pass is required for the correction, including restic-to-WSL producer checks.
The owner has paused v12 while completing Cognee recovery-key custody and
credential review. Do not start a backup or switch the task from this update.
The older qualification and resume instructions below are historical.

Updated: 22 October 2026. Current everyday script: **v11**.

Save this manual with your recovery information. The same copy is installed at
`C:\Scripts\BACKUP-AND-RESTORE-SIMPLE-MANUAL.md`. Commands run in **Windows
PowerShell**, from any folder. PowerShell 7 can launch the `powershell.exe`
commands below. Do not run them in a Linux terminal.

The corrected v12 launcher passed 48 native Windows checks, zero failures/skips,
exit code 0. The installed files match the qualified hashes. Resume the normal
v12 backup in section 10 without -NewRun; its completed Cognee portion is retained.
No qualification rerun is needed for this documentation update. The scheduled
task remains v11 until real v12 backup and recovery review are complete.
V11 7-Zip archives and v12 restic repositories need different restore procedures;
`Restore-Backup-v12.ps1` cannot restore your existing `base.7z`.

## 1. Which PowerShell window?

| Action | Window to use |
| --- | --- |
| Complete routine v11 backup | Administrator PowerShell, using your usual Vincent Windows account |
| Backup preview | Normal PowerShell |
| Configure or enter the archive password | Normal PowerShell; use the same account that runs backups |
| Test an archive | Normal PowerShell |
| Recover files into a new private folder | Normal PowerShell |
| Reinstall Windows, import an entire WSL distro, restore a live database | Separate guided recovery; administrator/operator access may be needed |

To open an administrator window, find PowerShell in Start, choose **Run as
administrator** and approve Windows' prompt. Do not sign in as a different
administrator: WSL installations and the saved backup password belong to your
Windows account. The archive test you just completed required no elevation.

## 2. Run a normal backup

Connect power, prevent sleep during the run, and make D: available. Start
OneDrive and Google Drive and confirm their configured folders are available.
Do not start another backup while one is running, including the scheduled job.

In **Administrator PowerShell**:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\backup-all-wsl-v11.ps1" -RequireCogneeBackup
Write-Host ("Exit code: " + $LASTEXITCODE)
```

Normally there is **no password prompt**: Windows unlocks the protected password
you already configured. `-RequireCogneeBackup` makes missing/stale Enhanced
Cognee service backups a failure rather than silently accepting the coverage gap.
The command does not change the saved machine-wide execution policy.

Success requires exit code **0**, no recorded backup errors, and completion of
both cloud clients' uploads. A successful copy into a sync folder is only the
start of the cloud upload. Check OneDrive and Google Drive separately afterward.
The encrypted `.7z` archives are under `D:\Archive\Snapshots\chains`. V11 also
uses `D:\Archive\WSL_Backups` as a staging area; its ordinary files are not all
encrypted by the archive password. Keep that area private. Archive encryption
does not establish that Windows drive encryption is enabled.
Logs are at `D:\Archive\Logs`. If the run fails, retain the output and logs;
do not remove files, add `-Force` or run a separate `/MIR` command to repair it.

The first complete archive can take hours. Later v11 runs normally create a
differential against the base, but still scan/copy/check data and may reread
large archives. V12 is intended to improve content reuse after qualification.

For a configuration preview only, in **normal PowerShell**:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\backup-all-wsl-v11.ps1" -RequireCogneeBackup -WhatIf
```

A preview does not verify real source access or perform a backup.

## 3. Which password, and when?

| Password or key | Purpose |
| --- | --- |
| Your written 10-word KeePassXC master passphrase | Opens your KeePassXC vault |
| KeePassXC entry `Windows - Backup archive encryption` | Encrypts/unlocks the Windows/WSL backup archives |
| Microsoft account password / Windows Hello PIN | Windows sign-in or Windows approval prompts; separate from archive encryption |
| Separate Enhanced Cognee recovery keys | Unlock/verify the encrypted Cognee service backup after the outer archive is opened |

For ordinary backups, use the stored password automatically. To enter it
manually for a particular backup, add `-PromptForArchivePassword` to the normal
backup command. Copy the **same archive password** from KeePassXC into its hidden
prompts and confirm it. Do not use the vault master passphrase there.

After reinstalling Windows or moving to another machine, configure automatic
unlocking under your own account, in **normal PowerShell**:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\backup-all-wsl-v11.ps1" -ConfigureArchivePassword
```

Enter and confirm the password from the KeePassXC archive entry. This setup
command does not start a backup. You have already completed it on this machine;
do not repeat it for each backup. Its Windows-protected file is
`%APPDATA%\RNR-Backups\archive-password.xml`. That file alone cannot recover your
backup on another Windows installation. Keep an independently accessible vault
copy and its written master passphrase.

Never put a password after a command's `-p` or `-ArchivePassword` option, in chat,
in a text file or in Git. The legacy v11 backup internally supplies the password
to its 7-Zip child process; a sufficiently privileged local process can inspect
that process argument. Use your trusted machine. V12's different password
handling remains subject to its own qualification.

## 4. Find the recovery point

The local completed v11 archives are under:

```text
D:\Archive\Snapshots\chains\chain-...
```

Cloud copies use the corresponding `WSL_Backups\chains\chain-...` folder in
OneDrive and Google Drive. Your tested generation is:

```text
chain-20261021T140518Z-dc96519cf8914871abf4eed7be7ef35e
```

Keep its `restore-...json` manifest with the archives it names. The manifest is
the recovery recipe: it identifies the matching base and, when present, **one
selected differential**. Recover the base first and that differential second.
Do not stack all differential archives or mix generations. Older base-only
manifests recover their own earlier point, not automatically the latest data.

The recovery copy you have just checked is:

```text
D:\Recovery-Test\WSL-v11-OneDrive-2026-10-21\base.7z
```

Its manifest names only the base. There is no differential for this recovery
point. The archive is 47,503,603,481 bytes (47.5 decimal GB / about 44.2 GiB).

This temporary recovery copy has completed its selected-file drill and the owner
approved its cleanup. It is not the original backup. After cleanup, use the
retained original below for local recovery, or obtain a fresh provider copy to
test remote recovery. The following archive commands use the retained original,
so they do not require keeping another 47.5 GB test copy.

## 5. Verify a recovered archive before extraction

In **normal PowerShell**, compare the checksum with the selected manifest:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath "D:\Archive\Snapshots\chains\chain-20261021T140518Z-dc96519cf8914871abf4eed7be7ef35e\base.7z"
```

The expected SHA256 for this particular base is:

```text
6FBBC9F4E5105D29E9AB7EDD44260EDB79A014C8A93202A0B03FB09C2B97F5E8
```

Then test password/decryption and archive integrity:

```powershell
& "C:\Program Files\7-Zip\7z.exe" t "D:\Archive\Snapshots\chains\chain-20261021T140518Z-dc96519cf8914871abf4eed7be7ef35e\base.7z"
```

At the hidden password prompt, enter the KeePassXC **archive password**. The
password is not echoed. Success is `Everything is Ok`; warnings/errors are not a
pass. This test does not extract files. You have now completed both checks for
this recovery copy, including all 744,108 archived files. You do not need to
repeat this large check immediately. A changed/re-downloaded archive or a new
recovery point needs its own verification.

## 6. First check a few recovered files

The specific temporary recovery copy above was checked in **normal PowerShell**:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\Test-V11RecoveredFiles.ps1" -OpenFiles
```

This installed helper extracts only three named files into a NEW private
`D:\Recovery-Test\Checked-v11-...` folder. It uses the maintained
`C:\Scripts\backup-v12\engine.ps1` for private-folder protection and reporting.
Enter the **archive password** at 7-Zip's hidden prompt. The files are the distro
inventory, the saved backup command text and the Enhanced Cognee README. Their
checksums are compared with the retained v11 staging copies; no recovered
commands are executed. On success, two text files open in Notepad. Confirm that
they are readable and send the small result, never the password.

Only about 155 KB of selected file contents is written, although 7-Zip may need
to read/decompress large solid blocks. The helper does not repeat the entire
archive SHA256 pass. Its report records that application recovery and independent
remote provenance are separate checks. Keep the test copies until the result and
readability confirmation have been reviewed.

Completed result: all three files matched their reference checksums and the
owner confirmed both opened text files were readable. No repeat is needed.
The helper requires the temporary archive at the documented recovery-copy path;
after cleanup it is a historical drill command, not the normal restore command.
Use section 7 with the retained original for a future local restore.

## 7. Extract the tested base into a NEW private recovery folder

This is the **full file-extraction command for the specific base above**, for
reference. It can write about 89.3 GB of files and take considerable time. A
small representative recovery can be guided separately first. There is no need
to extract everything now just because the integrity test passed.

In **normal PowerShell**, paste the whole block together. It creates a unique
folder, restricts it to your Windows account and SYSTEM, checks that permissions
were applied, then extracts. It refuses an existing destination. It does not
restore into Windows, WSL, Hermes or a live project.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $archive = 'D:\Archive\Snapshots\chains\chain-20261021T140518Z-dc96519cf8914871abf4eed7be7ef35e\base.7z'
    $restore = 'D:\Recovery-Test\Restored-v11-' + [guid]::NewGuid().ToString('N')
    if (Test-Path -LiteralPath $restore) { throw 'Choose a new recovery folder.' }
    New-Item -ItemType Directory -Path $restore -ErrorAction Stop | Out-Null
    $ownerSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $restore /inheritance:r /grant:r "*${ownerSid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F'
    if ($LASTEXITCODE -ne 0) { throw 'Folder protection failed. No extraction was started.' }
    Write-Host ('Recovery folder: ' + $restore)
    & 'C:\Program Files\7-Zip\7z.exe' x $archive ("-o" + $restore) -aos
    if ($LASTEXITCODE -ne 0) { throw 'Extraction did not finish cleanly. Keep the output for review.' }
    Write-Host ('Extraction complete. Review files here: ' + $restore)
}
```

Enter the **archive password** when 7-Zip asks. The recovered files are
decrypted; keep this folder private and outside cloud sync. Do not rename a
`.7z` file to decrypt it, run recovered scripts, or copy everything over live
data. Compare selected documents/source files first. The command above is a
prepared recovery procedure; its full extraction and Windows permission result
have not yet been demonstrated by your archive-integrity output.

For a **future manifest containing a differential**, use a new private recovery
folder, extract the matched base, then apply only its named differential to that
same isolated folder. That overlay can replace files and apply deletions inside
the recovery folder. Obtain a path-specific command/review before doing this;
do not adapt the base-only command to overwrite your working data.

## 8. Restoring working systems is a separate step

- Windows documents/source files: compare the recovered copies, then copy back
  only what is needed. Preserve the current versions before replacement.
- Linux homes/workspaces: extract their native archives inside a disposable
  Linux recovery location so filenames, permissions and links are preserved.
  A Windows extraction of the outer archive is not a Linux installation restore.
- Hermes: use its matching native backup/import procedure in a separate test
  profile/environment before replacing profiles or bot data. No single generic
  PowerShell command safely restores all profiles into a running installation.
- Enhanced Cognee: the outer password exposes the still-encrypted `.dump.age`
  file and completion manifest. The protected Hermes operator must use its
  separate age identity, signing/encryption/index recovery material and a NEW
  database. Check memory decryption, history and project access, then rebuild
  derived indexes as required. The archive password alone is insufficient.
- A whole Windows/WSL operating-system recovery needs its own image/export and
  recovery procedure. These selected-data backups do not prove that coverage.

## 9. Schedule, interruptions and what remains

The existing **WSL Master Incremental Backup** task is configured for v11 with
required Cognee coverage, under your account, on its preserved weekly Friday
21:00 schedule. The actual unattended scheduled run still needs verification.
Do not change the task while testing recovery or start a manual run on top of it.
An additional manual backup after important new work is useful if that work
cannot wait for the next scheduled backup. There is no need to repeat the
successful backup merely because the archive test finished. Repeat a recovery
drill periodically and after substantial backup/password/machine changes.

If interrupted, keep the completed generations and partial files. Confirm no
backup is still running before retrying. V11 can reuse staged files and its
completed base, but resuming every operation without rework is not guaranteed.
Do not delete `.partial` files, older archives or provider data as a repair.

Checks completed: real v11 backup; both sync clients reported up to date; full
recovery-copy checksum; owner-run 7-Zip password/integrity test; three selected
extracted-file hashes and owner-confirmed text readability. Still separate:
application recovery, independent remote-source
provenance/provider qualification, the scheduled run, Cognee recovery-key custody
and credential replacement. V12's first real broader-coverage backup/restore
remains pending. OneDrive personal originals remain separate by
your choice; do not assume every file on C:, D: or in every distro is covered.

Keep the vault recovery copy independently available. Do not retain its only
copy inside an archive whose password is stored in that vault.

## 10. First real v12 backup after successful qualification

Use **Administrator PowerShell under your usual Vincent account**. Keep the
laptop powered and awake, with OneDrive and Google Drive running. Ensure no
other backup is running. Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\backup-all-wsl-v12.ps1" -RequireCogneeBackup
Write-Host ("Exit code: " + $LASTEXITCODE)
```

The saved archive password is used automatically; do not put it in the command.
The encrypted repository is `D:\Archive\Snapshots\restic-v12`, separate from
retained v11 archives. The first run can take hours and needs a new baseline;
later v12 runs reuse stored content. Keep both clients running until uploads
finish. Send the final result or any error for review. This command does not
switch the scheduled task. Review real scopes and prove selected v12 recovery
before that transition. For v12 recovery use its operating/recovery guide,
rather than the v11 7-Zip commands.

If a run stops at `Home inventory failed`, keep its checkpoint and repository.
Do not choose NewRun or delete data. A read-only diagnostic is available in
normal PowerShell as the same owner:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\Diagnose-V12HomeInventory.ps1" -Distro "Ubuntu-Workspace"
Write-Host ("Exit code: " + $LASTEXITCODE)
```

Send the small result and exit code. Detailed stdout/stderr stays in its private
evidence folder; do not paste those raw files into chat. This does not start a
backup or change the task. The diagnostic preserves the existing qualification
hashes, so adding it does not require another qualification test.
