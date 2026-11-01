# Windows recovery and protected fleet follow-up

Date: 20 October 2026. Supplements the
[protected deployment report](HERMES-PROTECTED-DEPLOYMENT-2026-10-20.md).
Vincent is still completing credential/recovery custody confirmation. No private
activation, main merge, everyday-bot changes or new test account was performed.

## Further installed fleet checks completed

The HTTP fixture tests/qualification/live_fleet_smoke.py was delivered through
GitHub at df575f29d880c277265b3c99f516888dd2984784, then executed against the
installed protected API inside Ubuntu-Hermes. A fresh synthetic tenant contained
41 bot scopes and a controller. The client ran as existing unprivileged nobody
(UID 65534), with scoped short-lived tokens through standard input. No signing,
database, recovery or real profile keys were given to it. A separate synthetic
reviewer token performed the explicit library approvals.

All checks passed:
- 42 private writes with at most eight concurrent requests; batch time 0.998 s.
- Private recalls with concurrency four and 42 cross-scope denial checks.
- Reviewed common guidance accessible to all 41 admitted synthetic bot scopes.
- Ordinary credentials denied reviewer membership administration.
- Membership revocation immediately denied the revoked reader.
- Correcting published guidance withdrew the prior publication from every bot;
  their own private records remained accessible.
- Actual vector-index querying and zero pending events across all 42 scopes.
- 299 requests, no admission retries; median request time 0.011 s and p95 0.110 s.

These are warm synthetic memory-service measurements on this laptop, not an SLA
or a model-inference benchmark. No actual bot profiles were installed, no chat
model calls ran and no claim of 42 simultaneous conversations is made. The
temporary account removed in the previous continuation was not recreated.

## Windows checks and newly confirmed scheduling fault

Native Windows PowerShell 5.1.26100.9711 is reachable through the existing host
control route. No mounts, interop settings or firewall rules were changed.
The maintained C:\Scripts\backup-all-wsl-v11.ps1 parses with zero errors. Its
new qualification harness and prepared scheduling helper also parse with zero
errors. 7-Zip 26.03 is installed. After the process-only approval, all 32 native
Windows checks passed, including DPAPI, archive recovery and real WSL collection.

Read-only inspection of WSL Master Incremental Backup found:
- Its action refers to backup-all-wsl.ps1, and that target file does not exist.
- The action does not select v11 or require a completed Cognee backup.
- The task is Ready, uses the same Windows account with Password logon and
  Highest run level, and retains IgnoreNew overlap protection.
- Its weekly schedule is intact. The last result is nonzero (0xFFFD0000).
  The missing target is a confirmed fault; that result code alone was not used
  to diagnose every historical failure.
- No Windows-protected archive-password file is present at the configured
  per-user location. No new-format restore manifests were found under the
  configured local D:\Archive\Snapshots\chains directory. This does not prove
  that older archives or remote copies are absent elsewhere.

The live scheduled task has not been edited, started, disabled or deleted.

## Prepared correction and verification

C:\Scripts\Update-WSLBackupTask-v11.ps1 is an inert-by-default review helper.
With no Apply switch it prints the proposed correction without changing the task.
The proposed action uses the maintained v11 script with RequireCogneeBackup and
RemoteSigned for its PowerShell process only. It preserves the current schedule,
principal/logon and overlap settings and does not start a backup.

Applying requires the real archive-password file to exist, decrypt as a
SecureString for the current account, and meet the minimum length. The original
task XML is saved under a new restricted operator directory before an action
change. The helper deliberately does not create or guess the owner's real
password. Its actual apply path is not yet qualified or executed.

The maintained repository harness scripts/qualification/Test-WindowsBackup.ps1
uses only explicitly selected definitions from the real backup script; it never
dot-sources or starts the full backup. It prepares retained private fixtures for
Windows DPAPI, unattended child-process unlocking, actual 7-Zip encryption,
wrong-password refusal, encrypted filenames, base-plus-latest-diff restoration,
matched manifests and older-file preservation. CollectCognee additionally tests
the actual Windows-to-Hermes pull of completed encrypted backup/manifest pairs
into an isolated fixture destination, without collecting recovery keys.

The first harness launch was refused before execution by Windows policy.
Vincent then approved RemoteSigned only for this native test process. No saved
machine/user policy was changed. A separate fresh process afterward verified
that both saved policies remain unset and no process policy was inherited.

Native execution exposed and repaired two environment/implementation issues:
- Desktop's inherited module path included PowerShell 7 modules before the
  Windows PowerShell 5.1 modules. Loading the Security module failed with duplicate
  type data. The test process now selects only its own built-in module directory;
  no saved environment variable or profile was edited.
- Actual encrypted-backup inventory failed because the v11 WSL calls invoked an
  implicit shell. The extra shell parsed Python parentheses and quotes instead
  of passing the intended argument. All 13 relevant direct/interpreter call
  sites now use explicit WSL exec, including the binary-export launcher.
  Original v11 is preserved as
  C:\Scripts\backup-all-wsl-v11.ps1.before-native-exec-20261020.bak.
  The corrected script remains C:\Scripts\backup-all-wsl-v11.ps1, SHA256
  235e44c93e346d88a2d98870cc516a964111518a46973f2ecb23adbb9dbd32da.

The final native run passed 32 checks with zero failures:
- Windows DPAPI encryption without plaintext in the file, same-account recovery,
  and unattended unlocking in a separate PowerShell process.
- Actual 7-Zip encryption and integrity, wrong-password rejection, encrypted
  filenames, matched base/latest-differential restoration of added/changed/
  deleted files, restore-manifest hashes and retained older sync-folder files.
- Actual WSL binary export of every byte value into a destination with spaces.
  Failed exports retain their partial file and are not promoted as complete.
- Collection of three real encrypted Cognee backup/manifest pairs from the
  protected approved Hermes directory into a new private Windows fixture,
  checking copied lengths and SHA256 hashes. No recovery keys were collected.

Earlier failed fixture runs are retained. The task repair helper's default
preview also ran successfully without modifying or starting the existing task.
Vincent approved that exact task correction after real archive-password setup;
the absent password file is now the prerequisite, not an unanswered approval.
Additional native probes verified quoted bash/Python ZIP arguments without
writing host files, and the actual corrected v11 WhatIf preview exited zero.

The repeatable native test command is:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File "$env:LOCALAPPDATA\RNR-Backups\qualification-tools\Test-WindowsBackup.ps1" -CollectCognee -TaskName 'WSL Master Incremental Backup'
```

This generated test password is unrelated to the owner's real archive password.
Tests retain their small fixture directory. They do not prove password-manager
custody, an actual scheduled run or a downloaded-cloud recovery. The real Windows
archive-password file is still absent; the generated test password did not
configure or replace the owner's real archive password.

## Remaining independent and owner gates

1. Native Windows mechanics are qualified. Complete the owner-password, actual
   scheduling and real off-machine recovery steps below.
2. Owner chooses and retains the real archive password, then uses the maintained
   v11 ConfigureArchivePassword operation locally. Never paste it into chat.
   This is separate from the memory database encryption/age/manifest keys.
3. Apply the already approved task action correction once the real protected
   archive-password file is configured. Preserve the existing weekly schedule;
   do not start the task as part of the correction or ask again for approval.
4. Run a real backup at a convenient time, verify both cloud clients completed
   upload, download a matched base/latest differential generation, and restore
   into a new empty recovery directory using independent recovery material.
5. Confirm exposed-credential revocation/replacement and independent memory
   recovery custody, then review the first real bot's non-admin operating
   boundary and credential renewal before a staged private rollout.
6. Retain frontend release gates. Fresh registry inspection still reports braces
   3.0.3 and eslint-config-next 16.4.2. The latest Next lint plugin pins fast-glob
   3.3.1, whose micromatch chain still reaches braces. No listed patched braces
   version is available. No lint removal, unsupported replacement, fake version,
   audit suppression or downgrade was introduced.

Fresh hosted checks on dac7826f56d876d5282f7210581f114e061ec06d completed:
- Required CI run 39501940961 passed: 4,344 units, 3 schema, 10 upstream settings/
  security and 80 canonical checks, with zero failures/errors/skips.
- Default-stack run 39501944103 passed all 35 checks with zero skips.
- Dashboard run 39501947497 passed the real browser. Both frontend jobs passed
  their other steps but failed the enforced full dependency audit: five HIGH
  development-dependency matches each, zero production findings.

Later native-helper/evidence updates do not silently inherit exact-revision
release approval from those runs. No application runtime changed in this
follow-up. Main remains protected and unchanged; unresolved audits and owner/
private-activation requirements still prevent conditional main merge.

Sanitized additional evidence:
[evidence/2026-10-20-windows-fleet-followup.json](evidence/2026-10-20-windows-fleet-followup.json).

References:
- [Current braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
- [Microsoft DPAPI-bound credential exports](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/export-clixml?view=powershell-5.1)

