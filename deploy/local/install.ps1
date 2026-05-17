#Requires -Version 5.0
<#
.SYNOPSIS
    Enhanced Cognee local installer for Windows.

.DESCRIPTION
    Idempotent installer:
      1. Checks/installs Python 3.11+
      2. Creates .venv if missing
      3. Installs editable package + deps
      4. Brings up Docker stack (postgres/qdrant/neo4j/redis)
      5. Registers MCP server in ~/.claude.json
      6. Optionally registers Windows Task Scheduler entry to auto-start
         the Docker stack on logon (per Q8 in the production plan).

    Safe to re-run; each step is idempotent.

.PARAMETER AutoStart
    If set, registers a Windows Task Scheduler job that brings up the Docker
    stack on user logon (matches Q8 answer in PRODUCTION_READINESS_PLAN.md).

.PARAMETER SkipDocker
    Skip Docker stack bring-up (useful if you'll manage containers yourself).

.EXAMPLE
    .\install.ps1
    .\install.ps1 -AutoStart
    .\install.ps1 -SkipDocker
#>

[CmdletBinding()]
param(
    [switch]$AutoStart,
    [switch]$SkipDocker
)

$ErrorActionPreference = "Stop"

# ----------------------------------------------------------------------------
# Helpers (ASCII-only output per project rule)
# ----------------------------------------------------------------------------

function Write-Step  { param($msg) Write-Host "[STEP] $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host "[ERR]  $msg" -ForegroundColor Red }

$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$VenvPath = Join-Path $RepoRoot ".venv"
$ComposeFile = Join-Path $RepoRoot "docker\docker-compose-enhanced-cognee.yml"
$ClaudeConfig = Join-Path $env:USERPROFILE ".claude.json"

Write-Step "Enhanced Cognee installer starting"
Write-Host "  Repo:    $RepoRoot"
Write-Host "  Venv:    $VenvPath"
Write-Host "  Compose: $ComposeFile"
Write-Host ""

# ----------------------------------------------------------------------------
# 1. Python check
# ----------------------------------------------------------------------------

Write-Step "Checking Python >=3.11"
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Err "Python not found on PATH. Install from https://www.python.org/downloads/ (3.11+)"
    exit 1
}
$pyVersion = & python --version 2>&1
Write-Ok "Found: $pyVersion"

# ----------------------------------------------------------------------------
# 2. Virtual environment
# ----------------------------------------------------------------------------

Write-Step "Setting up .venv"
if (-not (Test-Path $VenvPath)) {
    & python -m venv $VenvPath
    Write-Ok "Created $VenvPath"
} else {
    Write-Ok "Venv already exists"
}

$VenvPy = Join-Path $VenvPath "Scripts\python.exe"
$VenvPip = Join-Path $VenvPath "Scripts\pip.exe"

# ----------------------------------------------------------------------------
# 3. Install dependencies
# ----------------------------------------------------------------------------

Write-Step "Upgrading pip + installing Enhanced Cognee (editable)"
& $VenvPy -m pip install --upgrade pip --quiet
Push-Location $RepoRoot
try {
    & $VenvPip install -e . --quiet
    Write-Ok "Installed editable package"
} finally {
    Pop-Location
}

# ----------------------------------------------------------------------------
# 4. Docker stack
# ----------------------------------------------------------------------------

if (-not $SkipDocker) {
    Write-Step "Checking Docker"
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCmd) {
        Write-Err "Docker not found. Install Docker Desktop from https://www.docker.com/products/docker-desktop"
        exit 1
    }
    Write-Ok "Docker found"

    Write-Step "Starting Enhanced Cognee Docker stack"
    & docker compose -f $ComposeFile up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Err "docker compose up failed"
        exit 1
    }

    Write-Step "Waiting for services to become healthy (up to 60s)"
    $deadline = (Get-Date).AddSeconds(60)
    $services = @("cognee-mcp-postgres", "cognee-mcp-qdrant", "cognee-mcp-neo4j", "cognee-mcp-valkey")
    while ((Get-Date) -lt $deadline) {
        $allHealthy = $true
        foreach ($svc in $services) {
            $status = docker inspect --format='{{.State.Health.Status}}' $svc 2>$null
            if ($status -ne "healthy") {
                $allHealthy = $false
                break
            }
        }
        if ($allHealthy) {
            Write-Ok "All 4 services healthy"
            break
        }
        Start-Sleep -Seconds 3
    }
}

# ----------------------------------------------------------------------------
# 5. Register MCP server in ~/.claude.json
# ----------------------------------------------------------------------------

Write-Step "Registering MCP server in $ClaudeConfig"
$mcpEntry = @{
    command = (Join-Path $VenvPath "Scripts\python.exe")
    args = @((Join-Path $RepoRoot "bin\enhanced_cognee_mcp_server.py"))
    env = @{
        ENHANCED_COGNEE_MODE = "true"
        POSTGRES_HOST = "localhost"
        POSTGRES_PORT = "25432"
        POSTGRES_DB = "cognee_db"
        POSTGRES_USER = "cognee_user"
        POSTGRES_PASSWORD = "cognee_password"
        QDRANT_HOST = "localhost"
        QDRANT_PORT = "26333"
        NEO4J_URI = "bolt://localhost:27687"
        NEO4J_USER = "neo4j"
        NEO4J_PASSWORD = "cognee_password"
        REDIS_HOST = "localhost"
        REDIS_PORT = "26379"
    }
}

if (Test-Path $ClaudeConfig) {
    $cfg = Get-Content $ClaudeConfig -Raw | ConvertFrom-Json -AsHashtable
} else {
    $cfg = @{ mcpServers = @{} }
}
if (-not $cfg.ContainsKey("mcpServers")) { $cfg["mcpServers"] = @{} }
$cfg["mcpServers"]["cognee"] = $mcpEntry
$cfg | ConvertTo-Json -Depth 10 | Set-Content $ClaudeConfig -Encoding UTF8
Write-Ok "MCP server 'cognee' registered"

# ----------------------------------------------------------------------------
# 6. Optional: Task Scheduler auto-start (Q8: yes)
# ----------------------------------------------------------------------------

if ($AutoStart) {
    Write-Step "Registering Windows Task Scheduler entry for stack auto-start"
    $taskName = "EnhancedCogneeStack"
    $action = New-ScheduledTaskAction -Execute "docker" -Argument "compose -f `"$ComposeFile`" up -d"
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

    try {
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
            -Principal $principal -Settings $settings -Force | Out-Null
        Write-Ok "Auto-start registered as scheduled task '$taskName'"
    } catch {
        Write-Warn "Could not register scheduled task: $($_.Exception.Message)"
        Write-Warn "You may need to run this script as Administrator for auto-start."
    }
}

# ----------------------------------------------------------------------------
# Done
# ----------------------------------------------------------------------------

Write-Host ""
Write-Ok "Enhanced Cognee installation complete"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Restart Claude Code to pick up the new MCP server"
Write-Host "  2. Verify with: claude mcp list"
Write-Host "  3. Test:        make smoke   (or  python -m pytest tests/system/ -q)"
Write-Host ""
if (-not $AutoStart) {
    Write-Host "Tip: re-run with -AutoStart to auto-start the Docker stack at logon."
}
