# Read-only WSL inventory diagnostic. Retains private errors without printing
# package lists, configuration contents or raw traceback paths to the console.
[CmdletBinding(SupportsShouldProcess=$true)]
param([ValidateSet('Ubuntu-Workspace','Ubuntu-Hermes','Ubuntu-Company')][string]$Distro='Ubuntu-Workspace')
$ErrorActionPreference='Stop'
if ($WhatIfPreference) {Write-Host 'Preview only: run the existing qualified home inventory and save private diagnostics; no backup/upload/task change.';return}
if ($env:OS -ne 'Windows_NT') {throw 'Run this diagnostic in Windows PowerShell as the backup owner.'}
$env:PSModulePath=Join-Path $PSHOME Modules
. (Join-Path $PSScriptRoot 'backup-v12\engine.ps1')
$state=Join-Path $env:LOCALAPPDATA 'RNR-Backups\v12-state'
$proof=Get-Content -LiteralPath (Join-Path $state qualification\latest-pass.json) -Raw|ConvertFrom-Json
if (-not $proof.complete -or -not $proof.native_windows -or $proof.failed -ne 0 -or $proof.skipped -ne 0) {throw 'The qualified runtime receipt is required.'}
foreach ($entry in $proof.source_hashes.PSObject.Properties) {
 if (-not (Test-Path -LiteralPath $entry.Name) -or (Get-FileHash -LiteralPath $entry.Name).Hash -ne $entry.Value) {throw 'A qualified runtime file changed; preserve it for review.'}
}
$private=Join-Path $state ('inventory-diagnostics\'+$Distro+'-'+[guid]::NewGuid().ToString('N'))
if (-not $PSCmdlet.ShouldProcess($private,'save diagnostics from the existing read-only home inventory')) {return}
Protect-V12Directory $private
$helper=Join-Path $PSScriptRoot 'backup-v12\capture_home.py'
$arguments=@('-d',$Distro,'-u','vincentspereira','--cd','/','--exec')+
 (Get-V12PythonCommand $helper @('--inventory-only'))
Write-Host ('Checking '+$Distro+' inventory. A large home can take several minutes; no file contents are being backed up.')
$result=Invoke-V12Process (Join-Path $env:SystemRoot 'System32\wsl.exe') $arguments (Join-Path $private inventory)
$report=@{complete=($result.exit -eq 0);inventory_exit=$result.exit;distro=$Distro;private_evidence=$private;
 real_backup_started=$false;cloud_upload_started=$false;qualified_runtime_unchanged=$true}
Save-V12Json $report (Join-Path $private summary.json)
[pscustomobject]$report|Select-Object complete,inventory_exit,distro,private_evidence|ConvertTo-Json -Compress
Write-Host 'Send only this small result. Keep inventory.stdout and inventory.stderr private; do not paste them into chat.'
if ($result.exit -ne 0) {exit 1}
exit 0
