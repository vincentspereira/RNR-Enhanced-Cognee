# Restore only into a new disposable destination. Never overwrites originals.
[CmdletBinding(SupportsShouldProcess=$true)]
param(
 [Parameter(Mandatory=$true)][string]$Repository,
 [Parameter(Mandatory=$true)][string]$Destination,
 [string]$Snapshot,
 [string]$PasswordFile="$env:APPDATA\RNR-Backups\archive-password.xml",
 [switch]$PromptForRecoveryPassword,
 [switch]$ListSnapshots,
 [switch]$VerifyOnly
)
$ErrorActionPreference='Stop'
. "$PSScriptRoot\backup-v12\engine.ps1"
. "$PSScriptRoot\backup-v12\policy.ps1"
if ($WhatIfPreference) {Write-Host 'Preview only: verify/decrypt a repository or restore a chosen snapshot into a NEW folder.';return}
if ($env:OS -ne 'Windows_NT') {throw 'Use native Windows PowerShell.'}
$env:PSModulePath=Join-Path $PSHOME Modules
$restic="$PSScriptRoot\backup-v12\tools\0.19.1\restic.exe"
if ((Get-FileHash -LiteralPath $restic).Hash -ne 'b0dd1fd21eea5d8fe1325f55f7118213c21f36de8a261e04c0624a5ab9fd7830') {throw 'Backup engine hash differs.'}
Assert-V12SeparatePaths @($Repository) @($Destination)
if (Test-Path -LiteralPath $Destination) {throw 'Choose a new disposable recovery folder. Existing destinations are preserved.'}
$privateRoot=$null
try {
 if ($PromptForRecoveryPassword) {
  $privateRoot=Join-Path $env:LOCALAPPDATA ('RNR-Backups\recovery-tests\'+[guid]::NewGuid().ToString('N'))
  Protect-V12Directory $privateRoot
  $PasswordFile=Join-Path $privateRoot recovery-password.xml
  $secure=Read-Host 'Enter the backup archive password from KeePassXC (hidden, never paste it into chat)' -AsSecureString
  try {
   if ($secure.Length -lt 20) {throw 'Recovery password is too short.'}
   $secure|Export-Clixml -LiteralPath $PasswordFile
  } finally {$secure.Dispose()}
 }
 $privateCommand=(ConvertTo-V12Argument "$PSHOME\powershell.exe")+' -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File '+
 (ConvertTo-V12Argument "$PSScriptRoot\backup-v12\Read-Password.ps1")+' -PasswordFile '+(ConvertTo-V12Argument $PasswordFile)
 $common=@('-r',$Repository,'--password-command',$privateCommand,'--cache-dir',(Join-Path $env:LOCALAPPDATA RNR-Backups\recovery-cache))
 if ($ListSnapshots) {
  $r=Invoke-V12Process $restic ($common+@('snapshots')) $null
 } elseif ($VerifyOnly) {
  $r=Invoke-V12Process $restic ($common+@('check','--read-data')) $null
 } else {
  if (-not $Snapshot -or $Snapshot -eq 'latest') {throw 'Choose an explicit snapshot ID from ListSnapshots; scopes have independent snapshots.'}
  if ($Snapshot -notmatch '^[a-fA-F0-9]{8,64}$') {throw 'Snapshot must be an explicit hexadecimal ID from the recovery-point list.'}
  if (-not $PSCmdlet.ShouldProcess($Destination,'restore selected encrypted snapshot into a NEW folder')) {return}
  Protect-V12Directory $Destination
  $r=Invoke-V12Process $restic ($common+@('restore',$Snapshot,'--target',$Destination,'--verify')) $null
 }
 if ($r.exit -ne 0) {throw ('Recovery command failed (exit '+$r.exit+'); existing backups and originals preserved.')}
 $r.stdout
 Write-Host 'OK: requested recovery operation completed. Linux home data is inside the recovered tar; extract it only in a disposable Linux recovery location.'
} finally {
 # Keep the encrypted, restricted DPAPI recovery file as a recovery-test
 # artifact. No plaintext file was created, and no existing file is deleted.
 if ($privateRoot) {Write-Host ('Private encrypted recovery-test artifact retained at '+$privateRoot)}
}
