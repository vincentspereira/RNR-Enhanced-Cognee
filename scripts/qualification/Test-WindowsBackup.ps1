# Native Windows tests. Never runs the full backup, uploads or edits schedules.
[CmdletBinding(SupportsShouldProcess=$true)]
param(
 [string]$BackupScript='C:\Scripts\backup-all-wsl-v11.ps1',
 [string]$ArtifactsRoot="$env:LOCALAPPDATA\RNR-Backups\qualification",
 [switch]$CollectCognee,
 [string]$TaskName=''
)
$ErrorActionPreference='Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {throw 'Native Windows required.'}
if ($PSVersionTable.PSEdition -ne 'Desktop' -or $PSVersionTable.PSVersion.Major -ne 5) {
 throw 'Use native Windows PowerShell 5.1 for this qualification.'
}
if ($WhatIfPreference) {
 Write-Host 'Preview only: native synthetic encryption/restore checks, optional encrypted Cognee collection, no full backup or cloud upload.'
 return
}
# The desktop launcher can inherit PowerShell 7's module search path. Select
# only this interpreter's built-in modules for this test process and children.
# No saved environment variable or user profile is changed.
$env:PSModulePath=Join-Path $PSHOME 'Modules'
$run=Join-Path $ArtifactsRoot ('native-'+(Get-Date -Format yyyyMMdd-HHmmss)+'-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $run | Out-Null
$acl=New-Object Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true,$false)
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
foreach ($allowed in @($sid,[Security.Principal.SecurityIdentifier]::new('S-1-5-18'))) {
 $rule=New-Object Security.AccessControl.FileSystemAccessRule($allowed,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
 $acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $run -AclObject $acl
$checks=[Collections.Generic.List[object]]::new()
function Check([string]$Name,[bool]$Passed) {
 $checks.Add([pscustomobject]@{name=$Name;passed=$Passed})
 if (-not $Passed) {throw ('Failed: '+$Name)}
}
function Read-SecretText([Security.SecureString]$Secret) {
 $p=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secret)
 try {return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($p)}
 finally {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p)}
}
try {
 $tokens=$null;$parseErrors=$null
 $ast=[Management.Automation.Language.Parser]::ParseFile($BackupScript,[ref]$tokens,[ref]$parseErrors)
 Check 'native_parser' (@($parseErrors).Count -eq 0)
 # Only named definitions are evaluated. Full-script side effects cannot run.
 $wanted=@('Write-Task','Write-Ok','Write-Bad','Invoke-SevenZip','Test-SevenZipArchive',
 'Invoke-WslBinaryExport','Backup-EnhancedCognee','Write-RestoreManifest','Test-CloudFilesPresent')
 foreach ($name in $wanted) {
  $d=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)|Where-Object {$_.Name -eq $name})
  Check ('one_definition_'+$name) ($d.Count -eq 1)
  . ([scriptblock]::Create($d[0].Extent.Text))
 }
 $sevenZip=Get-Item -LiteralPath "$env:ProgramFiles\7-Zip\7z.exe"
 $rng=[Security.Cryptography.RandomNumberGenerator]::Create()
 $random=New-Object byte[] 36;$rng.GetBytes($random);$rng.Dispose()
 $secret=[Convert]::ToBase64String($random)
 $secure=ConvertTo-SecureString -String $secret -AsPlainText -Force
 $dpapi=Join-Path $run synthetic-dpapi.xml
 $secure|Export-Clixml -LiteralPath $dpapi
 Check 'dpapi_no_plaintext' (-not (Get-Content $dpapi -Raw).Contains($secret))
 $recovered=Import-Clixml -LiteralPath $dpapi
 Check 'dpapi_same_account_roundtrip' ((Read-SecretText $recovered) -ceq $secret)
 $code='$ErrorActionPreference="Stop";$s=Import-Clixml -LiteralPath "'+$dpapi+'";if ($s -isnot [Security.SecureString]) {exit 2};$p=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($s);try {if ([Runtime.InteropServices.Marshal]::PtrToStringBSTR($p).Length -lt 20) {exit 3}} finally {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p);$s.Dispose()};exit 0'
 $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($code))
 & "$PSHOME\powershell.exe" -NoProfile -NonInteractive -EncodedCommand $encoded
 Check 'dpapi_unattended_child_process' ($LASTEXITCODE -eq 0)
 $secure.Dispose();$recovered.Dispose()
 $source=Join-Path $run source;$chain=Join-Path $run chain;$diffs=Join-Path $chain diffs;$out=Join-Path $run restored
 New-Item -ItemType Directory -Path $source,$diffs,$out|Out-Null
 [IO.File]::WriteAllText((Join-Path $source unchanged.txt),'unchanged')
 [IO.File]::WriteAllText((Join-Path $source change.txt),'before')
 [IO.File]::WriteAllText((Join-Path $source delete.txt),'synthetic deletion')
 $base=Join-Path $chain base.7z
 Invoke-SevenZip $sevenZip @('a','-t7z','-mx=1',("-p"+$secret),'-mhe=on',$base,(Join-Path $source '*'))|Out-File (Join-Path $run create.log)
 Check 'encrypted_base_created' ($LASTEXITCODE -eq 0)
 Check 'encrypted_base_integrity' (Test-SevenZipArchive $sevenZip $base $secret)
 # PowerShell 5.1 can promote native stderr to a terminating error under Stop.
 # These two deliberately failing native calls must retain their exit codes.
 $ErrorActionPreference='Continue'
 try {
  $denied=-not (Test-SevenZipArchive $sevenZip $base synthetic-wrong-password 2>$null)
  $headers=& $sevenZip.FullName l $base -psynthetic-wrong-password 2>$null
  $listingExit=$LASTEXITCODE
 } finally {$ErrorActionPreference='Stop'}
 Check 'wrong_password_rejected' $denied
 Check 'filenames_encrypted' ($listingExit -ne 0 -and ($headers -join ' ') -notmatch 'unchanged\.txt')
 Start-Sleep -Seconds 2
 [IO.File]::WriteAllText((Join-Path $source change.txt),'after-correction')
 # Preserve the fixture outside the input tree to test an archive deletion.
 Move-Item (Join-Path $source delete.txt) (Join-Path $run preserved-delete.txt)
 [IO.File]::WriteAllText((Join-Path $source added.txt),'new fixture')
 $diff=Join-Path $diffs latest.7z
 Invoke-SevenZip $sevenZip @('u',$base,'-u-',("-up3q3r2x2y2z0w2!"+$diff),'-t7z',("-p"+$secret),'-mhe=on',(Join-Path $source '*'))|Out-File (Join-Path $run diff.log)
 Check 'encrypted_diff_created' ($LASTEXITCODE -eq 0)
 Check 'encrypted_diff_integrity' (Test-SevenZipArchive $sevenZip $diff $secret)
 foreach ($archive in @($base,$diff)) {
  Invoke-SevenZip $sevenZip @('x',$archive,("-p"+$secret),("-o"+$out),'-y')|Out-File (Join-Path $run ('extract-'+(Split-Path $archive -Leaf)+'.log'))
  Check ('extract_'+(Split-Path $archive -Leaf)) ($LASTEXITCODE -eq 0)
 }
 Check 'restore_unchanged' ((Get-Content (Join-Path $out unchanged.txt) -Raw) -ceq 'unchanged')
 Check 'restore_corrected' ((Get-Content (Join-Path $out change.txt) -Raw) -ceq 'after-correction')
 Check 'restore_added' ((Get-Content (Join-Path $out added.txt) -Raw) -ceq 'new fixture')
 Check 'restore_deletion' (-not (Test-Path (Join-Path $out delete.txt)))
 $stamp='synthetic'
 Write-RestoreManifest $base $diff
 $m=Get-Content (Join-Path $chain restore-synthetic.json) -Raw|ConvertFrom-Json
 Check 'manifest_hashes' ($m.encrypted -and $m.archives.Count -eq 2 -and $m.archives[0].sha256 -eq (Get-FileHash $base).Hash -and $m.archives[1].sha256 -eq (Get-FileHash $diff).Hash)
 $mirror=Join-Path $run sync-folder-fixture
 New-Item -ItemType Directory -Path $mirror|Out-Null
 Copy-Item (Join-Path $chain '*') $mirror -Recurse
 [IO.File]::WriteAllText((Join-Path $mirror older-retained.txt),'old')
 Test-CloudFilesPresent $chain $mirror
 Check 'older_files_retained' (Test-Path (Join-Path $mirror older-retained.txt))
 # Exercise the actual Windows ProcessStartInfo/WSL binary boundary with
 # spaces in the destination and all byte values, including NUL and CR/LF.
 $binary=Join-Path $run 'binary with spaces.bin'
 Invoke-WslBinaryExport 'import sys; sys.stdout.buffer.write(bytes(range(256)))' $binary root
 $bytes=[IO.File]::ReadAllBytes($binary)
 $same=($bytes.Length -eq 256)
 for ($i=0;$i -lt $bytes.Length;$i++) {if ($bytes[$i] -ne $i) {$same=$false}}
 Check 'real_wsl_binary_all_byte_values' $same
 $failed=Join-Path $run failed-export.bin
 $refused=$false
 try {Invoke-WslBinaryExport "import sys; sys.stdout.buffer.write(b'partial'); sys.stdout.flush(); sys.exit(7)" $failed root}
 catch {$refused=$true}
 Check 'failed_wsl_export_not_promoted' ($refused -and -not (Test-Path -LiteralPath $failed))
 Check 'failed_wsl_partial_retained' (@(Get-ChildItem -LiteralPath $run -Filter 'failed-export.bin.partial-*').Count -eq 1)
 $collection=$null
 if ($CollectCognee) {
  $BackupRoot=Join-Path $run cognee-collection;$RequireCogneeBackup=$true;$CogneeMaxBackupAgeHours=48
  $script:Errors=[Collections.Generic.List[string]]::new();$script:CoverageWarnings=[Collections.Generic.List[string]]::new()
  Backup-EnhancedCognee
  Check 'actual_windows_wsl_collection' ($script:Errors.Count -eq 0)
  $dest=Join-Path $BackupRoot 'Hermes\enhanced-cognee-encrypted'
  $index=Get-Content (Join-Path $dest collection-index.json) -Raw|ConvertFrom-Json
  Check 'complete_archive_manifest_pairs' ($index.state -eq 'ready' -and @($index.files).Count -ge 2 -and @($index.files).Count % 2 -eq 0)
  $collection=@{completed_pairs=@($index.files).Count/2;copied_hashes_verified=$true;recovery_keys_collected=$false;destination=$dest}
 }
 $taskSummary=$null
 if ($TaskName) {
  $task=Get-ScheduledTask -TaskName $TaskName;$info=$task|Get-ScheduledTaskInfo
  $taskSummary=@{name=$task.TaskName;uses_v11=[bool]($task.Actions.Arguments -match 'backup-all-wsl-v11\.ps1');
   requires_cognee=[bool]($task.Actions.Arguments -match 'RequireCogneeBackup');nonoverlap=$task.Settings.MultipleInstances.ToString();
   logon=$task.Principal.LogonType.ToString();last_result=('0x{0:X8}' -f $info.LastTaskResult);modified_by_test=$false}
 }
 $summary=[ordered]@{complete=$true;windows_powershell=$PSVersionTable.PSVersion.ToString();seven_zip=$sevenZip.VersionInfo.FileVersion;
 backup_script_sha256=(Get-FileHash $BackupScript).Hash;passed=$checks.Count;failed=0;checks=$checks;collected_cognee=$collection;scheduled_task=$taskSummary;
 fixtures_retained=$true;full_backup_started=$false;cloud_upload_started=$false;owner_real_password_configured=(Test-Path "$env:APPDATA\RNR-Backups\archive-password.xml");
 real_off_machine_recovery_qualified=$false;scheduled_execution_qualified=$false}
 $summary|ConvertTo-Json -Depth 8|Set-Content (Join-Path $run summary.json) -Encoding UTF8
 [pscustomobject]@{complete=$true;passed=$checks.Count;failed=0;artifacts=$run;collected_pairs=$collection.completed_pairs}|ConvertTo-Json -Compress
} catch {
 @{complete=$false;passed=@($checks|Where-Object {$_.passed}).Count;failed=1;checks=$checks;error_type=$_.Exception.GetType().Name}|
 ConvertTo-Json -Depth 6|Set-Content (Join-Path $run summary.json) -Encoding UTF8
 Write-Error ('Qualification stopped; private evidence retained at '+$run)
 exit 1
} finally {$secret=$null}

