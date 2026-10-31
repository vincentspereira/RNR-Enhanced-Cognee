# Preview first. -Apply updates only this existing task's action after prerequisites.
[CmdletBinding(SupportsShouldProcess=$true)]
param([switch]$Apply,[switch]$PromptForTaskCredential)
function Assert-V12ScheduledCoverage {
 param([object]$Run)
 if (-not $Run.local_complete -or -not $Run.cloud.OneDrive -or -not $Run.cloud.GoogleDrive) {
  throw 'The first local backup and both cloud sync-folder copies must complete before switching the task.'
 }
 foreach ($scope in @('cognee-v2-profiles','Ubuntu-Workspace','Ubuntu-Hermes','Ubuntu-Company','Windows-D')) {
  if (-not $Run.completed.PSObject.Properties[$scope]) {
   throw 'The normal real backup must qualify all three homes, encrypted Cognee database AND profile coverage, and Windows-D. Legacy database-only snapshots and offline exports do not qualify the scheduled home backup.'
  }
 }
}
$ErrorActionPreference='Stop'
# Process-local built-in modules; no saved environment or machine policy change.
$env:PSModulePath=Join-Path $PSHOME 'Modules'
$taskName='WSL Master Incremental Backup'
$scriptPath='C:\Scripts\backup-all-wsl-v12.ps1'
$task=Get-ScheduledTask -TaskName $taskName
if (@($task.Actions).Count -ne 1) {throw 'Review required: task no longer has one action.'}
$proposed='-NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File "C:\Scripts\backup-all-wsl-v12.ps1" -RequireCogneeBackup'
$account=[Security.Principal.WindowsIdentity]::GetCurrent()
if ($task.Principal.UserId -notin @($account.Name,$env:USERNAME,$account.User.Value)) {
 throw 'Review required: use the Windows account that owns the scheduled backup.'
}
$preview=[pscustomobject]@{TaskName=$taskName;CurrentActionTargetsV12=[bool]($task.Actions.Arguments -match 'backup-all-wsl-v12\.ps1');
 ProposedProgram="$PSHOME\powershell.exe";ProposedArguments=$proposed;
 SchedulePreserved=$true;PrincipalAndLogonPreserved=$true;OverlapPolicy=$task.Settings.MultipleInstances.ToString();
 TaskStartsImmediately=$false;SavedMachineExecutionPolicyChanged=$false;
 PasswordConfigured=[IO.File]::Exists("$env:APPDATA\RNR-Backups\archive-password.xml")}
$preview|Format-List
if (-not $Apply) {Write-Host 'Preview only. No scheduled task was changed.';return}
$qualification=Join-Path $env:LOCALAPPDATA 'RNR-Backups\v12-state\qualification\latest-pass.json'
if (-not (Test-Path -LiteralPath $qualification)) {throw 'Run Test-WindowsBackup-v12.ps1 successfully first. The current v11 task is preserved.'}
$proof=Get-Content -LiteralPath $qualification -Raw|ConvertFrom-Json
if (-not $proof.complete -or -not $proof.native_windows -or $proof.failed -ne 0 -or $proof.skipped -ne 0) {throw 'Native v12 qualification is incomplete.'}
foreach ($entry in $proof.source_hashes.PSObject.Properties) {
 if (-not (Test-Path -LiteralPath $entry.Name) -or (Get-FileHash -LiteralPath $entry.Name).Hash -ne $entry.Value) {throw 'A qualified backup file changed; repeat native qualification before switching the task.'}
}
$state=Join-Path $env:LOCALAPPDATA 'RNR-Backups\v12-state\active-run.json'
if (-not (Test-Path -LiteralPath $state)) {throw 'Complete the first real v12 backup and review coverage before switching the task.'}
$completed=Get-Content -LiteralPath $state -Raw|ConvertFrom-Json
Assert-V12ScheduledCoverage $completed

if (-not [IO.File]::Exists($scriptPath)) {throw 'Maintained v12 script is missing.'}
$passwordPath="$env:APPDATA\RNR-Backups\archive-password.xml"
if (-not [IO.File]::Exists($passwordPath)) {
 throw 'First save the archive password in your password manager, use the existing v11 -ConfigureArchivePassword setup helper locally. V12 reuses that password.'
}
$password=Import-Clixml -LiteralPath $passwordPath
try {
 if ($password -isnot [Security.SecureString] -or $password.Length -lt 20) {throw 'Invalid Windows-protected archive password.'}
} finally {if ($password -is [Security.SecureString]) {$password.Dispose()}}
if (-not $PSCmdlet.ShouldProcess($taskName,'replace only the action with v12 and required Cognee coverage; preserve schedule and do not start task')) {return}
$root=Join-Path "$env:LOCALAPPDATA\RNR-Backups\task-reviews" ((Get-Date -Format yyyyMMdd-HHmmss)+'-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
$acl=New-Object Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true,$false)
foreach ($sid in @($account.User,[Security.Principal.SecurityIdentifier]::new('S-1-5-18'))) {
 $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow'))
}
[IO.Directory]::SetAccessControl($root,$acl)
Export-ScheduledTask -TaskName $taskName|Set-Content -LiteralPath (Join-Path $root task-before.xml) -Encoding Unicode
$action=New-ScheduledTaskAction -Execute "$PSHOME\powershell.exe" -Argument $proposed
# A password-logon task may require its Windows credentials again when updated.
# Request them locally; never accept a plaintext password argument or write it.
$beforeXml=[xml](Export-ScheduledTask -TaskName $taskName)
$beforeInfo=Get-ScheduledTaskInfo -TaskName $taskName
if ($task.State.ToString() -eq 'Running') {throw 'Task is running; no update was applied.'}
if ($PromptForTaskCredential) {
 if ($task.Principal.LogonType.ToString() -ne 'Password') {throw 'Review required: task logon type changed; no update was applied.'}
 $taskCredential=$null;$taskLogonPassword=$null
 try {
  $taskCredential=Get-Credential -UserName $account.Name -Message 'Enter your Windows sign-in PASSWORD for the existing backup task. Not your PIN, vault passphrase or archive password.'
  if ($null -eq $taskCredential) {throw 'No credential supplied; task was not changed.'}
  if (-not [String]::Equals($taskCredential.UserName,$account.Name,[StringComparison]::OrdinalIgnoreCase)) {
   throw 'The supplied account differs from the existing owner; task was not changed.'
  }
  $taskLogonPassword=$taskCredential.GetNetworkCredential().Password
  Set-ScheduledTask -TaskName $taskName -Action $action -User $task.Principal.UserId -Password $taskLogonPassword|Out-Null
 } finally {
  $taskLogonPassword=$null
  if ($null -ne $taskCredential) {$taskCredential.Password.Dispose();$taskCredential=$null}
 }
} else {
 Set-ScheduledTask -TaskName $taskName -Action $action|Out-Null
}
$after=Get-ScheduledTask -TaskName $taskName
if ($after.Actions.Arguments -cne $proposed) {throw 'Task action verification failed; original XML retained.'}
$afterXml=[xml](Export-ScheduledTask -TaskName $taskName)
$afterInfo=Get-ScheduledTaskInfo -TaskName $taskName
if ($beforeXml.Task.Triggers.InnerXml -cne $afterXml.Task.Triggers.InnerXml -or
    $beforeXml.Task.Settings.InnerXml -cne $afterXml.Task.Settings.InnerXml -or
    $task.Principal.LogonType.ToString() -cne $after.Principal.LogonType.ToString() -or
    $task.Principal.RunLevel.ToString() -cne $after.Principal.RunLevel.ToString() -or
    $after.Principal.UserId -notin @($account.Name,$env:USERNAME,$account.User.Value)) {
 throw 'Review required: task settings comparison changed; original XML retained. No task was started by this helper.'
}
if ($beforeInfo.LastRunTime -ne $afterInfo.LastRunTime) {Write-Warning 'Task last-run time changed independently; inspect its history.'}
Write-Host ('Task action updated. Original XML retained at '+$root)
Write-Host 'The task was not started. Run the first real backup when ready, then verify cloud sync and a downloaded recovery.'
