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
$src=Join-Path $root source;[IO.Directory]::CreateDirectory($src)|Out-Null
[IO.File]::WriteAllText((Join-Path $src original.txt),'synthetic valuable data')
$null=Engine @('backup',$src)
$tokens=$null;$errors=$null
$main=[Management.Automation.Language.Parser]::ParseFile((Join-Path $WindowsScriptRoot backup-all-wsl-v12.ps1),[ref]$tokens,[ref]$errors)
$definition=@($main.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Get-ScopeSnapshots'},$true))[0]
. ([scriptblock]::Create($definition.Extent.Text))
function Invoke-BackupRestic([string[]]$Command,[string]$Label) {return (Engine $Command).stdout}
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
@{passed=$passed;failed=0;skipped=0;portable_only=$true;artifacts=$root}|ConvertTo-Json -Compress
