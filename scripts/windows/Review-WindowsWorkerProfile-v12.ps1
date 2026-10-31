# Read-only: never deletes, moves, enables or changes a Windows account/profile.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $PSHOME Modules
$account=Get-LocalUser -Name rnr-worker -ErrorAction SilentlyContinue
if (-not $account) {
 [pscustomobject]@{ProfileFolderExists=(Test-Path 'C:\Users\rnr-worker');AccountPresent=$false;Action='Preserve folder; native account/profile review required before any cleanup.'}|Format-List
 return
}
$group=Get-LocalGroup -SID 'S-1-5-32-544'
$admins=@(Get-LocalGroupMember -Group $group.Name)
$isAdmin=@($admins|Where-Object {$_.SID.Value -eq $account.SID.Value}).Count -gt 0
$profile=Get-CimInstance Win32_UserProfile|Where-Object {$_.SID -eq $account.SID.Value}
[pscustomobject]@{AccountPresent=$true;AccountEnabled=$account.Enabled;IsAdministrator=$isAdmin;
 ManagedWindowsProfile=([bool]$profile);ProfileLoaded=([bool]$profile.Loaded);
 ProfileFolderExists=(Test-Path 'C:\Users\rnr-worker');
 Action='Keep the Windows-managed profile in place; the Spatial worker uses this isolated identity.'}|Format-List
if ($isAdmin) {Write-Warning 'Worker administrator membership needs a separate security review. Nothing changed.'}
