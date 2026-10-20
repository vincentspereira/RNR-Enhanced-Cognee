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
errors. 7-Zip is installed.

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

The first attempt to run this harness was refused by Windows script execution
policy before its code started. No persistent user/machine execution policy was
configured, no Group Policy execution setting was found and no process-only
policy was supplied. Native parser and read-only inspection results must not be
represented as successful DPAPI, 7-Zip, collection or scheduled-execution tests.
A question for process-only RemoteSigned execution is pending; dependent tests
remain unperformed until approved. No policy workaround was used.

After that approval, the existing test command is:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File "$env:LOCALAPPDATA\RNR-Backups\qualification-tools\Test-WindowsBackup.ps1" -CollectCognee -TaskName 'WSL Master Incremental Backup'
```

This generated test password is unrelated to the owner's real archive password.
Tests retain their small fixture directory. They do not prove password-manager
custody, an actual scheduled run or a downloaded-cloud recovery.

## Remaining independent and owner gates

1. Finish the pending native tests after the process-only policy decision.
2. Owner chooses and retains the real archive password, then uses the maintained
   v11 ConfigureArchivePassword operation locally. Never paste it into chat.
   This is separate from the memory database encryption/age/manifest keys.
3. Review and authorize the prepared task action correction; preserve the existing
   weekly schedule unless the owner explicitly chooses another frequency.
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

The previous exact revision e5a02343 passed Required CI, default-stack and
canonical-browser. Both frontend jobs failed only their enforced full dependency
audits: five HIGH development-dependency matches each, zero production matches.
That evidence is historical for later documentation/test commits. Main remains
protected and unchanged; a new candidate needs exact-revision hosted checks.

Sanitized additional evidence:
[evidence/2026-10-20-windows-fleet-followup.json](evidence/2026-10-20-windows-fleet-followup.json).

References:
- [Current braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
- [Microsoft DPAPI-bound credential exports](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/export-clixml?view=powershell-5.1)

