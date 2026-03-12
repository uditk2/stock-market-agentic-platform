#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UNIT_NAME="smap-service"
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
    --unit-name)
      UNIT_NAME="$2"
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

mkdir -p "$HOME/.config/systemd/user"
TMP_FILE="$(mktemp)"

RENDER_CMD=(
  node "$ROOT_DIR/apps/desktop/main/render_service_template.js"
  --target linux
  --output "$TMP_FILE"
  --working-directory "$WORKING_DIR"
  --service-bin "$SERVICE_BIN"
  --description "$DESCRIPTION"
)

for arg in "${SERVICE_ARGS[@]}"; do
  RENDER_CMD+=(--arg "$arg")
done

"${RENDER_CMD[@]}"
cp "$TMP_FILE" "$HOME/.config/systemd/user/${UNIT_NAME}.service"
rm -f "$TMP_FILE"

systemctl --user daemon-reload
systemctl --user enable --now "${UNIT_NAME}.service"

echo "Installed and started ${UNIT_NAME}.service"
