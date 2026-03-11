#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="$ROOT_DIR/apps/service"

cd "$SERVICE_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e . pyinstaller

pyinstaller --clean --noconfirm smap_service.spec

mkdir -p dist
if [[ -f dist/smap-service ]]; then
  echo "Built Linux/macOS service binary at dist/smap-service"
fi
if [[ -f dist/smap-service.exe ]]; then
  echo "Built Windows service binary at dist/smap-service.exe"
fi
