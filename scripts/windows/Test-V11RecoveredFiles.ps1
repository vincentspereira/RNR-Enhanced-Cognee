# Selected-file drill for the already hash/integrity-checked October v11 base.
# Never extracts over working data or runs recovered scripts.
[CmdletBinding(SupportsShouldProcess=$true)]
param([switch]$OpenFiles)
$ErrorActionPreference='Stop'
if ($WhatIfPreference) {
 Write-Host 'Preview only: extract three named files into a NEW private D:\Recovery-Test folder, compare SHA256, optionally open two text files. No changes made.'
 return
}
if ($env:OS -ne 'Windows_NT') {throw 'Run this drill in normal Windows PowerShell as the backup owner.'}
. (Join-Path $PSScriptRoot 'backup-v12\engine.ps1')
$root='D:\Recovery-Test\WSL-v11-OneDrive-2026-10-21'
$archive=Join-Path $root base.7z
$manifest=Get-Content -LiteralPath (Join-Path $root restore-2026-10-21_135746.json) -Raw|ConvertFrom-Json
$entries=@($manifest.archives)
$expectedArchiveHash='6fbbc9f4e5105d29e9ab7edd44260edb79a014c8a93202a0b03fb09c2b97f5e8'
if ($manifest.encrypted -ne $true -or $entries.Count -ne 1 -or $entries[0].name -cne 'base.7z' -or
    $entries[0].sha256.ToLowerInvariant() -cne $expectedArchiveHash) {
 throw 'This drill requires the previously checked base-only recovery point. No files extracted.'
}
$before=Get-Item -LiteralPath $archive
if ($before.Length -ne 47503603481 -or $before.Attributes -band [IO.FileAttributes]::ReparsePoint) {
 throw 'Unexpected archive length or link; stop for review.'
}
$sevenZip=Join-Path $env:ProgramFiles '7-Zip\7z.exe'
if (-not (Test-Path -LiteralPath $sevenZip -PathType Leaf)) {throw 'The installed 7-Zip executable is missing.'}
# References are SHA256 of the corresponding retained v11 staging files.
# This deliberately targets documents/metadata, never credential files.
$references=@(
 @{member='_manifests\wsl-distros.txt';bytes=437;sha256='0924e4f08184deb2e8b8c440b4accf0e6599260496ba9705b61d36a824c7498a'},
 @{member='Windows_Host\Scripts\Backup Command.txt';bytes=212;sha256='321d8b4c523545eded8c18ac0fea454e4add24413fce1a54c3699698e46ac5c9'},
 @{member='Workspace\Projects\AI-Agents\RNR-Enhanced-Cognee\README.md';bytes=153675;sha256='fa31d902e70d0358be9c322dabdb5ce2e811b274899f6b25634e333aacd2d50c'}
)
$destination='D:\Recovery-Test\Checked-v11-'+[guid]::NewGuid().ToString('N')
if (Test-Path -LiteralPath $destination) {throw 'Recovery destination already exists; preserved.'}
if (-not $PSCmdlet.ShouldProcess($destination,'extract and verify only the three selected files')) {return}
Protect-V12Directory $destination
Write-Host ('Private recovery folder: '+$destination)
Write-Host 'Enter the Windows - Backup archive encryption password from KeePassXC when 7-Zip asks. Do not use the vault master passphrase.'
Write-Host 'Only three small files are written. Reading solid compressed blocks can still take time.'
$arguments=@('x',$archive,('-o'+$destination),'-aos','-spd')+@($references|ForEach-Object {$_.member})
& $sevenZip @arguments
if ($LASTEXITCODE -ne 0) {throw 'Selected extraction did not finish cleanly. Private outputs retained for review.'}
$checks=@()
foreach ($reference in $references) {
 $path=Join-Path $destination $reference.member
 if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {throw 'An expected selected file was not recovered.'}
 $file=Get-Item -LiteralPath $path -Force
 $digest=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
 if ($file.Length -ne $reference.bytes -or $digest -cne $reference.sha256) {throw 'A recovered selected file differs from its retained reference. Preserve it for review.'}
 $checks+=@{member=$reference.member;bytes=$file.Length;sha256=$digest;passed=$true}
}
$after=Get-Item -LiteralPath $archive
if ($after.Length -ne $before.Length -or $after.LastWriteTimeUtc.Ticks -ne $before.LastWriteTimeUtc.Ticks) {
 throw 'The recovery archive changed during the drill; do not record a pass.'
}
$written=@(Get-ChildItem -LiteralPath $destination -Recurse -Force -File)
if ($written.Count -ne $references.Count) {throw 'Extraction wrote an unexpected number of files; preserve the private output for review.'}
$writtenBytes=($written|Measure-Object -Property Length -Sum).Sum
$report=@{complete=$true;passed=$checks.Count;failed=0;folder=$destination;checks=$checks;
 extracted_files=$written.Count;extracted_bytes=$writtenBytes;only_selected_files_written=$true;
 archive_full_sha256_rechecked=$false;previously_verified_manifest_sha256=$expectedArchiveHash;
 application_restore_qualified=$false;independent_remote_provenance_verified=$false;
 automated_file_checks_passed=$true;human_readability_confirmation_pending=$true}
Save-V12Json $report (Join-Path $destination recovery-check.json)
Write-Host ('Actual extracted files: '+$written.Count+'; file-content bytes written: '+$writtenBytes+'. 7-Zip solid-block processing figures can be larger.')
[pscustomobject]$report|Select-Object complete,passed,failed,folder|ConvertTo-Json -Compress
if ($OpenFiles) {
 $notepad=Join-Path $env:SystemRoot 'System32\notepad.exe'
 foreach ($member in @($references[1].member,$references[2].member)) {
  $path=Join-Path $destination $member
  Start-Process -FilePath $notepad -ArgumentList ('"'+$path+'"')
 }
 Write-Host 'Confirm that both text files open and contain readable text. Do not execute the recovered backup command.'
}
