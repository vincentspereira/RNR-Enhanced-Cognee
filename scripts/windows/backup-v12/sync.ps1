# Copy a quiescent restic repository. Immutable data first, snapshots last.
# No /MIR, purge, repository unlock, forget, prune or cloud deletion.
function Copy-V12ImmutableFile {
 param([string]$Source,[string]$Target,[string]$Receipt)
 $origin=Get-Item -LiteralPath $Source -Force
 if ($origin.Attributes -band [IO.FileAttributes]::ReparsePoint) {throw 'A repository source is a link.'}
 $saved=$null
 if (Test-Path -LiteralPath $Receipt) {$saved=Get-Content -LiteralPath $Receipt -Raw|ConvertFrom-Json}
 # Immutable objects verified on a previous copy need no repeated content read.
 if ($saved -and $saved.source_ticks -eq $origin.LastWriteTimeUtc.Ticks -and $saved.bytes -eq $origin.Length) {
  $expected=$saved.sha256
 } else {$expected=(Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash.ToLowerInvariant()}
 if (Test-Path -LiteralPath $Target) {
  $item=Get-Item -LiteralPath $Target -Force
  if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
   # Cloud providers use reparse points. Only accept a prior verified receipt;
   # never follow an arbitrary link or hydrate an unverified object silently.
   $cloudPlaceholder=([int]$item.Attributes -band (0x1000 -bor 0x40000 -bor 0x400000)) -and -not $item.LinkType
   if (-not $cloudPlaceholder) {throw 'Unreviewed destination reparse point.'}
  }
  if ($saved) {
   if ($saved.sha256 -eq $expected -and $saved.bytes -eq $origin.Length -and
       $item.Length -eq $origin.Length -and $saved.target_ticks -eq $item.LastWriteTimeUtc.Ticks) {
    return @{copied=0;reused=1;resumed_bytes=0}
   }
  }
  if ($item.Length -ne $origin.Length -or
      (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
   throw 'Existing cloud object differs; preserved for investigation. Nothing overwritten.'
  }
  Save-V12Json @{sha256=$expected;bytes=$item.Length;source_ticks=$origin.LastWriteTimeUtc.Ticks;target_ticks=$item.LastWriteTimeUtc.Ticks} $Receipt
  return @{copied=0;reused=1;resumed_bytes=0}
 }
 [IO.Directory]::CreateDirectory((Split-Path $Target -Parent))|Out-Null
 $partial=$Target+'.partial-v12';$offset=[long]0
 if (Test-Path -LiteralPath $partial) {
  $piece=Get-Item -LiteralPath $partial -Force
  if ($piece.Attributes -band [IO.FileAttributes]::ReparsePoint -or $piece.Length -gt $origin.Length) {
   throw 'Invalid partial object retained; review it before retrying.'
  }
  # Resume only if the existing prefix exactly matches the source.
  $a=[IO.File]::OpenRead($Source);$b=[IO.File]::OpenRead($partial)
  $ha=[Security.Cryptography.SHA256]::Create();$hb=[Security.Cryptography.SHA256]::Create()
  try {
   $left=[byte[]]::new(1MB);$right=[byte[]]::new(1MB);$remaining=$piece.Length
   while ($remaining -gt 0) {
    $count=[int][Math]::Min(1MB,$remaining)
    $n=$b.Read($right,0,$count);$m=$a.Read($left,0,$n)
    if ($n -le 0 -or $m -ne $n) {throw 'Partial prefix is truncated.'}
    $null=$ha.TransformBlock($left,0,$m,$left,0)
    $null=$hb.TransformBlock($right,0,$n,$right,0)
    $remaining-=$n
   }
   $null=$ha.TransformFinalBlock([byte[]]::new(0),0,0)
   $null=$hb.TransformFinalBlock([byte[]]::new(0),0,0)
   if ([BitConverter]::ToString($ha.Hash) -cne [BitConverter]::ToString($hb.Hash)) {throw 'Partial prefix differs; retained without overwrite.'}
   $offset=$piece.Length
  } finally {$a.Dispose();$b.Dispose();$ha.Dispose();$hb.Dispose()}
 }
 $inputStream=[IO.File]::OpenRead($Source)
 $outputStream=[IO.File]::Open($partial,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try {
  $inputStream.Position=$offset;$outputStream.Position=$offset
  $inputStream.CopyTo($outputStream,4MB);$outputStream.Flush($true)
 } finally {$inputStream.Dispose();$outputStream.Dispose()}
 if ((Get-Item -LiteralPath $partial).Length -ne $origin.Length -or
     (Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
  throw 'Copied ciphertext failed verification; partial file retained.'
 }
 [IO.File]::Move($partial,$Target)
 $item=Get-Item -LiteralPath $Target
 Save-V12Json @{sha256=$expected;bytes=$item.Length;source_ticks=$origin.LastWriteTimeUtc.Ticks;target_ticks=$item.LastWriteTimeUtc.Ticks} $Receipt
 return @{copied=1;reused=0;resumed_bytes=$offset}
}
function Sync-V12Repository {
 param([string]$Repository,[string]$Destination,[string]$ReceiptRoot)
 if (-not (Test-Path -LiteralPath (Join-Path $Repository config))) {throw 'Local repository is absent.'}
 Assert-V12SeparatePaths -Sources @($Repository) -Destinations @($Destination)
 foreach ($root in @($Repository,$Destination)) {
  if (Test-Path -LiteralPath (Join-Path $root locks)) {
   if (@(Get-ChildItem -LiteralPath (Join-Path $root locks) -File -Force).Count) {throw 'Repository has an active or stale lock. No automatic unlock or cloud copy.'}
  }
 }
 if (Test-Path -LiteralPath (Join-Path $Destination config)) {
  if ((Get-FileHash -LiteralPath (Join-Path $Repository config)).Hash -ne
      (Get-FileHash -LiteralPath (Join-Path $Destination config)).Hash) {
   throw 'Cloud folder belongs to another repository; nothing merged.'
  }
 }
 [IO.Directory]::CreateDirectory($Destination)|Out-Null
 Protect-V12Directory $ReceiptRoot
 $totals=@{copied=0;reused=0;resumed_bytes=[long]0;cloud_server_verified=$false}
 foreach ($phase in @(@('config','keys','data','index'),@('snapshots'))) {
  foreach ($name in $phase) {
   $path=Join-Path $Repository $name
   if (-not (Test-Path -LiteralPath $path)) {continue}
   $files=if ((Get-Item -LiteralPath $path).PSIsContainer) {@(Get-ChildItem -LiteralPath $path -File -Recurse -Force)} else {@(Get-Item -LiteralPath $path)}
   foreach ($file in $files) {
    $relative=$file.FullName.Substring($Repository.TrimEnd('\').Length+1)
    $hash=[Security.Cryptography.SHA256]::Create()
    try {$receiptName=([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($relative)))).Replace('-','')+'.json'}
    finally {$hash.Dispose()}
    $result=Copy-V12ImmutableFile $file.FullName (Join-Path $Destination $relative) (Join-Path $ReceiptRoot $receiptName)
    foreach ($key in @('copied','reused','resumed_bytes')) {$totals[$key]+=$result[$key]}
   }
  }
 }
 return $totals
}
