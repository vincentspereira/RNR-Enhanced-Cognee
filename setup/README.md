# Enhanced Cognee Setup Scripts

This directory contains installation and setup scripts for Enhanced Cognee.

## Installation

### Linux / macOS
```bash
# Standard installation
./setup/install.sh

# Lite installation (minimal dependencies)
./setup/install_lite.sh
```

### Windows
```powershell
# Standard installation
.\setup\install.ps1

# Lite installation (minimal dependencies)
.\setup\install_lite.ps1
```

## Uninstallation

### Linux / macOS
```bash
./setup/uninstall.sh
```

### Windows
```powershell
.\setup\uninstall.ps1
```

## Docker Entrypoint
- `entrypoint.sh` - Docker container entrypoint script

## Python Installer
The `install.py` script in the `bin/` directory provides an alternative Python-based installation method.

## For More Information

See the [Installation Guide](../docs/guides/) in the documentation.
