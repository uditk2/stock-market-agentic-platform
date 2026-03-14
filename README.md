# Stock Market Agentic Platform

Modular desktop platform scaffold for NSE F&O signal/recommendation workflows.

## Monorepo Layout
- `apps/service`: Python background service (scheduler + ingestion + APIs + plugin registries)
- `apps/desktop`: Electron desktop shell (wizard + terminal + service control)
- `packages/contracts`: shared contracts used by service and desktop
- `.github/workflows`: CI build and packaging pipeline

## Quick Start

### Installer Runtime (Preferred)
1. Install SMAP Desktop package for your OS.
2. Launch desktop app.
3. In Setup Wizard:
- run mandatory CLI checks
- use `Install Background Service` when prompted
4. After wizard passes, workspace unlocks and service is managed without manual service-install commands.

### macOS Unsigned Install (No Notarization)
Direct latest DMG (private GitHub release link; requires repo access):
- https://github.com/uditk2/stock-market-agentic-platform/releases/tag/smap-mac-latest

If macOS reports the app as damaged/blocked, run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/uditk2/stock-market-agentic-platform/master/scripts/macos/unblock_unsigned_app.sh)"
```

Or run locally from repo checkout:

```bash
scripts/macos/unblock_unsigned_app.sh "/Applications/SMAP Desktop.app"
```

### Service
```bash
cd apps/service
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn smap_service.main:app --reload --port 18787
```

### Desktop
```bash
cd apps/desktop
npm install
npm run dev
```

In source mode, desktop will auto-try local service binary (`apps/service/dist`) and then fall back to `python3 -m uvicorn ...` when needed.

In packaged installer mode, desktop auto-resolves bundled service binary from app resources (`resources/service/`) so install-and-run works without manual `SMAP_SERVICE_BIN` setup.

## Current Sprint Status
Sprint 1 scaffolding implemented with pluggable interfaces:
- `LLMAdapter`
- `NewsProvider`
- `StrategyModule`

Background scheduler runs inside service process and is designed to keep ingestion jobs independent from the UI lifecycle.

## W5 Background Service Install Helpers
- Linux (`systemd --user`):
```bash
scripts/background_service/install_linux_user_service.sh --service-bin /abs/path/to/smap-service
scripts/background_service/uninstall_linux_user_service.sh
```
- macOS (`launchd` LaunchAgent):
```bash
scripts/background_service/install_macos_launchagent.sh --service-bin /abs/path/to/smap-service
scripts/background_service/uninstall_macos_launchagent.sh
```
- Windows (Task Scheduler):
```powershell
powershell -ExecutionPolicy Bypass -File scripts/background_service/install_windows_task.ps1 -ServiceBin C:\path\to\smap-service.exe
powershell -ExecutionPolicy Bypass -File scripts/background_service/uninstall_windows_task.ps1
```

All installers default to user-scoped registration and support optional `--arg`/`-ServiceArgs` for service runtime flags.
