# Private stdout is consumed only by restic's password-command pipe.
[CmdletBinding()]
param([string]$PasswordFile="$env:APPDATA\RNR-Backups\archive-password.xml")
$ErrorActionPreference='Stop'
$env:PSModulePath=Join-Path $PSHOME 'Modules'
$secret=$null;$pointer=[IntPtr]::Zero
try {
 $secret=Import-Clixml -LiteralPath $PasswordFile
 if ($secret -isnot [Security.SecureString] -or $secret.Length -lt 20) {throw 'Invalid protected password'}
 $pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
 [Console]::Out.WriteLine([Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer))
} catch {
 [Console]::Error.WriteLine('Cannot unlock the Windows-protected backup password. Use its owning Windows account or reconfigure it from KeePassXC.')
 exit 1
} finally {
 if ($pointer -ne [IntPtr]::Zero) {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)}
 if ($secret -is [Security.SecureString]) {$secret.Dispose()}
}
