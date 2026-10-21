# Native synthetic qualification and local policy/recovery inventory checks.
# Does not back up real source contents, upload data or edit scheduled tasks.
[CmdletBinding(SupportsShouldProcess=$true)]
param([string]$ArtifactsRoot="$env:LOCALAPPDATA\RNR-Backups\v12-state\qualification")
$ErrorActionPreference='Stop'
if ($WhatIfPreference) {Write-Host 'Preview only: synthetic encrypted backup, interrupted copy, VSS and recovery tests. No real backup/cloud upload/task changes.';return}
if ($env:OS -ne 'Windows_NT' -or $PSVersionTable.PSEdition -ne 'Desktop') {throw 'Run this qualification in native Windows PowerShell 5.1.'}
$env:PSModulePath=Join-Path $PSHOME Modules
$principal=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {throw 'Use elevated Windows PowerShell under the backup owner account.'}
$support=Join-Path $PSScriptRoot backup-v12
foreach ($file in @('engine.ps1','policy.ps1','sync.ps1')) {. (Join-Path $support $file)}
$run=Join-Path $ArtifactsRoot ('native-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+[guid]::NewGuid().ToString('N'))
Protect-V12Directory $run
$checks=[Collections.Generic.List[object]]::new()
function Check([string]$Name,[bool]$Pass) {
 $checks.Add(@{name=$Name;passed=$Pass});if (-not $Pass) {throw ('Failed: '+$Name)}
}
$restic=Join-Path $support 'tools\0.19.1\restic.exe'
$repo=Join-Path $run repository
$dpapi=Join-Path $run synthetic-dpapi.xml
$passwordCommand=(ConvertTo-V12Argument "$PSHOME\powershell.exe")+' -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File '+
 (ConvertTo-V12Argument (Join-Path $support Read-Password.ps1))+' -PasswordFile '+(ConvertTo-V12Argument $dpapi)
function Engine([string[]]$Arguments,[switch]$ExpectFailure) {
 $r=Invoke-V12Process $restic (@('-r',$repo,'--password-command',$passwordCommand,'--cache-dir',(Join-Path $run cache))+$Arguments) $null
 if (-not $ExpectFailure -and $r.exit -ne 0) {throw ('Synthetic engine failed (exit '+$r.exit+').')}
 return $r
}
try {
 $rootNames=@('backup-all-wsl-v12.ps1','Test-WindowsBackup-v12.ps1','Restore-Backup-v12.ps1','Review-HermesFolders-v12.ps1',
  'Review-WindowsWorkerProfile-v12.ps1','Update-WSLBackupTask-v12.ps1','Install-BackupV12Tools.ps1')
 $rootFiles=@($rootNames|ForEach-Object {Get-Item -LiteralPath (Join-Path $PSScriptRoot $_)})
 foreach ($path in @($rootFiles|ForEach-Object {$_.FullName}) + @(Get-ChildItem -LiteralPath $support -Filter '*.ps1'|ForEach-Object {$_.FullName})) {
  $tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
  Check ('native_parse_'+[IO.Path]::GetFileName($path)) (@($errors).Count -eq 0)
 }
 Check pinned_engine ((Get-FileHash -LiteralPath $restic).Hash -eq 'b0dd1fd21eea5d8fe1325f55f7118213c21f36de8a261e04c0624a5ab9fd7830')
 Check empty_json_array_is_no_snapshot (@(ConvertFrom-V12JsonArray '[]').Count -eq 0)
 $one=@(ConvertFrom-V12JsonArray '[{"id":"fixture-one"}]')
 Check single_json_snapshot_is_one_item ($one.Count -eq 1 -and $one[0].id -eq 'fixture-one')
 $many=@(ConvertFrom-V12JsonArray '[{"id":"fixture-one"},{"id":"fixture-two"}]')
 Check multiple_json_snapshots_are_separate_items ($many.Count -eq 2 -and $many[1].id -eq 'fixture-two')
 $random=[byte[]]::new(40);$rng=[Security.Cryptography.RandomNumberGenerator]::Create();$rng.GetBytes($random);$rng.Dispose()
 $secret=[Convert]::ToBase64String($random);$secure=ConvertTo-SecureString $secret -AsPlainText -Force
 $secure|Export-Clixml -LiteralPath $dpapi;$secure.Dispose()
 Check dpapi_ciphertext (-not (Get-Content -LiteralPath $dpapi -Raw).Contains($secret))
 $r=Engine @('init');Check password_command_child_pipe ($r.exit -eq 0 -and -not $r.stdout.Contains($secret) -and -not $r.stderr.Contains($secret))
 $src=Join-Path $run source;[IO.Directory]::CreateDirectory($src)|Out-Null
 [IO.File]::WriteAllBytes((Join-Path $src unchanged.bin),$random*32768)
 [IO.File]::WriteAllText((Join-Path $src change.txt),'before')
 [IO.File]::WriteAllText((Join-Path $src delete.txt),'older version')
 $r=Engine @('backup','--json','--use-fs-snapshot',$src)
 $summary=@($r.stdout -split "`r?`n"|Where-Object {$_}|ForEach-Object {$_|ConvertFrom-Json}|Where-Object {$_.message_type -eq 'summary'})[-1]
 $first=$summary.snapshot_id;Check native_vss_backup ([bool]$first)
 $r=Engine @('backup','--json',$src)
 $summary=@($r.stdout -split "`r?`n"|Where-Object {$_}|ForEach-Object {$_|ConvertFrom-Json}|Where-Object {$_.message_type -eq 'summary'})[-1]
 Check unchanged_data_reused ($summary.data_added -lt 8192 -and $summary.data_blobs -eq 0)
 $null=Engine @('backup','--tag','scope:fixture','--tag','run:old',$src)
 $r=Engine @('snapshots','--json','--tag','scope:fixture,run:new')
 Check new_run_cannot_reuse_old_tagged_snapshot (@(ConvertFrom-V12JsonArray $r.stdout).Count -eq 0)
 $r=Engine @('snapshots','--json','--tag','scope:fixture,run:old')
 Check same_run_snapshot_can_resume (@(ConvertFrom-V12JsonArray $r.stdout).Count -eq 1)
 [IO.File]::WriteAllText((Join-Path $src change.txt),'after-correction')
 Move-Item -LiteralPath (Join-Path $src delete.txt) -Destination (Join-Path $run preserved-delete.txt)
 $r=Engine @('backup','--json',$src)
 $summary=@($r.stdout -split "`r?`n"|Where-Object {$_}|ForEach-Object {$_|ConvertFrom-Json}|Where-Object {$_.message_type -eq 'summary'})[-1]
 $latest=$summary.snapshot_id
 $out=Join-Path $run recovered
 $null=Engine @('restore',$latest,'--target',$out)
 $change=@(Get-ChildItem -LiteralPath $out -Recurse -File -Filter change.txt)
 Check corrected_recovery ($change.Count -eq 1 -and (Get-Content -LiteralPath $change[0].FullName -Raw) -eq 'after-correction')
 Check deletion_does_not_reappear (@(Get-ChildItem -LiteralPath $out -Recurse -File -Filter delete.txt).Count -eq 0)
 $older=Join-Path $run older
 $null=Engine @('restore',$first,'--target',$older)
 Check older_version_preserved (@(Get-ChildItem -LiteralPath $older -Recurse -File -Filter delete.txt).Count -eq 1)
 $before=@(ConvertFrom-V12JsonArray (Engine @('snapshots','--json')).stdout)
 $producer=Join-Path $run failing-producer.ps1
 [IO.File]::WriteAllText($producer,"[Console]::Out.Write('partial synthetic output');exit 7")
 $r=Engine @('backup','--stdin-from-command','--stdin-filename','bad.tar','--',"$PSHOME\powershell.exe",'-NoProfile','-ExecutionPolicy','RemoteSigned','-File',$producer) -ExpectFailure
 Check producer_failure_reported ($r.exit -ne 0)
 $after=@(ConvertFrom-V12JsonArray (Engine @('snapshots','--json')).stdout)
 Check failed_producer_no_snapshot ($before.Count -eq $after.Count)
 $bad=$false;try {Assert-V12SeparatePaths @($src) @((Join-Path $src repo))} catch {$bad=$true};Check recursion_rejected $bad
 $bad=$false;try {Assert-V12SeparatePaths @((Join-Path $src child)) @($src) @($src)} catch {$bad=$true};Check source_inside_destination_rejected_even_if_excluded $bad
 $bad=$false;try {Assert-V12SeparatePaths @($src,(Join-Path $src child)) @((Join-Path $run other))} catch {$bad=$true};Check nested_sources_rejected $bad
 $target=Join-Path $run synthetic-cloud-repository;$receipts=Join-Path $run receipts
 $r=Sync-V12Repository $repo $target $receipts;Check initial_encrypted_copy ($r.copied -gt 0)
 $r=Sync-V12Repository $repo $target $receipts;Check repeat_cloud_copy_reused ($r.copied -eq 0 -and $r.reused -gt 0)
 $resumeSource=Join-Path $run source-object;$resumeTarget=Join-Path $run resumed-object
 $bytes=[byte[]]::new(4096);$rng=[Security.Cryptography.RandomNumberGenerator]::Create();$rng.GetBytes($bytes);$rng.Dispose()
 [IO.File]::WriteAllBytes($resumeSource,$bytes);[IO.File]::WriteAllBytes(($resumeTarget+'.partial-v12'),$bytes[0..1023])
 $r=Copy-V12ImmutableFile $resumeSource $resumeTarget (Join-Path $run resume-receipt.json)
 Check interrupted_object_resumed ($r.resumed_bytes -eq 1024 -and (Get-FileHash $resumeSource).Hash -eq (Get-FileHash $resumeTarget).Hash)
 $corruptTarget=Join-Path $run corrupt-existing;[IO.File]::WriteAllText($corruptTarget,'preserve me')
 $bad=$false;try {Copy-V12ImmutableFile $resumeSource $corruptTarget (Join-Path $run corrupt-receipt.json)|Out-Null} catch {$bad=$true}
 Check corrupt_existing_refused_and_preserved ($bad -and (Get-Content $corruptTarget -Raw) -eq 'preserve me')
 $null=Engine @('check','--read-data');Check local_integrity_check $true
 $r=Invoke-V12Process $restic @('-r',$target,'--password-command',$passwordCommand,'check','--read-data') $null
 Check copied_repository_decrypts_and_checks ($r.exit -eq 0)
 $policy=Get-V12SourcePolicy (Join-Path $run recovery-metadata)
 Write-V12WindowsInventory (Join-Path $run recovery-metadata)
 $software=Get-Content -LiteralPath (Join-Path $run recovery-metadata\windows-software-recovery.json) -Raw|ConvertFrom-Json
 Check local_windows_recovery_inventory ([bool]$software.os_version -and $software.is_windows_system_image -eq $false)
 Assert-V12SeparatePaths $policy.sources @('D:\Archive\Snapshots\restic-v12',"$env:USERPROFILE\OneDrive\Vincent\WSL_Backups\restic-v12",'G:\My Drive\WSL_Backups\restic-v12') $policy.excluded_subtrees
 Check real_source_policy_has_no_nested_or_recursive_roots $true
 Check coverage_gaps_explicit ($policy.one_drive_originals_separate -and -not $policy.downloaded_weights_included -and $policy.distro_images_separate)
 $filterRoot=Join-Path $run filter-fixtures
 foreach ($relative in @('AI-Models\studio\weights.gguf','AI-Models\studio\mesh.bin','AI-Models\studio\keep.7z','AI-Models\studio\evidence.log','Vincent\Personal-Workspace\Entertainment\entertainment-only.txt')) {
  $file=Join-Path $filterRoot $relative;[IO.Directory]::CreateDirectory((Split-Path $file -Parent))|Out-Null
  [IO.File]::WriteAllText($file,'synthetic fixture')
 }
 $excludeFile=Join-Path $run reviewed-excludes.txt
 [IO.File]::WriteAllLines($excludeFile,[string[]]$policy.excludes,[Text.UTF8Encoding]::new($false))
 $r=Engine @('backup','--json','--exclude-file',$excludeFile,$filterRoot)
 $summary=@($r.stdout -split "`r?`n"|Where-Object {$_}|ForEach-Object {$_|ConvertFrom-Json}|Where-Object {$_.message_type -eq 'summary'})[-1]
 $listing=(Engine @('ls','--json',$summary.snapshot_id)).stdout
 Check downloaded_weight_excluded (-not $listing.Contains('weights.gguf'))
 Check entertainment_excluded (-not $listing.Contains('entertainment-only.txt'))
 Check original_geometry_binary_kept ($listing.Contains('mesh.bin'))
 Check work_product_archive_and_log_kept ($listing.Contains('keep.7z') -and $listing.Contains('evidence.log'))
 $r=Invoke-V12Process "$PSHOME\powershell.exe" @('-NoProfile','-ExecutionPolicy','RemoteSigned','-File',(Join-Path $PSScriptRoot backup-all-wsl-v12.ps1),'-WhatIf') $null
 Check main_read_only_preview ($r.exit -eq 0 -and $r.stdout.Contains('PREVIEW ONLY'))
 $hashes=@{}
 foreach ($file in $rootFiles+@(Get-ChildItem $support -File -Recurse|Where-Object {$_.Extension -in @('.ps1','.py','.exe')})) {
  $hashes[$file.FullName]=(Get-FileHash -LiteralPath $file.FullName).Hash
 }
 $summary=@{complete=$true;passed=$checks.Count;failed=0;skipped=0;checks=@($checks.ToArray());artifacts=$run;source_hashes=$hashes;
  native_windows=$true;actual_homes_and_profiles_qualified=$false;real_cloud_upload_verified=$false;offline_wsl_restore_verified=$false}
 Save-V12Json $summary (Join-Path $run summary.json)
 Save-V12Json $summary (Join-Path $ArtifactsRoot latest-pass.json)
 $summary|Select-Object complete,passed,failed,skipped,artifacts|ConvertTo-Json -Compress
 exit 0
} catch {
 Save-V12Json @{complete=$false;checks=@($checks.ToArray());error=$_.Exception.Message;artifacts=$run} (Join-Path $run summary.json)
 Write-Error -Message ('Native qualification failed: '+$_.Exception.Message) -ErrorAction Continue
 exit 1
} finally {$secret=$null;$random=$null}
