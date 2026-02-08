################################################################################
# Enhanced Cognee Lite Mode - Installation Script (Windows)
#
# Lightweight setup with SQLite, no Docker required.
# Setup time: <2 minutes
#
# Author: Enhanced Cognee Team
# Version: 1.0.0
# Date: 2026-02-06
################################################################################

$ErrorActionPreference = "Stop"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LiteDir = Join-Path $ScriptDir "src\lite_mode"
$ConfigFile = Join-Path $LiteDir "lite_config.json"
$DbFile = Join-Path $ScriptDir "cognee_lite.db"

Write-Host "Enhanced Cognee Lite Mode Installation" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""

# Check Python version
Write-Host "[INFO] Checking Python version..." -ForegroundColor Green
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[INFO] Found $pythonVersion"
} catch {
    Write-Host "[ERR] Python is not installed" -ForegroundColor Red
    Write-Host "[INFO] Please install Python 3.8 or higher from: https://www.python.org/downloads/"
    exit 1
}

# Extract Python version numbers
$versionParts = $pythonVersion.Split(" ")[1].Split(".")
$major = [int]$versionParts[0]
$minor = [int]$versionParts[1]

if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
    Write-Host "[ERR] Python 3.8 or higher is required (found $pythonVersion)" -ForegroundColor Red
    exit 1
}

# Check if pip is available
Write-Host "[INFO] Checking pip..." -ForegroundColor Green
try {
    pip --version | Out-Null
} catch {
    Write-Host "[ERR] pip is not installed" -ForegroundColor Red
    Write-Host "[INFO] Install pip: python -m ensurepip --upgrade"
    exit 1
}

# Install dependencies
Write-Host "[INFO] Installing dependencies..." -ForegroundColor Green
python -m pip install --upgrade pip | Out-Null

# Check SQLite support (usually built-in)
Write-Host "[INFO] Checking SQLite support..." -ForegroundColor Green
try {
    $sqliteVersion = python -c "import sqlite3; print(sqlite3.sqlite_version)"
    Write-Host "[INFO] SQLite version: $sqliteVersion"
} catch {
    Write-Host "[ERR] SQLite support not found" -ForegroundColor Red
    exit 1
}

# Optional: Install APScheduler for maintenance tasks
Write-Host "[INFO] Installing APScheduler for maintenance scheduling..." -ForegroundColor Green
try {
    pip install apscheduler | Out-Null
    Write-Host "[OK] APScheduler installed" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Failed to install APScheduler (optional)" -ForegroundColor Yellow
}

# Create directories
Write-Host "[INFO] Creating directories..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path "$LiteDir" | Out-Null
New-Item -ItemType Directory -Force -Path "$ScriptDir\migrations" | Out-Null
New-Item -ItemType Directory -Force -Path "$ScriptDir\backups" | Out-Null
New-Item -ItemType Directory -Force -Path "$ScriptDir\logs" | Out-Null

# Check if schema file exists
$SchemaFile = Join-Path $ScriptDir "migrations\create_lite_schema.sql"
if (-not (Test-Path $SchemaFile)) {
    Write-Host "[ERR] Schema file not found: migrations\create_lite_schema.sql" -ForegroundColor Red
    exit 1
}

# Initialize database
Write-Host "[INFO] Initializing SQLite database..." -ForegroundColor Green
if (Test-Path $DbFile) {
    Write-Host "[WARN] Database already exists: $DbFile" -ForegroundColor Yellow
    $response = Read-Host "Do you want to recreate it? (y/N)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Remove-Item $DbFile -Force
        Write-Host "[INFO] Creating new database..."
    } else {
        Write-Host "[INFO] Using existing database"
    }
}

# Create database and initialize schema
$initScript = @"
import sqlite3
import os

db_path = r'$DbFile'
schema_path = r'$SchemaFile'

if not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    # Split and execute each statement
    for statement in schema_sql.split(';'):
        statement = statement.strip()
        if statement:
            try:
                conn.execute(statement)
            except sqlite3.OperationalError as e:
                if 'already exists' not in str(e):
                    print(f'[WARN] {e}')

    conn.commit()
    conn.close()
    print('[OK] Database created: ' + db_path)
else:
    print('[INFO] Database already exists: ' + db_path)
"@

python -c $initScript

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERR] Database initialization failed" -ForegroundColor Red
    exit 1
}

# Test Lite MCP Server
Write-Host "[INFO] Testing Lite MCP Server..." -ForegroundColor Green
$testScript = @"
import sys
sys.path.insert(0, r'$ScriptDir')

from src.lite_mode.sqlite_manager import SQLiteManager

db = SQLiteManager(r'$DbFile')
health = db.health_check()

if health['status'] == 'OK':
    print('[OK] Lite mode database ready')
    print(f'     Database: {health["database"]}')
    print(f'     Path: {health["path"]}')
    print(f'     Mode: {health["mode"]}')
else:
    print('[ERR] Database health check failed')
    sys.exit(1)

# Test adding a memory
doc_id = db.add_document(
    data_id='test_memory',
    data_text='Enhanced Cognee Lite Mode installation test',
    data_type='test',
    metadata={'test': True},
    user_id='installer',
    agent_id='install_script'
)

print(f'[OK] Test memory added: {doc_id}')

# Test search
results = db.search_documents('installation', user_id='installer', limit=1)
if results:
    print(f'[OK] Full-text search working: found {len(results)} result(s)')
else:
    print('[WARN] Full-text search returned no results')

db.close()
"@

python -c $testScript

if ($LASTEXITCODE -eq 0) {
    Write-Host "[INFO] Lite mode installation successful!" -ForegroundColor Green
} else {
    Write-Host "[ERR] Lite mode installation failed" -ForegroundColor Red
    exit 1
}

# Create startup script
Write-Host "[INFO] Creating startup script..." -ForegroundColor Green
$startupScript = @"
# Enhanced Cognee Lite Mode - Startup Script

`$ScriptDir = Split-Path -Parent `$MyInvocation.MyCommand.Path
Set-Location `$ScriptDir

Write-Host "Starting Enhanced Cognee Lite Mode..."
Write-Host "Database: `$ScriptDir\cognee_lite.db"
Write-Host ""

# Start Lite MCP Server
python src\lite_mode\lite_mcp_server.py
"@

$startupScriptPath = Join-Path $ScriptDir "start_lite.ps1"
$startupScript | Out-File -FilePath $startupScriptPath -Encoding UTF8

# Print summary
Write-Host ""
Write-Host "[INFO] Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:"
Write-Host "--------"
Write-Host "  Database: $DbFile"
Write-Host "  Config: $ConfigFile"
Write-Host "  Logs: $ScriptDir\logs\"
Write-Host "  Backups: $ScriptDir\backups\"
Write-Host ""
Write-Host "Next Steps:"
Write-Host "----------"
Write-Host "1. Test Lite mode:"
Write-Host "   python src\lite_mode\lite_mcp_server.py"
Write-Host ""
Write-Host "2. Start Lite mode:"
Write-Host "   .\start_lite.ps1"
Write-Host ""
Write-Host "3. Configure Claude Code:"
Write-Host "   Add to %USERPROFILE%\.claude.json:"
Write-Host '   {"mcpServers": {"cognee-lite": {"command": "python", "args": ["' $ScriptDir '\src\lite_mode\lite_mcp_server.py"]}}}'
Write-Host ""
Write-Host "For more information, see docs\LITE_MODE_GUIDE.md"
Write-Host ""
Write-Host "[INFO] Setup time: <2 minutes (no Docker required!)" -ForegroundColor Green
Write-Host ""
