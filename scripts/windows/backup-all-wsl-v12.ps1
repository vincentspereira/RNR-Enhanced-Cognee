<#
Encrypted, deduplicated Windows/WSL backup v12. Requires elevated Windows
PowerShell as the same Windows owner who configured the DPAPI password.
Preserves v9/v10/v11 files, archives and schedules. No automatic deletion.
Use -WhatIf for a read-only preview. Run the native qualification first.
See C:\Scripts\BACKUP-ENCRYPTION-AND-RESTORE-v12.md.
#>
[CmdletBinding(SupportsShouldProcess=$true)]
param(
 [string]$Repository='D:\Archive\Snapshots\restic-v12',
 [string]$OneDriveTarget="$env:USERPROFILE\OneDrive\Vincent\WSL_Backups\restic-v12",
 [string]$GDriveTarget='G:\My Drive\WSL_Backups\restic-v12',
 [string]$PasswordFile="$env:APPDATA\RNR-Backups\archive-password.xml",
 [string]$StateRoot="$env:LOCALAPPDATA\RNR-Backups\v12-state",
 [ValidateRange(1,168)][int]$CogneeMaxBackupAgeHours=48,
 [switch]$RequireCogneeBackup,
 [switch]$LocalOnly,
 [switch]$RetryCloudOnly,
 [switch]$NewRun,
 [switch]$ExportDistros,
 [switch]$CheckData,
 [switch]$RecoverStaleLock,
 [string[]]$Distros=@('Ubuntu-Workspace','Ubuntu-Hermes','Ubuntu-Company')
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $PSHOME Modules
$support=Join-Path $PSScriptRoot backup-v12
foreach ($file in @('engine.ps1','policy.ps1','sync.ps1')) {. (Join-Path $support $file)}
$restic=Join-Path $support 'tools\0.19.1\restic.exe'
$passwordReader=Join-Path $support Read-Password.ps1
$powershell=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$wsl=Join-Path $env:SystemRoot 'System32\wsl.exe'
$runPath=Join-Path $StateRoot active-run.json
$mutex=$null;$locked=$false

function Invoke-BackupRestic {
 param([string[]]$Command,[string]$Label)
 $privateCommand=(ConvertTo-V12Argument $powershell)+' -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File '+
    (ConvertTo-V12Argument $passwordReader)+' -PasswordFile '+(ConvertTo-V12Argument $PasswordFile)
 $arguments=@('--repo',$Repository,'--password-command',$privateCommand,
              '--cache-dir',(Join-Path $StateRoot restic-cache))+ $Command
 $log=if ($Label) {Join-Path $script:runDirectory ($Label+'-'+[guid]::NewGuid().ToString('N'))} else {$null}
 $result=Invoke-V12Process $restic $arguments $log
 if ($result.exit -ne 0) {throw "Backup engine failed for $Label (exit $($result.exit)); private logs retained. No success recorded."}
 return $result.stdout
}
function Get-ScopeSnapshots {
 param([string]$Scope,[string]$RunTag='')
 # One comma-separated tag list means AND. Separate --tag flags mean OR
 # and could wrongly reuse a snapshot from an earlier run.
 $selection='scope:'+$Scope
 if ($RunTag) {$selection+=',run:'+$RunTag}
 $command=@('snapshots','--json','--tag',$selection)
 return @(ConvertFrom-V12JsonArray -Json (Invoke-BackupRestic $command ('inventory-'+$Scope)))
}
function Save-BackupScope {
 param([string]$Name,[string[]]$Arguments)
 if ($script:run.completed.ContainsKey($Name)) {Write-Host "  Reusing completed scope: $Name";return}
 # Recover a committed snapshot if interruption occurred just before the
 # local checkpoint was written. A nonzero producer creates no snapshot.
 $existing=@(Get-ScopeSnapshots $Name $script:run.id)
 if ($existing.Count) {
  $script:run.completed[$Name]=@{snapshot=$existing[-1].id;recovered_after_interruption=$true}
 } else {
  Write-Host "  Backing up $Name (unchanged content is reused)"
  $output=Invoke-BackupRestic (@('backup','--json','--tag',('scope:'+$Name),'--tag',('run:'+$script:run.id))+$Arguments) $Name
  $summaries=@($output -split "`r?`n" | Where-Object {$_} | ForEach-Object {ConvertFrom-Json -InputObject $_} | Where-Object {$_.message_type -eq 'summary'})
  if (-not $summaries.Count) {throw "No completion summary for $Name"}
  $snapshotProperty=$summaries[-1].PSObject.Properties['snapshot_id']
  $snapshot=if ($snapshotProperty) {$snapshotProperty.Value} else {$null}
  if (-not $snapshot) {
   $previous=@(Get-ScopeSnapshots $Name)
   if (-not $previous.Count) {throw 'Unchanged result has no earlier recovery snapshot.'}
   $snapshot=$previous[-1].id
  }
  $script:run.completed[$Name]=@{snapshot=$snapshot;completed_utc=[DateTime]::UtcNow.ToString('o')}
 }
 Save-V12Json $script:run $runPath
}

function Assert-CompletedCogneeCoverage {
 param([hashtable]$Run)
 if ($Run.local_complete -and -not $Run.export_distros -and -not $Run.completed.ContainsKey('cognee-v2-profiles')) {
  throw 'This completed run predates required encrypted Cognee profile coverage. Preserve it and use NewRun after native qualification; RetryCloudOnly cannot upgrade its coverage.'
 }
}

try {
 if ($WhatIfPreference) {
  Write-Host 'PREVIEW ONLY: no files, passwords, snapshots, distros or scheduled tasks changed.'
  Write-Host "Encrypted local repository: $Repository"
  Write-Host 'Windows owner/worker profiles, C:\Scripts, D:\Vincent (except Entertainment), approved D: work products.'
  Write-Host 'Linux homes: native tar, links preserved, caches omitted, Hermes native database/profile capture included.'
  Write-Host 'OneDrive personal originals and downloadable model weights excluded; coverage gaps reported.'
  Write-Host "Cloud repositories: $OneDriveTarget ; $GDriveTarget"
  Write-Host 'Offline full WSL images: explicit -ExportDistros, already stopped distros only. No stop/restart.'
  exit 0
 }
 if ($env:OS -ne 'Windows_NT') {throw 'Run v12 in native Windows PowerShell.'}
 if ($LocalOnly -and $RetryCloudOnly) {throw 'LocalOnly and RetryCloudOnly cannot be combined.'}
 if ($NewRun -and $RetryCloudOnly) {throw 'NewRun and RetryCloudOnly cannot be combined.'}
 $expectedBinary='b0dd1fd21eea5d8fe1325f55f7118213c21f36de8a261e04c0624a5ab9fd7830'
 if ((Get-FileHash -LiteralPath $restic).Hash.ToLowerInvariant() -ne $expectedBinary) {throw 'Pinned backup engine hash differs.'}
 if (-not (Test-Path -LiteralPath $PasswordFile -PathType Leaf)) {throw 'Configure the owner DPAPI archive password first.'}
 $principal=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
 if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {throw 'Use elevated PowerShell under the same Windows owner account (VSS requires it).'}
 $mutex=[Threading.Mutex]::new($false,'Global\RNR-WSL-Backup-v12')
 try {$locked=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$locked=$true}
 if (-not $locked) {throw 'Another v12 backup is already running.'}
 $other=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and
   $_.Name -match '^(powershell|pwsh)\.exe$' -and $_.CommandLine -match '(?i)(?:^|[\\/"\s])backup-all-wsl-v(?:9|10|11|12)\.ps1(?:"|\s|$)'})
 if ($other.Count) {throw 'Another backup version is running. Let it finish before starting v12.'}
 $qualification=Join-Path $StateRoot 'qualification\latest-pass.json'
 if (-not (Test-Path -LiteralPath $qualification)) {throw 'First run C:\Scripts\Test-WindowsBackup-v12.ps1 in elevated Windows PowerShell. Current v11 backups are unchanged.'}
 $proof=Get-Content -LiteralPath $qualification -Raw|ConvertFrom-Json
 if (-not $proof.complete -or -not $proof.native_windows -or $proof.failed -ne 0 -or $proof.skipped -ne 0) {throw 'Native v12 qualification has not passed.'}
 foreach ($entry in $proof.source_hashes.PSObject.Properties) {
  if (-not (Test-Path -LiteralPath $entry.Name) -or (Get-FileHash -LiteralPath $entry.Name).Hash -ne $entry.Value) {throw 'A v12 file changed since qualification. Repeat the native test before real backup.'}
 }
 Protect-V12Directory $StateRoot
 $metadata=Join-Path $StateRoot recovery-metadata
 if ($RetryCloudOnly) {
  $savedPolicy=Join-Path $metadata coverage-policy.json
  if (-not (Test-Path -LiteralPath $savedPolicy)) {throw 'Completed run source policy is missing; cloud-only retry cannot verify destination boundaries.'}
  $policy=Get-Content -LiteralPath $savedPolicy -Raw|ConvertFrom-Json
 } else {
  $policy=Get-V12SourcePolicy $metadata
  Write-V12WindowsInventory $metadata
 }
 $clouds=@($OneDriveTarget,$GDriveTarget)
 Assert-V12SeparatePaths $policy.sources (@($Repository)+$clouds) $policy.excluded_subtrees
 Assert-V12SeparatePaths @($Repository) $clouds
 if ($Repository.StartsWith($StateRoot,[StringComparison]::OrdinalIgnoreCase)) {throw 'Repository cannot be inside its state directory.'}
 # Retain incomplete run IDs: finished scopes are reused on retry, not recaptured.
 if ((Test-Path -LiteralPath $runPath) -and -not $NewRun) {
  $old=Get-Content -LiteralPath $runPath -Raw|ConvertFrom-Json
  if ($old.repository -ne $Repository) {throw 'State belongs to another repository; choose a separate StateRoot.'}
  if ($RetryCloudOnly -or -not $old.local_complete) {
   $script:run=@{id=$old.id;repository=$old.repository;local_complete=$old.local_complete;completed=@{};cloud=@{};export_distros=$old.export_distros}
   foreach ($p in $old.completed.PSObject.Properties) {$script:run.completed[$p.Name]=$p.Value}
  if (-not $RetryCloudOnly -and $ExportDistros.IsPresent -ne [bool]$old.export_distros) {throw 'Resume with the same ExportDistros choice, or choose NewRun.'}
  }
 }
 if (-not (Get-Variable run -Scope Script -ErrorAction SilentlyContinue)) {
  if ($RetryCloudOnly) {throw 'No completed local run is available for cloud retry.'}
  $script:run=@{id=([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8));
   repository=$Repository;local_complete=$false;completed=@{};cloud=@{};export_distros=$ExportDistros.IsPresent}
 }
 $script:runDirectory=Join-Path $StateRoot ('runs\'+$script:run.id)
 Protect-V12Directory $script:runDirectory
 Save-V12Json $policy (Join-Path $metadata coverage-policy.json)
 Save-V12Json $script:run $runPath
 if (-not (Test-Path -LiteralPath (Join-Path $Repository config))) {
  if (Test-Path -LiteralPath $Repository) {
   if (@(Get-ChildItem -LiteralPath $Repository -Force).Count) {throw 'Repository path is nonempty but has no restic config; nothing overwritten.'}
  }
  Protect-V12Directory $Repository
  $null=Invoke-BackupRestic @('init','--repository-version','2') init
 }
 if ($RecoverStaleLock) {
  $runningEngine=@(Get-CimInstance Win32_Process|Where-Object {$_.Name -eq 'restic.exe'})
  if ($runningEngine.Count) {throw 'A restic process is running. No lock recovery attempted.'}
  # Explicit operator option after interruption; built-in unlock removes stale
  # locks only. Never use --remove-all or bypass an active repository lock.
  $null=Invoke-BackupRestic @('unlock') operator-stale-lock-recovery
 }
 Assert-CompletedCogneeCoverage $script:run
 if ($RetryCloudOnly -and -not $script:run.local_complete) {throw 'Local run is incomplete; resume without RetryCloudOnly.'}
 if (-not $RetryCloudOnly -and -not $script:run.local_complete) {
  if (-not $RequireCogneeBackup) {Write-Warning 'Cognee service backup coverage is mandatory in v12; RequireCogneeBackup is retained for task compatibility.'}
  if ($ExportDistros) {
   $running=Invoke-V12Process $wsl @('--list','--running','--quiet') $null
   if ($running.exit -ne 0) {throw 'Cannot verify stopped distros for offline images.'}
   $names=@(($running.stdout.Replace([string][char]0,'') -split "`r?`n")|ForEach-Object {$_.Trim()}|Where-Object {$_})
   foreach ($distro in $Distros) {
    if ($distro -notin @('Ubuntu-Workspace','Ubuntu-Hermes','Ubuntu-Company')) {throw 'Unreviewed distro name.'}
    if ($distro -in $names) {throw 'Offline image requires already stopped distros. Close sessions and stop services in an agreed maintenance window. Nothing was stopped by this script.'}
   }
   foreach ($distro in $Distros) {
    Save-BackupScope ('offline-'+$distro) @('--stdin-from-command','--stdin-filename',($distro+'-full-distro.tar'),'--',$wsl,'--export',$distro,'-')
   }
  } else {
  $native=Get-V12PythonCommand (Join-Path $support capture_cognee.py) @('--max-age-hours',[string]$CogneeMaxBackupAgeHours)
  # A versioned scope prevents interrupted old database-only checkpoints from
  # satisfying the new database AND restricted-profile collection requirement.
  Save-BackupScope cognee-v2-profiles (@('--stdin-from-command','--stdin-filename','enhanced-cognee-encrypted.tar','--',$wsl,'-d','Ubuntu-Hermes','-u','root','--cd','/','--exec')+$native)
  foreach ($distro in $Distros) {
   if ($distro -notin @('Ubuntu-Workspace','Ubuntu-Hermes','Ubuntu-Company')) {throw 'Unreviewed distro; use one of the three reviewed names.'}
   $options=@(if ($distro -eq 'Ubuntu-Hermes') {'--hermes'})
   if (-not $script:run.completed.ContainsKey($distro)) {
    $helper=Join-Path $support capture_home.py
    $helperHash=(Get-FileHash -LiteralPath $helper).Hash
    $inventory=Get-V12PythonCommand $helper @('--inventory-only')
    $beforeLog=Join-Path $script:runDirectory ('home-inventory-'+$distro+'-'+[guid]::NewGuid().ToString('N'))
    $before=Invoke-V12Process $wsl (@('-d',$distro,'-u','vincentspereira','--cd','/','--exec')+$inventory) $beforeLog
    if ($before.exit -ne 0) {throw ('Home inventory failed for '+$distro+'; private diagnostics retained in the run evidence')}
    $fingerprint=($before.stdout|ConvertFrom-Json).fingerprint
    $cachePath=Join-Path $StateRoot ($distro+'-last-home.json')
    if (Test-Path -LiteralPath $cachePath) {
     $prior=Get-Content -LiteralPath $cachePath -Raw|ConvertFrom-Json
     if ($prior.fingerprint -eq $fingerprint -and $prior.helper_sha256 -eq $helperHash) {
      $confirmed=@(ConvertFrom-V12JsonArray -Json (Invoke-BackupRestic @('snapshots','--json',$prior.snapshot) ('reuse-'+$distro)))
      if ($confirmed.Count -eq 1) {
       $script:run.completed[$distro]=@{snapshot=$prior.snapshot;unchanged_home_reused=$true}
       Save-V12Json $script:run $runPath
       Write-Host ('  Reusing unchanged Linux home snapshot: '+$distro)
      }
     }
    }
    $native=Get-V12PythonCommand $helper $options
    Save-BackupScope $distro (@('--stdin-from-command','--stdin-filename',($distro+'-home.tar'),'--',$wsl,'-d',$distro,'-u','vincentspereira','--cd','/','--exec')+$native)
    $afterLog=Join-Path $script:runDirectory ('post-capture-inventory-'+$distro+'-'+[guid]::NewGuid().ToString('N'))
    $after=Invoke-V12Process $wsl (@('-d',$distro,'-u','vincentspereira','--cd','/','--exec')+$inventory) $afterLog
    if ($after.exit -ne 0) {throw ('Post-capture home inventory failed for '+$distro)}
    if (($after.stdout|ConvertFrom-Json).fingerprint -eq $fingerprint) {
     Save-V12Json @{snapshot=$script:run.completed[$distro].snapshot;fingerprint=$fingerprint;helper_sha256=$helperHash} $cachePath
    } else {Write-Warning ($distro+': home changed during capture; next run will collect again. Individual database images are consistent; the whole live home is not one atomic point in time.')}
   } else {Write-Host ('  Reusing completed scope: '+$distro)}
  }
  }
  $list=Join-Path $metadata windows-sources.txt
  $filters=Join-Path $metadata windows-excludes.txt
  [IO.File]::WriteAllLines($list,[string[]]$policy.sources,[Text.UTF8Encoding]::new($false))
  [IO.File]::WriteAllLines($filters,[string[]]$policy.excludes,[Text.UTF8Encoding]::new($false))
  Save-BackupScope Windows-D @('--use-fs-snapshot','--exclude-cloud-files','--skip-if-unchanged','--files-from-verbatim',$list,'--exclude-file',$filters)
  $null=Invoke-BackupRestic @('check') metadata-check
  $script:run.local_complete=$true
  Save-V12Json $script:run (Join-Path $script:runDirectory local-complete.json)
  Save-V12Json $script:run $runPath
 }
 if ($CheckData) {$null=Invoke-BackupRestic @('check','--read-data') full-ciphertext-check}
 if (-not $LocalOnly) {
  foreach ($cloud in @(@{name='OneDrive';path=$OneDriveTarget},@{name='GoogleDrive';path=$GDriveTarget})) {
   $parent=Split-Path $cloud.path -Parent
   if (-not (Test-Path -LiteralPath $parent -PathType Container)) {throw ($cloud.name+' sync parent is unavailable; local snapshots retained. RetryCloudOnly can resume later.')}
   $result=Sync-V12Repository $Repository $cloud.path (Join-Path $StateRoot ('receipts\'+$cloud.name))
   $script:run.cloud[$cloud.name]=$result
   Save-V12Json $script:run $runPath
   Write-Host ("  {0}: {1} new objects, {2} reused objects; cloud server confirmation still required." -f $cloud.name,$result.copied,$result.reused)
  }
 }
 Write-Host 'OK: requested backup stages completed. Existing generations retained.'
 Write-Host 'GAPS: OneDrive personal originals, downloadable weights, Windows OS image, and offline WSL images are separate.'
 Write-Host 'Cloud sync-folder verification is not proof of completed upload. Check both clients and test a downloaded recovery.'
 exit 0
} catch {
 Write-Error -Message ('Backup v12 stopped: '+$_.Exception.Message) -ErrorAction Continue
 if (Get-Variable runDirectory -Scope Script -ErrorAction SilentlyContinue) {Write-Host ('Private run evidence: '+$script:runDirectory)}
 exit 1
} finally {
 if ($locked -and $mutex) {$mutex.ReleaseMutex()}
 if ($mutex) {$mutex.Dispose()}
}
