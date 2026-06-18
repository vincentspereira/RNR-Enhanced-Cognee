# Enhanced Cognee Desktop Installer

This directory contains everything needed to ship Enhanced Cognee as a
double-click desktop application for Windows, macOS, and Linux.

## What the user gets

A small launcher app ("Enhanced Cognee") that:

1. Checks Docker Desktop is installed and running (and helps the user get
   it if not -- this is the only prerequisite).
2. On first run, writes the runtime stack (docker compose file, database
   bootstrap SQL, auto-generated passwords) to a per-user data directory:
   - Windows: `%LOCALAPPDATA%\EnhancedCognee`
   - macOS:   `~/Library/Application Support/EnhancedCognee`
   - Linux:   `~/.local/share/enhanced-cognee`
3. Starts the full stack with one click (PostgreSQL, Qdrant, ArcadeDB,
   Valkey, the REST API, and the web dashboard).
4. Opens the dashboard at http://localhost:9050 in the default browser.
5. Stop button shuts everything down; all data is preserved in Docker
   volumes and survives restarts, upgrades, and reinstalls.

See `docs/USER_MANUAL.md` for the end-user step-by-step guide.

## Layout

```
installer/
  launcher.py                       The tkinter launcher application
  resources/
    docker-compose.launcher.yml     The runtime stack (prebuilt images only)
    01-init-pgvector.sql            Copied from docker/init-scripts at build time
  build/
    build_windows.ps1               PyInstaller + Inno Setup
    build_macos.sh                  PyInstaller .app + .dmg
    build_linux.sh                  PyInstaller binary + tarball + AppImage
  windows/EnhancedCognee.iss        Inno Setup script
  linux/enhanced-cognee.desktop     Desktop entry
  dist/                             Build outputs (gitignored)
```

## Building locally

All platforms need Python 3.11+ and `pip install pyinstaller`.

- Windows: `powershell -ExecutionPolicy Bypass -File installer\build\build_windows.ps1`
  (install Inno Setup 6 for the Setup.exe wrap; the bare launcher exe is
  produced either way)
- macOS:   `bash installer/build/build_macos.sh` (hdiutil is built in)
- Linux:   `bash installer/build/build_linux.sh` (AppImage requires
  appimagetool on PATH; the tarball is always produced)

Test the launcher without building: `python installer/launcher.py`.

## CI builds

`.github/workflows/build-installers.yml` builds all three platforms and
publishes the two app images the stack pulls:

- `ghcr.io/<owner>/enhanced-cognee-api` (from `dashboard/Dockerfile.api`)
- `ghcr.io/<owner>/enhanced-cognee-dashboard` (from `dashboard/nextjs-dashboard/Dockerfile`)

Trigger by pushing a `v*` tag (also attaches installers to a GitHub
Release) or manually via workflow dispatch.

NOTE: the ghcr images must be public (or the user logged in to ghcr) for
the launcher's `docker compose pull` to succeed. Set package visibility to
public in the GitHub Packages settings after the first push.

## Versioning

Set `EC_VERSION` (env var) before running a build script to stamp the
output filenames; CI derives it from the tag name.

## Code signing (recommended for distribution)

- Windows: sign `EnhancedCogneeLauncher.exe` and the Setup exe with
  signtool + your Authenticode cert to avoid SmartScreen warnings.
- macOS: codesign + notarize the .app/.dmg (see notes printed by
  build_macos.sh) to avoid Gatekeeper blocking.
- Linux: no signing required.
