#!/usr/bin/env bash
set -euo pipefail

APP_PATH="${1:-/Applications/SMAP Desktop.app}"

if [[ ! -d "$APP_PATH" ]]; then
  echo "App not found at: $APP_PATH" >&2
  echo "Usage: $0 \"/Applications/SMAP Desktop.app\"" >&2
  exit 1
fi

echo "Removing macOS quarantine flag from: $APP_PATH"
xattr -dr com.apple.quarantine "$APP_PATH"
echo "Done. You can now launch SMAP Desktop."
