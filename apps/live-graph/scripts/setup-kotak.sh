#!/usr/bin/env bash
# Fill the Kotak credentials in .env without printing them.
#
# Values are read with the terminal echo off and written straight to .env, so
# nothing lands in your shell history, your scrollback, or an agent transcript.
# Run it yourself; it needs no arguments.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=".env"
[ -f "$ENV_FILE" ] || cp .env.example "$ENV_FILE"

# Writes KEY=value into .env, replacing any existing line for that key.
set_key() {
  local key="$1" value="$2" tmp
  tmp="$(mktemp)"
  grep -v "^${key}=" "$ENV_FILE" > "$tmp" || true
  printf '%s=%s\n' "$key" "$value" >> "$tmp"
  mv "$tmp" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
}

# Prompts with echo off, keeps the current value when the answer is blank.
ask() {
  local key="$1" prompt="$2" current value
  current="$(grep "^${key}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)"
  local shown="not set"
  case "$current" in
    "" ) shown="not set" ;;
    \#* ) shown="placeholder text, needs replacing" ;;
    *  ) shown="already set (${#current} chars)" ;;
  esac
  printf '\n%s\n  currently: %s\n' "$prompt" "$shown"
  read -r -s -p "  value (blank to keep): " value
  echo
  [ -n "$value" ] && set_key "$key" "$value"
}

echo "Kotak Neo credentials. Nothing you type is echoed or logged."

ask KOTAK_CONSUMER_KEY "Consumer key   (Neo app: Invest tab, Trade API card, generate application)"
ask KOTAK_MOBILE_NUMBER "Mobile number  (with country code, e.g. +919876543210)"
ask KOTAK_UCC          "UCC            (Unique Client Code, in your Neo profile)"
ask KOTAK_MPIN         "MPIN           (your Neo MPIN)"
ask KOTAK_TOTP_SECRET  "TOTP secret    (base32 from the one-time QR registration)"

echo
echo "Checking what was written..."
.venv/bin/python - <<'PY'
import sys
sys.path.insert(0, "src")
from livegraph.feed import KotakSettings
from livegraph.feed.config import load_kotak_settings
from livegraph.feed.totp import TotpError, current_code

#: The store the Admin tab writes to overrides .env, so report what the app
#: will actually use. Reading .env alone would call a field missing that the
#: Admin tab had already set.
settings = load_kotak_settings()
missing = settings.missing_fields()
for field in KotakSettings.REQUIRED:
    value = getattr(settings, field)
    if not value:
        state = "missing"
    elif value.strip().startswith("#"):
        state = "still placeholder text"
    else:
        state = f"set ({len(value)} chars)"
    print(f"  {field:16} {state}")

if settings.totp_secret and not settings.totp_secret.strip().startswith("#"):
    try:
        code = current_code(settings.totp_secret)
        print(f"\n  TOTP secret is valid. Current code {code.code}, rotates in {code.expires_in}s.")
        print("  Check it matches your authenticator app right now.")
    except TotpError as exc:
        print(f"\n  TOTP secret rejected: {exc}")

print("\nConfigured." if not missing else f"\nStill missing: {', '.join(missing)}")
PY
