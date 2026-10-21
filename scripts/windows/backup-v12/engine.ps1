# Shared native Windows process and durable-state helpers. No secret arguments.
function ConvertTo-V12Argument {
 param([AllowEmptyString()][string]$Value)
 # CommandLineToArgvW quoting, including quotes and trailing backslashes.
 return '"'+([regex]::Replace([regex]::Replace($Value,'(\\*)"','$1$1\"'),'(\\+)$','$1$1'))+'"'
}
function Invoke-V12Process {
 param([string]$Program,[string[]]$Arguments,[string]$LogPrefix)
 $p=[Diagnostics.Process]::new();$p.StartInfo.FileName=$Program
 $p.StartInfo.Arguments=($Arguments|ForEach-Object {ConvertTo-V12Argument $_}) -join ' '
 $p.StartInfo.UseShellExecute=$false;$p.StartInfo.CreateNoWindow=$true
 $p.StartInfo.RedirectStandardOutput=$true;$p.StartInfo.RedirectStandardError=$true
 $started=$false
 # Explicit configuration always wins over inherited restic credentials/routes.
 foreach ($key in @($p.StartInfo.EnvironmentVariables.Keys)) {
  if ([string]$key -like 'RESTIC_*') {$p.StartInfo.EnvironmentVariables.Remove([string]$key)}
 }
 try {
  if (-not $p.Start()) {throw 'Child process could not start.'}
  $started=$true
  $outTask=$p.StandardOutput.ReadToEndAsync();$errTask=$p.StandardError.ReadToEndAsync()
  $p.WaitForExit()
  $stdout=$outTask.GetAwaiter().GetResult();$stderr=$errTask.GetAwaiter().GetResult()
  if ($LogPrefix) {
   [IO.File]::WriteAllText($LogPrefix+'.stdout',$stdout,[Text.UTF8Encoding]::new($false))
   [IO.File]::WriteAllText($LogPrefix+'.stderr',$stderr,[Text.UTF8Encoding]::new($false))
  }
  return @{exit=$p.ExitCode;stdout=$stdout;stderr=$stderr}
 } finally {
  if ($started -and -not $p.HasExited) {$p.Kill();$p.WaitForExit()}
  $p.Dispose()
 }
}
function Save-V12Json {
 param([object]$Value,[string]$Path)
 $temporary=$Path+'.new-'+[guid]::NewGuid().ToString('N')
 [IO.File]::WriteAllText($temporary,($Value|ConvertTo-Json -Depth 16),[Text.UTF8Encoding]::new($false))
 if (Test-Path -LiteralPath $Path) {[IO.File]::Replace($temporary,$Path,[System.Management.Automation.Language.NullString]::Value)}
 else {[IO.File]::Move($temporary,$Path)}
}
function Protect-V12Directory {
 param([string]$Path)
 [IO.Directory]::CreateDirectory($Path)|Out-Null
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent().User
 $acl=[Security.AccessControl.DirectorySecurity]::new();$acl.SetOwner($identity)
 $acl.SetAccessRuleProtection($true,$false)
 foreach ($sid in @($identity,[Security.Principal.SecurityIdentifier]::new('S-1-5-18'))) {
  $rule=[Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
  $acl.AddAccessRule($rule)
 }
 Set-Acl -LiteralPath $Path -AclObject $acl
}
function Get-V12PythonCommand {
 param([string]$Helper,[string[]]$Options=@())
 $encoded=[Convert]::ToBase64String([IO.File]::ReadAllBytes($Helper))
 return @('/usr/bin/python3','-I','-c',"exec(__import__('base64').b64decode('$encoded'))")+$Options
}
