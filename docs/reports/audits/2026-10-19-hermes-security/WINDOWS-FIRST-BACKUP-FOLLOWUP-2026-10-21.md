# Windows first backup follow-up - 21 October 2026

## Second real run: native npm selection

The second supplied full-run output exited 1 after 01:05:40. It again collected
four encrypted Cognee pairs, but Workspace's `npm-global` inventory returned 1.
Cloud status was `blocked_by_local_error`: no archive was attempted, so this run
does not qualify the full-tree link correction or publish a new generation.

Read-only reproduction found noninteractive `bash -lc` selecting the Windows
npm launcher from the mounted Windows PATH while finding Linux system Node 18.
The user's interactive `.bashrc` returns before loading nvm in that shell mode.
Windows npm then reported that it could not determine its Node installation.
The available Linux nvm default is Node 24.18.0 with npm 12.0.0; explicitly
selecting it successfully listed seven global packages with no dependency
problems. No runtime was installed or upgraded.

The Windows-local v11 manifest worker now filters Windows-drive entries only
from its child process PATH, selects the existing nvm default when available,
and verifies that both npm and Node resolve to native Linux paths. It records
the executable paths alongside inventory status. No login profile, saved PATH,
interop policy, runtime default, private store or service was changed.

The same Workspace/Company inventory capture is now performed before long file
copies and reused in section 5. A failed inventory exits before those copies or
cloud archive creation. Genuine failures still fail; no exit code is suppressed.

The installed worker's five actual Workspace inventories were rerun directly:
four succeeded and the empty crontab was correctly recorded. The earlier
54-check native run established the prior revision; it checked command success
without proving Linux npm selection. Two executable-route assertions were added
to the native runner (56 checks with Cognee collection). The changed PowerShell
wrapper, Company inventory and complete 56-check native run still require owner
Windows execution because this session cannot launch Windows executables.

Latest Windows script SHA256:
`62214ce03631fd21861baec7c4262c059429690ad86fcfdf4516ce1fadeb3501`.

The sections below retain first-run and prior-revision evidence. The complete
backup, remote upload, archive recovery and actual scheduled execution remain
unqualified.

## Confirmed owner and Windows progress

The owner created a KeePassXC vault, retained a written master passphrase,
configured the Windows-protected archive password and retained its vault entry.
The owner downloaded an independent OneDrive copy of the encrypted vault,
unlocked it using the written passphrase and confirmed the Windows archive and
Microsoft sign-in entries. This does not establish owner custody of the separate
Cognee age identity, signing/encryption keys or complete service recovery map.

The existing Windows scheduled task was corrected with the owner's credential
prompt. Its action now invokes v11 with `-RequireCogneeBackup`; independent
read-only comparison confirmed its triggers, settings and principal unchanged,
password logon and IgnoreNew preserved. No account-password reset was needed.
The correction did not start the task. Next run at review was 23 October, 21:00
Windows local time; the historical task result was not a new execution result.

## First real backup result

The supplied output records exit 1 after 03:03:23. Four completed encrypted
Cognee backup/manifest pairs were collected with ciphertext hashes verified.
The local staging tree was 81.32 GB. The new 7-Zip base remained a partial file
after 21 scan warnings about Linux links retained in the Windows staging tree.
No new cloud generation was admitted. Do not call this a complete restore point.

Workspace and Company inventory generation also printed five redirection errors
each. A multiline shell argument contained Windows line endings, and a final
`true` concealed failing commands. These errors were not counted by the old
script's final error list. Optional missing GnuPG directories and cloud-cache
size observations are distinct from these failures.

## Correction and qualification

The Windows-local maintained file remains `C:\Scripts\backup-all-wsl-v11.ps1`.
Originals were preserved before editing; no source links, failed archives, older
generations, private profiles or keys were removed.

- Record links without following them in `_manifests/archive-links.json` and
  exclude those exact paths from 7-Zip. The catalog travels inside the encrypted
  archive. A link record preserves its target, not the target's external data.
- Keep ordinary-file warnings fatal and keep failed partial output unpublished.
- Pull inventories as structured output rather than redirecting through a
  multiline shell argument. Record every command's status; distinguish optional
  uninstalled commands/no crontab from failures. Preserve prior failed manifests
  and count actual failures so they block cloud archival. Capture environment
  names only; pip listing disables index/version checks.
- Explicitly choose the Linux working directory for new Python collection calls,
  avoiding inherited Windows/UNC current-directory translation in isolated WSL.

The expanded native test passed 54 checks with zero failures: encrypted base and
differential recovery, DPAPI unattended unlocking, exact link exclusion, dangling
and cyclic links, preservation of an ordinary same-name file and all target
metadata, both actual distro inventories, binary collection and four actual
Cognee pairs. The first expanded attempt exposed a PowerShell 5.1 array-count
assertion issue in the test harness; that assertion was corrected and the suite
rerun. Its failing evidence remains retained.

After final scan/working-directory housekeeping, the owner reran the native
qualification from Windows. Its saved summary was independently read and its
script SHA256 matched the current maintained file: complete, 54 passed, zero
failed, four completed Cognee pairs collected. The task still uses v11 with
required Cognee coverage, password logon and IgnoreNew; the test did not modify
it. No full backup or cloud upload was started by this qualification. Its
scheduled-execution and off-machine archive-recovery flags remain false.
This session's earlier Windows executable launch failure was not bypassed by
changing interop registration; the owner's direct Windows run resolved that
qualification prerequisite.

Prior Windows script SHA256 (the owner's 54-check native run):
`b12a9c549de35c6ad0d2902b5936f6f77ea942a90f4298bdab68b42999086f00`.

Remaining: successful full backup retry, both remote
uploads, downloaded matching generation recovery and actual scheduled execution.
Service recovery-key custody, exposed-credential disposition, frontend release
gates and everyday bot admission remain separate unfinished acceptance items.
