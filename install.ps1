#
# Enhanced Cognee Installation Script for Windows
#
# This script installs Enhanced Cognee in one command.
# Supports both Full and Lite installation modes.
#
# Usage:
#   .\install.ps1              # Interactive mode
#   .\install.ps1 -Mode full   # Full mode (all databases)
#   .\install.ps1 -Mode lite   # Lite mode (SQLite only)
#   .\install.ps1 -Help        # Show help
#
# Author: Enhanced Cognee Team
# Version: 1.0.0
# Date: 2026-02-06

#Requires -Version 5.1

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("full", "lite")]
    [string]$Mode = "full",

    [Parameter(Mandatory=$false)]
    [switch]$Help
)

# Configuration
$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$PythonCmd = "python"

# Functions
function Print-Header {
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "  Enhanced Cognee Installation" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
}

function Print-Step {
    param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor Green
}

function Print-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Print-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Print-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Print-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Test-Prerequisites {
    Print-Step "Checking prerequisites..."

    # Check Python
    try {
        $pythonVersion = & $PythonCmd --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Print-Error "Python is not installed"
            Print-Info "Please install Python 3.10 or higher from: https://www.python.org/downloads/"
            exit 1
        }
        Print-Info "Python version: $pythonVersion"
    }
    catch {
        Print-Error "Python is not installed"
        Print-Info "Please install Python 3.10 or higher from: https://www.python.org/downloads/"
        exit 1
    }

    # Check Python version >= 3.10
    $versionString = & $PythonCmd -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
    $version = [version]$versionString
    $minVersion = [version]"3.10"

    if ($version -lt $minVersion) {
        Print-Error "Python 3.10 or higher is required (found $version)"
        exit 1
    }

    # Check pip
    try {
        & $PythonCmd -m pip --version | Out-Null
        Print-Info "pip is installed"
    }
    catch {
        Print-Error "pip is not installed"
        exit 1
    }

    Print-Success "Prerequisites check passed"
}

function Install-PythonDeps {
    Print-Step "Installing Python dependencies..."

    Set-Location $ProjectRoot

    # Install dependencies
    if (Test-Path "requirements.txt") {
        & $PythonCmd -m pip install -r requirements.txt
    }
    else {
        # Install core dependencies
        $packages = @(
            "asyncpg",
            "qdrant-client",
            "neo4j",
            "redis",
            "tiktoken",
            "anthropic",
            "openai",
            "python-dotenv",
            "pydantic",
            "fastapi",
            "uvicorn",
            "mcp"
        )

        foreach ($package in $packages) {
            Write-Host "Installing $package..." -ForegroundColor Gray
            & $PythonCmd -m pip install $package
        }
    }

    Print-Success "Python dependencies installed"
}

function Test-Docker {
    if ($Mode -ne "full") {
        Print-Info "Skipping Docker check (Lite mode)"
        return
    }

    Print-Step "Checking Docker installation..."

    # Check if Docker is installed
    try {
        $dockerVersion = docker --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Print-Warn "Docker is not installed"
            Print-Info "Please install Docker Desktop for Windows:"
            Print-Info "  https://www.docker.com/products/docker-desktop/"
            exit 1
        }
        Print-Info "$dockerVersion"
    }
    catch {
        Print-Warn "Docker is not installed"
        Print-Info "Please install Docker Desktop for Windows:"
        Print-Info "  https://www.docker.com/products/docker-desktop/"
        exit 1
    }

    # Check if Docker is running
    try {
        docker info | Out-Null
        Print-Info "Docker is running"
    }
    catch {
        Print-Error "Docker is not running"
        Print-Info "Please start Docker Desktop and try again"
        exit 1
    }

    Print-Success "Docker installation verified"
}

function Invoke-SetupWizard {
    Print-Step "Running setup wizard..."

    Set-Location $ProjectRoot

    & $PythonCmd setup_wizard.py

    if ($LASTEXITCODE -ne 0) {
        Print-Error "Setup wizard failed"
        exit 1
    }

    Print-Success "Setup wizard completed"
}

function Start-Services {
    Print-Step "Starting Enhanced Cognee services..."

    Set-Location $ProjectRoot

    if ($Mode -eq "full") {
        # Start Docker services
        Print-Info "Starting databases with Docker..."
        docker compose -f docker/docker-compose-enhanced-cognee.yml up -d

        if ($LASTEXITCODE -ne 0) {
            Print-Error "Failed to start Docker services"
            exit 1
        }
    }

    Print-Success "Services started"
}

function Invoke-Preflight {
    Print-Step "Running pre-flight checks..."

    Set-Location $ProjectRoot

    & $PythonCmd preflight.py

    if ($LASTEXITCODE -ne 0) {
        Print-Warn "Some pre-flight checks failed"
        Print-Info "You may need to fix these issues before using Enhanced Cognee"
    }
    else {
        Print-Success "All pre-flight checks passed"
    }
}

function Add-ToPath {
    Print-Step "Creating CLI command..."

    $cliScript = Join-Path $ProjectRoot "enhanced-cognee"

    if (-not (Test-Path $cliScript)) {
        Print-Error "CLI script not found: $cliScript"
        return
    }

    Print-Success "CLI script created: $cliScript"
    Print-Info "You can run Enhanced Cognee with: python $cliScript"
    Print-Info "Or add the project directory to your PATH for easy access"
}

function Print-Completion {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  Installation Complete!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Enhanced Cognee is ready to use!"
    Write-Host ""
    Write-Host "Quick Start:"
    Write-Host "  1. Check status:"
    Write-Host "     $ python preflight.py"
    Write-Host ""
    Write-Host "  2. Start services:"
    Write-Host "     $ python enhanced-cognee start"
    Write-Host ""
    Write-Host "  3. View logs:"
    Write-Host "     $ python enhanced-cognee logs"
    Write-Host ""
    Write-Host "For more information, see README.md"
    Write-Host ""
}

function Show-Help {
    Write-Host "Enhanced Cognee Installation Script for Windows"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\install.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Mode <mode>  Installation mode (full or lite) [default: full]"
    Write-Host "  -Help         Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\install.ps1          # Interactive mode (default: full)"
    Write-Host "  .\install.ps1 -Mode full   # Full mode with all databases"
    Write-Host "  .\install.ps1 -Mode lite   # Lite mode with SQLite only"
    Write-Host ""
}

# Main installation flow
function Main {
    Print-Header

    Print-Info "Installation mode: $Mode"
    Write-Host ""

    # Show help if requested
    if ($Help) {
        Show-Help
        exit 0
    }

    # Run installation steps
    Test-Prerequisites
    Install-PythonDeps

    if ($Mode -eq "full") {
        Test-Docker
    }

    Invoke-SetupWizard
    Start-Services
    Invoke-Preflight
    Add-ToPath

    Print-Completion
}

# Run main
Main
