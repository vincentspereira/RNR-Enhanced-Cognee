#
# Enhanced Cognee Uninstallation Script for Windows
#
# This script stops all services and optionally removes Docker volumes.
#
# Usage:
#   .\uninstall.ps1              # Stop services only
#   .\uninstall.ps1 -Cleanup     # Stop and remove all data
#   .\uninstall.ps1 -Help        # Show help
#
# Author: Enhanced Cognee Team
# Version: 1.0.0
# Date: 2026-02-06

#Requires -Version 5.1

param(
    [Parameter(Mandatory=$false)]
    [switch]$Cleanup,

    [Parameter(Mandatory=$false)]
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$DockerComposeFile = Join-Path $ProjectRoot "docker\docker-compose-enhanced-cognee.yml"

function Print-Header {
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "  Enhanced Cognee Uninstallation" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
}

function Print-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Print-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Print-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Print-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Confirm-Action {
    $response = Read-Host "This action cannot be undone. Continue (y/N)"
    return $response -eq 'y' -or $response -eq 'Y'
}

function Stop-Services {
    Print-Info "Stopping Enhanced Cognee services..."

    if (-not (Test-Path $DockerComposeFile)) {
        Print-Warn "Docker compose file not found: $DockerComposeFile"
        return
    }

    Set-Location $ProjectRoot
    docker compose -f $DockerComposeFile down

    if ($LASTEXITCODE -ne 0) {
        Print-Error "Failed to stop services"
        return
    }

    Print-Success "Services stopped"
}

function Remove-Volumes {
    if (-not $Cleanup) {
        return
    }

    Print-Warn "This will permanently delete all Enhanced Cognee data!"

    if (-not (Confirm-Action)) {
        Print-Info "Volume cleanup cancelled"
        return
    }

    Print-Info "Removing Docker volumes..."

    if (-not (Test-Path $DockerComposeFile)) {
        Print-Error "Docker compose file not found: $DockerComposeFile"
        return
    }

    Set-Location $ProjectRoot
    docker compose -f $DockerComposeFile down -v

    if ($LASTEXITCODE -ne 0) {
        Print-Error "Failed to remove volumes"
        return
    }

    Print-Success "Volumes removed"
}

function Print-Completion {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  Uninstallation Complete" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Enhanced Cognee services have been stopped."
    Write-Host ""

    if ($Cleanup) {
        Write-Host "All data has been permanently deleted."
    }
    else {
        Write-Host "Docker volumes have been preserved."
        Write-Host "To remove data later, run:"
        Write-Host "  $ .\uninstall.ps1 -Cleanup"
    }

    Write-Host ""
    Write-Host "To reinstall Enhanced Cognee, run:"
    Write-Host "  $ .\install.ps1"
    Write-Host ""
}

function Show-Help {
    Write-Host "Enhanced Cognee Uninstallation Script for Windows"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\uninstall.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Cleanup    Remove Docker volumes (deletes all data)"
    Write-Host "  -Help       Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\uninstall.ps1           # Stop services only"
    Write-Host "  .\uninstall.ps1 -Cleanup  # Stop and remove all data"
    Write-Host ""
}

function Main {
    Print-Header

    if ($Cleanup) {
        Print-Warn "CLEANUP MODE: All data will be deleted!"
        Write-Host ""
    }

    if (-not (Confirm-Action)) {
        Print-Info "Uninstall cancelled"
        exit 0
    }

    if ($Help) {
        Show-Help
        exit 0
    }

    Stop-Services
    Remove-Volumes

    Print-Completion
}

Main
