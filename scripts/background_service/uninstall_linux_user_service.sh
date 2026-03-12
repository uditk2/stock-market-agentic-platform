#!/usr/bin/env bash
set -euo pipefail

UNIT_NAME="${1:-smap-service}"
UNIT_FILE="$HOME/.config/systemd/user/${UNIT_NAME}.service"

systemctl --user disable --now "${UNIT_NAME}.service" >/dev/null 2>&1 || true
rm -f "$UNIT_FILE"
systemctl --user daemon-reload

echo "Uninstalled ${UNIT_NAME}.service"
