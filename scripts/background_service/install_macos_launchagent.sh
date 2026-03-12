#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LABEL="com.smap.service"
SERVICE_BIN=""
WORKING_DIR="$ROOT_DIR"
SERVICE_ARGS=()
DESCRIPTION="SMAP Background Service"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --service-bin)
      SERVICE_BIN="$2"
      shift 2
      ;;
    --working-dir)
      WORKING_DIR="$2"
      shift 2
      ;;
    --arg)
      SERVICE_ARGS+=("$2")
      shift 2
      ;;
    --label)
      LABEL="$2"
      shift 2
      ;;
    --description)
      DESCRIPTION="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$SERVICE_BIN" ]]; then
  if [[ -x "$ROOT_DIR/apps/service/dist/smap-service" ]]; then
    SERVICE_BIN="$ROOT_DIR/apps/service/dist/smap-service"
  else
    echo "Missing --service-bin and no default binary found at apps/service/dist/smap-service" >&2
    exit 1
  fi
fi

PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
mkdir -p "$HOME/Library/LaunchAgents"

RENDER_CMD=(
  node "$ROOT_DIR/apps/desktop/main/render_service_template.js"
  --target macos
  --output "$PLIST_PATH"
  --working-directory "$WORKING_DIR"
  --service-bin "$SERVICE_BIN"
  --label "$LABEL"
  --description "$DESCRIPTION"
)

for arg in "${SERVICE_ARGS[@]}"; do
  RENDER_CMD+=(--arg "$arg")
done

"${RENDER_CMD[@]}"
launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl load "$PLIST_PATH"

echo "Installed and loaded ${LABEL} LaunchAgent"
