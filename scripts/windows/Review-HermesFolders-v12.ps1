[CmdletBinding(SupportsShouldProcess=$true)]
param([switch]$Apply)
$ErrorActionPreference='Stop'
. "$PSScriptRoot\backup-v12\engine.ps1"
if ($WhatIfPreference) {Write-Host 'Preview only; no Hermes process or file change.';return}
$options=if ($Apply) {@('--apply')} else {@()}
if ($Apply -and -not $PSCmdlet.ShouldProcess('Ubuntu-Hermes owner home','apply the six requested moves, verify files, preserve compatibility links and stop on active sources/collisions')) {return}
$python=Get-V12PythonCommand "$PSScriptRoot\backup-v12\reorganize_hermes_home.py" $options
$result=Invoke-V12Process "$env:SystemRoot\System32\wsl.exe" (@('-d','Ubuntu-Hermes','-u','vincentspereira','--cd','/','--exec')+$python) $null
if ($result.exit -ne 0) {throw 'Hermes folder operation failed. Existing files preserved; inspect the private local journal before retry.'}
$result.stdout
$review=$result.stdout|ConvertFrom-Json
if ($Apply -and $review.review_required_count -gt 0) {
 Write-Warning 'Some requested folders were preserved for individual review (collision, active use, existing link or linked worktree). The JSON result identifies each one; those moves are not complete.'
 exit 2
}
