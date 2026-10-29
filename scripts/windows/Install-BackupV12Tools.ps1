# Portable, pinned free/open-source tool. No PATH, machine policy or task change.
[CmdletBinding(SupportsShouldProcess=$true)]
param()
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $PSHOME Modules
$folder=Join-Path $PSScriptRoot 'backup-v12\tools\0.19.1'
$binary=Join-Path $folder restic.exe
$binaryHash='b0dd1fd21eea5d8fe1325f55f7118213c21f36de8a261e04c0624a5ab9fd7830'
if (Test-Path -LiteralPath $binary) {
 if ((Get-FileHash -LiteralPath $binary).Hash -ne $binaryHash) {throw 'Existing engine differs; preserved without replacement.'}
 Write-Host 'OK: pinned restic 0.19.1 already installed and verified.';return
}
if (-not $PSCmdlet.ShouldProcess($folder,'download official portable restic 0.19.1 and verify pinned archive/binary hashes')) {return}
[IO.Directory]::CreateDirectory($folder)|Out-Null
$zip=Join-Path $folder ('official-download-'+[guid]::NewGuid().ToString('N')+'.zip')
$url='https://github.com/restic/restic/releases/download/v0.19.1/restic_0.19.1_windows_amd64.zip'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
if ((Get-FileHash -LiteralPath $zip).Hash -ne 'da948ad707ed690426473aaba2046cd61f8f90f6f0e7dab6be0d5796531de67d') {throw 'Official download hash differs; retained without execution.'}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive=[IO.Compression.ZipFile]::OpenRead($zip)
try {
 $entries=@($archive.Entries|Where-Object {$_.Name -like '*.exe'})
 if ($entries.Count -ne 1) {throw 'Unexpected official archive layout.'}
 $partial=$binary+'.verified-download'
 if (Test-Path -LiteralPath $partial) {throw 'A prior partial exists; retained for review.'}
 $source=$entries[0].Open();$target=[IO.File]::Open($partial,[IO.FileMode]::CreateNew)
 try {$source.CopyTo($target);$target.Flush($true)} finally {$source.Dispose();$target.Dispose()}
 if ((Get-FileHash -LiteralPath $partial).Hash -ne $binaryHash) {throw 'Engine hash differs; retained without execution.'}
 [IO.File]::Move($partial,$binary)
} finally {$archive.Dispose()}
Write-Host 'OK: portable restic 0.19.1 installed. Official download retained; no backup started.'
