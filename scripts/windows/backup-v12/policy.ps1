# Native Windows paths only. Outputs/repositories are never source roots.
function Write-V12WindowsInventory {
 param([string]$MetadataRoot)
 $programs=[Collections.Generic.List[object]]::new()
 foreach ($registryRoot in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
   'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
   'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall')) {
  if (-not (Test-Path -LiteralPath $registryRoot)) {continue}
  foreach ($key in Get-ChildItem -LiteralPath $registryRoot) {
   $value=Get-ItemProperty -LiteralPath $key.PSPath
   $name=$value.PSObject.Properties['DisplayName']
   if (-not $name -or -not $name.Value) {continue}
   $version=$value.PSObject.Properties['DisplayVersion'];$publisher=$value.PSObject.Properties['Publisher']
   $programs.Add(@{name=$name.Value;version=if ($version) {$version.Value} else {''};publisher=if ($publisher) {$publisher.Value} else {''}})
  }
 }
 $os=Get-CimInstance Win32_OperatingSystem
 $inventory=@{registered_programs=@($programs.ToArray());os_version=$os.Version;build=$os.BuildNumber;architecture=$os.OSArchitecture;
  is_windows_system_image=$false;does_not_cover_every_store_or_portable_app=$true}
 Save-V12Json $inventory (Join-Path $MetadataRoot windows-software-recovery.json)
}

function Get-V12SourcePolicy {
 param([string]$MetadataRoot)
 $sources=[Collections.Generic.List[string]]::new()
 $missing=[Collections.Generic.List[string]]::new()
 foreach ($path in @($env:USERPROFILE,'C:\Users\rnr-worker','C:\Scripts',
   'D:\Vincent','D:\RNR-Releases','D:\RNR-Backups','D:\RNR-Recovery-Drills',
   'D:\RNR-Worker-Sandbox','D:\WSL\docs','D:\WSL\backup-logs')) {
  if (Test-Path -LiteralPath $path) {$sources.Add($path)} else {$missing.Add($path)}
 }
 $models='D:\AI-Models'
 $modelInventory=[Collections.Generic.List[object]]::new()
 if (Test-Path -LiteralPath $models) {
  foreach ($item in Get-ChildItem -LiteralPath $models -Force -ErrorAction Stop) {
   if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {continue}
   if (-not $item.PSIsContainer) {$sources.Add($item.FullName);continue}
   if ($item.Name -eq 'RNR-Worker-Envs') {
    foreach ($child in Get-ChildItem -LiteralPath $item.FullName -Force) {
     if ($child.Attributes -band [IO.FileAttributes]::ReparsePoint) {continue}
     if ($child.PSIsContainer -and $child.Name -match 'fixture|evidence|report') {$sources.Add($child.FullName)}
     elseif (-not $child.PSIsContainer -and $child.Extension -in @('.json','.md','.txt','.yaml','.yml','.toml','.lock')) {$sources.Add($child.FullName)}
    }
   } elseif ($item.Name -eq 'HuggingFace') {
    # Never traverse cache symlinks or read weight blobs merely to inventory.
    $pending=[Collections.Generic.Stack[string]]::new();$pending.Push($item.FullName)
    while ($pending.Count) {
     foreach ($entry in Get-ChildItem -LiteralPath $pending.Pop() -Force -ErrorAction Stop) {
      if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) {
       $relative=$entry.FullName.Substring($models.Length+1)
       $modelInventory.Add(@{path=$relative;is_link=$true;link_target=@($entry.Target);content_hash_verified=$false})
       # HF snapshot metadata often points into content-addressed blobs.
       # Preserve only small reviewed metadata targets within this model root.
       if (-not $entry.PSIsContainer -and ($entry.Extension -in @('.json','.yaml','.yml','.toml','.txt','.md','.jinja','.jinja2','.model','.vocab','.merges') -or $entry.Name -match '^(LICENSE|NOTICE|COPYING|config|tokenizer)')) {
        $resolved=$entry
        for ($hop=0;$hop -lt 8 -and ($resolved.Attributes -band [IO.FileAttributes]::ReparsePoint);$hop++) {
         if (-not @($resolved.Target).Count) {throw 'Model metadata link has no readable target.'}
         $linkTarget=[string]@($resolved.Target)[0]
         if (-not [IO.Path]::IsPathRooted($linkTarget)) {$linkTarget=Join-Path $resolved.DirectoryName $linkTarget}
         $linkTarget=[IO.Path]::GetFullPath($linkTarget)
         if (-not $linkTarget.StartsWith($item.FullName+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Model metadata link escapes the reviewed model directory.'}
         $resolved=Get-Item -LiteralPath $linkTarget -Force -ErrorAction Stop
        }
        if ($resolved.Attributes -band [IO.FileAttributes]::ReparsePoint -or $resolved.PSIsContainer -or $resolved.Length -gt 64MB) {throw 'Model metadata target is not a small regular file.'}
        $metadataCopy=Join-Path (Join-Path $MetadataRoot model-metadata) $relative
        [IO.Directory]::CreateDirectory((Split-Path $metadataCopy -Parent))|Out-Null
        Copy-Item -LiteralPath $resolved.FullName -Destination $metadataCopy -Force
       }
       continue
      }
      if ($entry.PSIsContainer) {$pending.Push($entry.FullName);continue}
      $relative=$entry.FullName.Substring($models.Length+1)
      $modelInventory.Add(@{path=$relative;bytes=$entry.Length;modified_utc=$entry.LastWriteTimeUtc.ToString('o');content_hash_verified=$false})
      if ($entry.Extension -in @('.json','.yaml','.yml','.toml','.txt','.md','.jinja','.jinja2','.model','.vocab','.merges') -or
          $entry.Name -match '^(LICENSE|NOTICE|COPYING|\.gitattributes|\.rnr-|config|tokenizer)' -or
          $relative -match '\\refs\\') {
       if ($entry.Length -le 64MB) {$sources.Add($entry.FullName)}
      }
     }
    }
   } else {
    # All original assets, output media, release archives, source patches,
    # review packs and evidence are included; no global *.7z/*.log/build ban.
    $sources.Add($item.FullName)
   }
  }
 }
 [IO.Directory]::CreateDirectory($MetadataRoot)|Out-Null
 ConvertTo-Json -InputObject @($modelInventory.ToArray()) -Depth 5|Set-Content -LiteralPath (Join-Path $MetadataRoot model-recovery-inventory.json) -Encoding UTF8
 # MetadataRoot is inside the already selected Windows owner profile.
 $excludes=@(
  '**/node_modules','**/__pycache__','**/.cache','**/.venv','**/.pytest_cache','**/.mypy_cache','**/.ruff_cache',
  '**/AppData/Local/Temp','**/AppData/Local/restic','**/AppData/Local/Programs',
  '**/RNR-Backups/v12-state/restic-cache','**/RNR-Backups/v12-state/qualification',
  '**/AppData/Local/Microsoft/Windows/INetCache','**/AppData/Local/Google/DriveFS',
  '**/AppData/Local/Packages/*/LocalCache','**/AppData/Local/Packages/*/TempState',
  '**/AppData/Local/Packages/*/LocalState/*.vhdx','**/AppData/Local/Docker/wsl',
  '**/AppData/Local/**/ext4.vhdx',
  '**/Cache/Cache_Data','**/Code Cache','**/GPUCache','**/CrashDumps',
  '**/.ollama/models/blobs','**/Downloads/*.exe','**/Downloads/*.msi','**/Downloads/*.iso',
  '**/Vincent/Personal-Workspace/Entertainment',
  '**/AI-Models/**/*.gguf','**/AI-Models/**/*.safetensors','**/AI-Models/**/*.ckpt',
  '**/AI-Models/**/*.pth','**/AI-Models/**/*.pt','**/AI-Models/**/*.onnx',
  '**/AI-Models/whisper/ggml-*.bin',
  '**/AI-Models/RNR-AI-Image-Video-Studio/checkpoints/**/*.bin',
  '**/AI-Models/RNR-AI-Image-Video-Studio/text_encoders/**/*.bin',
  '**/AI-Models/RNR-AI-Audio-Studio/narration/**/*.bin'
 )
 # Entire backup destinations are excluded even if an owner adds a broad root.
 foreach ($destination in @('D:\Archive',"$env:USERPROFILE\OneDrive")) {
  $normal=$destination.Replace('\','/');$restic='/'+$normal.Substring(0,1)+$normal.Substring(2)
  $excludes+=@($normal,$restic)
 }
 return @{sources=@($sources.ToArray());excludes=$excludes;missing=@($missing.ToArray());
  excluded_subtrees=@('D:\Archive',"$env:USERPROFILE\OneDrive");
  custom_models_declared=$false;downloaded_weights_included=$false;
  recreation_metadata_included=$true;one_drive_originals_separate=$true;
  profile_is_not_a_windows_system_image=$true;distro_images_separate=$true}
}

function Assert-V12SeparatePaths {
 param([string[]]$Sources,[string[]]$Destinations,[string[]]$ExcludedSubtrees=@())
 $normal=@($Sources|ForEach-Object {[IO.Path]::GetFullPath($_).TrimEnd('\')})
 for ($i=0;$i -lt $normal.Count;$i++) {
  for ($j=$i+1;$j -lt $normal.Count;$j++) {
   if ($normal[$i].Equals($normal[$j],[StringComparison]::OrdinalIgnoreCase) -or
       ($normal[$i]+'\').StartsWith($normal[$j]+'\',[StringComparison]::OrdinalIgnoreCase) -or
       ($normal[$j]+'\').StartsWith($normal[$i]+'\',[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Overlapping source roots would duplicate coverage; review the source policy.'
   }
  }
 }
 foreach ($source in $normal) {foreach ($target in $Destinations) {
  $destination=[IO.Path]::GetFullPath($target).TrimEnd('\')
  $explicitlyExcluded=$false
  foreach ($excluded in $ExcludedSubtrees) {
   $cut=[IO.Path]::GetFullPath($excluded).TrimEnd('\')
   if ($destination.Equals($cut,[StringComparison]::OrdinalIgnoreCase) -or
       ($destination+'\').StartsWith($cut+'\',[StringComparison]::OrdinalIgnoreCase)) {$explicitlyExcluded=$true}
  }
  $sourceInsideTarget=$source.Equals($destination,[StringComparison]::OrdinalIgnoreCase) -or
      ($source+'\').StartsWith($destination+'\',[StringComparison]::OrdinalIgnoreCase)
  $targetInsideSource=($destination+'\').StartsWith($source+'\',[StringComparison]::OrdinalIgnoreCase)
  if ($sourceInsideTarget -or ($targetInsideSource -and -not $explicitlyExcluded)) {
   throw 'A backup source and destination overlap; no backup was started.'
  }
 }}
}
