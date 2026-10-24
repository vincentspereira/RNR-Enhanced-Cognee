# Cross-platform engine/copy qualification. Does not establish Windows VSS,
# DPAPI, ACL, Task Scheduler, real cloud or WSL host qualification.
param([string]$WindowsScriptRoot='/mnt/c/Scripts',[string]$Support='',
 [string]$Restic="$HOME/.local/share/rnr-backup-tools/restic/0.19.1/restic")
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (-not $Support) {$Support=Join-Path $WindowsScriptRoot backup-v12}
foreach ($file in @('engine.ps1','policy.ps1','sync.ps1')) {. (Join-Path $Support $file)}
# ACL behavior has a separate mandatory native Windows test.
function Protect-V12Directory([string]$Path) {[IO.Directory]::CreateDirectory($Path)|Out-Null}
$root=Join-Path ([IO.Path]::GetTempPath()) ('rnr-v12-portable-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($root)|Out-Null
$passed=0
function Check([string]$Name,[bool]$Value) {if (-not $Value) {throw "Failed: $Name"};$script:passed++;Write-Host "OK: $Name"}
$wslLine=Join-V12ProcessArguments 'C:\Windows\System32\wsl.exe' @('-d','Ubuntu-Workspace','-u','vincentspereira','--cd','/','--exec','/usr/bin/python3','-I','-c',"print('a value')")
Check wsl_launcher_options_are_not_quoted ($wslLine.StartsWith('-d Ubuntu-Workspace -u vincentspereira --cd / --exec /usr/bin/python3 -I -c '))
Check wsl_python_payload_is_still_quoted ($wslLine.EndsWith('"'+"print('a value')"+'"'))
$ordinary=Join-V12ProcessArguments 'C:\tools\restic.exe' @('-r','C:\repo','value with spaces')
Check other_program_quoting_unchanged ($ordinary -ceq ((@('-r','C:\repo','value with spaces')|ForEach-Object {ConvertTo-V12Argument $_}) -join ' '))
$scriptFiles=@('backup-all-wsl-v12.ps1','Test-WindowsBackup-v12.ps1','Restore-Backup-v12.ps1','Review-HermesFolders-v12.ps1',
 'Review-WindowsWorkerProfile-v12.ps1','Update-WSLBackupTask-v12.ps1','Install-BackupV12Tools.ps1')|ForEach-Object {Get-Item -LiteralPath (Join-Path $WindowsScriptRoot $_)}
foreach ($file in @(Get-ChildItem -LiteralPath $Support -File -Filter '*.ps1')+@($scriptFiles)) {
 $tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
 Check ('parser_'+$file.Name) ($errors.Count -eq 0)
}
# Execute each actual console-summary projection with a hashtable fixture.
# Select-Object cannot select hashtable keys without the PSCustomObject cast.
$summary=@{complete=$true;passed=3;failed=0;skipped=0;artifacts='synthetic'}
$report=@{complete=$true;passed=3;failed=0;folder='synthetic'}
foreach ($name in @('Test-WindowsBackup-v12.ps1','Test-V11RecoveredFiles.ps1')) {
 $tokens=$null;$errors=$null
 $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $WindowsScriptRoot $name),[ref]$tokens,[ref]$errors)
 Check ('parser_'+$name+'_summary_fixture') ($errors.Count -eq 0)
 $pipelines=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.PipelineAst] -and
  $node.Extent.Text -match 'Select-Object complete,passed,failed,' -and $node.Extent.Text -match 'ConvertTo-Json -Compress$'},$true))
 if ($pipelines.Count -ne 1) {throw 'Expected one actual console-summary projection.'}
 $actual=(& ([scriptblock]::Create($pipelines[0].Extent.Text)))|ConvertFrom-Json
 Check ('console_summary_preserves_hashtable_values_'+$name) ($actual.complete -eq $true -and $actual.passed -eq 3 -and $actual.failed -eq 0)
}
$repo=Join-Path $root repository;$pw=Join-Path $root synthetic-password
[IO.File]::WriteAllText($pw,'synthetic-only-not-a-real-password')
function Engine([string[]]$Arguments) {
 $r=Invoke-V12Process $Restic (@('-r',$repo,'--password-file',$pw,'--no-cache')+$Arguments) $null
 if ($r.exit -ne 0) {throw ('Synthetic restic: '+$r.stderr)}
 return $r
}
$null=Engine @('init')
# Run the actual home producer through restic, rather than testing only the
# inventory command (which always supplies a nonempty option). Keep all source
# data synthetic and disable only the test's system inventory.
$homeHelper=Join-Path $Support capture_home.py
$noOptions=if ($false) {@('--hermes')} else {@()}
$homeCommand=Get-V12PythonCommand $homeHelper $noOptions
Check null_home_options_add_no_argument ($homeCommand.Count -eq 4)
Check omitted_home_options_add_no_argument (@(Get-V12PythonCommand $homeHelper).Count -eq 4)
$fixtureHome=Join-Path $root synthetic-home
[IO.Directory]::CreateDirectory($fixtureHome)|Out-Null
[IO.File]::WriteAllText((Join-Path $fixtureHome durable.txt),'synthetic recoverable home content')
$r=Engine (@('backup','--json','--stdin-from-command','--stdin-filename','synthetic-home.tar','--')+$homeCommand+@('--root',$fixtureHome,'--test-no-system-inventory'))
$homeSummary=@($r.stdout -split "`r?`n"|Where-Object {$_}|ForEach-Object {$_|ConvertFrom-Json}|Where-Object {$_.message_type -eq 'summary'})[-1]
$homeRestore=Join-Path $root home-restored
$null=Engine @('restore',$homeSummary.snapshot_id,'--target',$homeRestore,'--verify')
$verifyCode='import sys,tarfile; t=tarfile.open(sys.argv[1]); assert any(m.isfile() and t.extractfile(m).read()==b"synthetic recoverable home content" for m in t.getmembers())'
$verified=Invoke-V12Process '/usr/bin/python3' @('-I','-c',$verifyCode,(Join-Path $homeRestore synthetic-home.tar)) $null
Check streamed_home_recovers_original_file ($verified.exit -eq 0)
$src=Join-Path $root source;[IO.Directory]::CreateDirectory($src)|Out-Null
[IO.File]::WriteAllText((Join-Path $src original.txt),'synthetic valuable data')
$null=Engine @('backup',$src)
$tokens=$null;$errors=$null
$main=[Management.Automation.Language.Parser]::ParseFile((Join-Path $WindowsScriptRoot backup-all-wsl-v12.ps1),[ref]$tokens,[ref]$errors)
$definition=@($main.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Get-ScopeSnapshots'},$true))[0]
. ([scriptblock]::Create($definition.Extent.Text))

$coverageDefinition=@($main.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Assert-CompletedCogneeCoverage'},$true))[0]
. ([scriptblock]::Create($coverageDefinition.Extent.Text))
foreach ($case in @(
 @{name='incomplete_old_run_can_collect_new_scope';done=$false;offline=$false;profiles=$false;blocked=$false},
 @{name='completed_database_only_run_cannot_claim_profiles';done=$true;offline=$false;profiles=$false;blocked=$true},
 @{name='completed_profile_scope_can_retry_cloud';done=$true;offline=$false;profiles=$true;blocked=$false},
 @{name='offline_completed_run_has_distinct_coverage';done=$true;offline=$true;profiles=$false;blocked=$false}
)) {
 $fixture=@{local_complete=$case.done;export_distros=$case.offline;completed=@{}}
 if ($case.profiles) {$fixture.completed['cognee-v2-profiles']=@{snapshot='synthetic'}}
 $caught=$false;try {Assert-CompletedCogneeCoverage $fixture} catch {$caught=$true}
 Check $case.name ($caught -eq $case.blocked)
}

function Invoke-BackupRestic([string[]]$Command,[string]$Label) {return (Engine $Command).stdout}
$taskAst=[Management.Automation.Language.Parser]::ParseFile((Join-Path $WindowsScriptRoot Update-WSLBackupTask-v12.ps1),[ref]$tokens,[ref]$errors)
$taskCoverage=@($taskAst.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Assert-V12ScheduledCoverage'},$true))
if ($taskCoverage.Count -ne 1) {throw 'Expected one actual task coverage guard.'}
. ([scriptblock]::Create($taskCoverage[0].Extent.Text))
foreach ($case in @(
 @{name='task_rejects_database_only_coverage';legacy=$true;omit='';local=$true;cloud=$true;blocked=$true},
 @{name='task_accepts_both_families_and_all_homes';legacy=$false;omit='';local=$true;cloud=$true;blocked=$false},
 @{name='task_rejects_missing_home';legacy=$false;omit='Ubuntu-Hermes';local=$true;cloud=$true;blocked=$true},
 @{name='task_rejects_offline_export_only';legacy=$false;omit='Ubuntu-Workspace';local=$true;cloud=$true;blocked=$true},
 @{name='task_rejects_incomplete_local';legacy=$false;omit='';local=$false;cloud=$true;blocked=$true},
 @{name='task_rejects_incomplete_cloud_copy';legacy=$false;omit='';local=$true;cloud=$false;blocked=$true}
)) {
 $fixture=@{local_complete=$case.local;cloud=@{OneDrive=$true;GoogleDrive=$case.cloud};completed=@{}}
 foreach ($scope in @('cognee-v2-profiles','Ubuntu-Workspace','Ubuntu-Hermes','Ubuntu-Company','Windows-D')) {
  if ($scope -ne $case.omit) {$fixture.completed[$scope]=@{snapshot='synthetic'}}
 }
 if ($case.legacy) {$fixture.completed.Remove('cognee-v2-profiles');$fixture.completed.cognee=@{snapshot='synthetic'}}
 # Read the same PSCustomObject shape produced by the saved JSON checkpoint.
 $fixture=$fixture|ConvertTo-Json -Depth 5|ConvertFrom-Json
 $caught=$false;try {Assert-V12ScheduledCoverage $fixture} catch {$caught=$true}
 Check $case.name ($caught -eq $case.blocked)
}

$null=Engine @('backup','--tag','scope:fixture','--tag','run:old',$src)
Check native_empty_snapshot_array (@(ConvertFrom-V12JsonArray '[]').Count -eq 0)
$one=@(ConvertFrom-V12JsonArray '[{"id":"one"}]')
Check native_single_snapshot_array ($one.Count -eq 1 -and $one[0].id -eq 'one')
$many=@(ConvertFrom-V12JsonArray '[{"id":"one"},{"id":"two"}]')
Check native_multiple_snapshot_array ($many.Count -eq 2 -and $many[1].id -eq 'two')
& {
 # Emulate 5.1's non-enumerating JSON cmdlet on PS7. This is a compatibility
 # regression fixture, not a claim that native Windows qualification passed.
 function ConvertFrom-Json {
  [CmdletBinding()]
  param([Parameter(Mandatory=$true)][string]$InputObject)
  Microsoft.PowerShell.Utility\ConvertFrom-Json -InputObject $InputObject -NoEnumerate
 }
 Check legacy_fixture_emits_empty_array_as_one_object (@(ConvertFrom-Json '[]').Count -eq 1)
 Check legacy_empty_array_normalized (@(ConvertFrom-V12JsonArray '[]').Count -eq 0)
 $one=@(ConvertFrom-V12JsonArray '[{"id":"one"}]')
 Check legacy_single_snapshot_normalized ($one.Count -eq 1 -and $one[0].id -eq 'one')
 $many=@(ConvertFrom-V12JsonArray '[{"id":"one"},{"id":"two"}]')
 Check legacy_multiple_snapshots_normalized ($many.Count -eq 2 -and $many[1].id -eq 'two')
 Check legacy_new_run_has_no_old_snapshot (@(Get-ScopeSnapshots fixture new).Count -eq 0)
 Check legacy_same_run_has_one_snapshot (@(Get-ScopeSnapshots fixture old).Count -eq 1)
}
foreach ($invalid in @('', 'null', '{}', '[null]', '[not-json]')) {
 $caught=$false;try {ConvertFrom-V12JsonArray $invalid|Out-Null} catch {$caught=$true}
 Check ('invalid_snapshot_list_rejected_'+$invalid) $caught
}
Check new_run_cannot_reuse_old_tagged_snapshot (@(Get-ScopeSnapshots fixture new).Count -eq 0)
Check same_run_committed_snapshot_can_resume (@(Get-ScopeSnapshots fixture old).Count -eq 1)
$definition=@($main.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Save-BackupScope'},$true))[0]
. ([scriptblock]::Create($definition.Extent.Text))
$script:run=@{id='new';completed=@{}};$runPath=Join-Path $root checkpoint.json
Save-BackupScope fixture @('--skip-if-unchanged',$src)
Check real_new_run_creates_own_checkpoint (@(Get-ScopeSnapshots fixture new).Count -eq 1 -and (Test-Path $runPath))
$beforeId=$script:run.completed.fixture.snapshot
[IO.File]::WriteAllText((Join-Path $src original.txt),'later correction after completed scope')
Save-BackupScope fixture @($src)
Check retry_reuses_completed_scope ($script:run.completed.fixture.snapshot -eq $beforeId -and @(Get-ScopeSnapshots fixture new).Count -eq 1)
$script:run=@{id='later';completed=@{}}
Save-BackupScope fixture @($src)
Check following_run_captures_later_correction ($script:run.completed.fixture.snapshot -ne $beforeId -and @(Get-ScopeSnapshots fixture later).Count -eq 1)
$recovered=Join-Path $root corrected-recovered
$null=Engine @('restore',$script:run.completed.fixture.snapshot,'--target',$recovered,'--verify')
$files=@(Get-ChildItem -LiteralPath $recovered -Recurse -Force -File -Filter original.txt)
Check corrected_snapshot_extracts_expected_contents ($files.Count -eq 1 -and (Get-Content -LiteralPath $files[0].FullName -Raw) -ceq 'later correction after completed scope')
$older=Join-Path $root older-recovered
$oldSnapshot=@(Get-ScopeSnapshots fixture old)[0].id
$null=Engine @('restore',$oldSnapshot,'--target',$older,'--verify')
$files=@(Get-ChildItem -LiteralPath $older -Recurse -Force -File -Filter original.txt)
Check older_snapshot_extracts_original_contents ($files.Count -eq 1 -and (Get-Content -LiteralPath $files[0].FullName -Raw) -ceq 'synthetic valuable data')
# Exercise the actual production exclusions and native fixture factory. The
# old fixture root was itself excluded; negative-only checks could pass vacuously.
$tokens=$null;$errors=$null
$native=[Management.Automation.Language.Parser]::ParseFile((Join-Path $WindowsScriptRoot Test-WindowsBackup-v12.ps1),[ref]$tokens,[ref]$errors)
$factory=@($native.FindAll({param($node) $node -is [Management.Automation.Language.ForEachStatementAst] -and
 $node.Variable.VariablePath.UserPath -eq 'relative' -and $node.Extent.Text.Contains('weights.gguf')},$true))
if ($factory.Count -ne 1) {throw 'Expected the native policy fixture factory.'}
$policy=Get-V12SourcePolicy (Join-Path $root policy-metadata)
$excludeFile=Join-Path $root production-excludes.txt
[IO.File]::WriteAllLines($excludeFile,[string[]]$policy.excludes,[Text.UTF8Encoding]::new($false))
$filterRoot=Join-Path $root 'RNR-Backups/v12-state/qualification/native-fixture/filter-fixtures'
. ([scriptblock]::Create($factory[0].Extent.Text))
$r=Engine @('backup','--json','--exclude-file',$excludeFile,$filterRoot)
$result=@($r.stdout -split "`r?`n"|Where-Object {$_}|ForEach-Object {$_|ConvertFrom-Json}|Where-Object {$_.message_type -eq 'summary'})[-1]
$listing=(Engine @('ls','--json',$result.snapshot_id)).stdout
Check real_policy_excludes_old_qualification_fixture_root (-not $listing.Contains('mesh.bin') -and -not $listing.Contains('keep.7z') -and -not $listing.Contains('evidence.log'))
$filterRoot=Join-Path $root 'RNR-Backups/policy-fixtures/native-fixture'
. ([scriptblock]::Create($factory[0].Extent.Text))
$r=Engine @('backup','--json',$filterRoot)
$result=@($r.stdout -split "`r?`n"|Where-Object {$_}|ForEach-Object {$_|ConvertFrom-Json}|Where-Object {$_.message_type -eq 'summary'})[-1]
$listing=(Engine @('ls','--json',$result.snapshot_id)).stdout
Check policy_control_lists_all_five_files ($listing.Contains('mesh.bin') -and $listing.Contains('keep.7z') -and $listing.Contains('evidence.log') -and $listing.Contains('weights.gguf') -and $listing.Contains('entertainment-only.txt'))
$r=Engine @('backup','--json','--exclude-file',$excludeFile,$filterRoot)
$result=@($r.stdout -split "`r?`n"|Where-Object {$_}|ForEach-Object {$_|ConvertFrom-Json}|Where-Object {$_.message_type -eq 'summary'})[-1]
$listing=(Engine @('ls','--json',$result.snapshot_id)).stdout
Check real_policy_preserves_geometry_archive_and_log ($listing.Contains('mesh.bin') -and $listing.Contains('keep.7z') -and $listing.Contains('evidence.log'))
Check real_policy_excludes_downloaded_weights_and_entertainment (-not $listing.Contains('weights.gguf') -and -not $listing.Contains('entertainment-only.txt'))
$target=Join-Path $root sync-folder;$receipts=Join-Path $root receipts
$first=Sync-V12Repository $repo $target $receipts
Check first_copy ($first.copied -gt 0 -and $first.reused -eq 0)
$second=Sync-V12Repository $repo $target $receipts
Check unchanged_ciphertext_skipped ($second.copied -eq 0 -and $second.reused -eq $first.copied)
$r=Invoke-V12Process $Restic @('-r',$target,'--password-file',$pw,'--no-cache','check','--read-data') $null
Check copied_repository_full_check ($r.exit -eq 0)
$data=Join-Path $root object;$out=Join-Path $root object-copy
$bytes=[byte[]]::new(8192);$rng=[Security.Cryptography.RandomNumberGenerator]::Create();$rng.GetBytes($bytes);$rng.Dispose()
[IO.File]::WriteAllBytes($data,$bytes);[IO.File]::WriteAllBytes(($out+'.partial-v12'),$bytes[0..2047])
$r=Copy-V12ImmutableFile $data $out (Join-Path $root object-receipt.json)
Check verified_prefix_resume ($r.resumed_bytes -eq 2048 -and (Get-FileHash $data).Hash -eq (Get-FileHash $out).Hash)
$badTarget=Join-Path $root corrupted;[IO.File]::WriteAllText($badTarget,'preserve this')
$caught=$false;try {Copy-V12ImmutableFile $data $badTarget (Join-Path $root bad-receipt.json)|Out-Null} catch {$caught=$true}
Check existing_corruption_preserved ($caught -and (Get-Content -LiteralPath $badTarget -Raw) -eq 'preserve this')
$badPrefix=Join-Path $root bad-prefix;[IO.File]::WriteAllText(($badPrefix+'.partial-v12'),'definitely not the prefix')
$caught=$false;try {Copy-V12ImmutableFile $data $badPrefix (Join-Path $root bad-prefix-receipt.json)|Out-Null} catch {$caught=$true}
Check corrupted_partial_preserved ($caught -and (Get-Content -LiteralPath ($badPrefix+'.partial-v12') -Raw) -eq 'definitely not the prefix')
[IO.Directory]::CreateDirectory((Join-Path $repo locks))|Out-Null
[IO.File]::WriteAllText((Join-Path $repo locks synthetic-lock),'synthetic active lock')
$caught=$false;try {Sync-V12Repository $repo $target $receipts|Out-Null} catch {$caught=$true}
Check live_or_stale_lock_refused $caught
[IO.Directory]::Move((Join-Path $repo locks),(Join-Path $root preserved-locks))
$quoteValues=@('spaces and tabs','contains " quote','ends-with-slash\','mixed\"quoted')
$program='/usr/bin/python3';$code='import json,sys;print(json.dumps(sys.argv[1:]))'
$r=Invoke-V12Process $program (@('-c',$code)+$quoteValues) $null
$actual=@($r.stdout|ConvertFrom-Json)
Check native_process_argument_roundtrip ($r.exit -eq 0 -and ($actual|ConvertTo-Json -Compress) -ceq ($quoteValues|ConvertTo-Json -Compress))
# Exercise the WSL-specific serialization branch with a real subprocess on
# Linux. This does not emulate WSL's raw option parser or replace its native test.
$proxy=Join-Path $root wsl.exe
$null=New-Item -ItemType SymbolicLink -Path $proxy -Target /usr/bin/python3
$r=Invoke-V12Process $proxy (@('-c',$code)+$quoteValues+@('plain-token','/absolute/path','')) $null
$actual=@($r.stdout|ConvertFrom-Json)
$expected=@($quoteValues)+@('plain-token','/absolute/path','')
Check wsl_branch_process_argument_roundtrip ($r.exit -eq 0 -and ($actual|ConvertTo-Json -Compress) -ceq ($expected|ConvertTo-Json -Compress))
@{passed=$passed;failed=0;skipped=0;portable_only=$true;artifacts=$root}|ConvertTo-Json -Compress
