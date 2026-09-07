#!/usr/bin/env bash
# Recover Kotak credentials from the old smap-service store into .env.
#
# The old desktop platform kept them Fernet-encrypted in the macOS application
# support directory. This reads that store and copies across whatever it holds
# that live-graph needs. Values are never printed; only field names and lengths.
set -euo pipefail
cd "$(dirname "$0")/.."

.venv/bin/python - "$@" <<'PY'
import json, pathlib, sqlite3, sys

try:
    from cryptography.fernet import Fernet
except ImportError:
    sys.exit("cryptography is not installed in this venv: uv pip install cryptography")

store = pathlib.Path.home() / "Library/Application Support/smap-service"
db, key_file = store / "runtime.sqlite3", store / "credentials.key"
if not db.exists() or not key_file.exists():
    sys.exit(f"No old credential store at {store}")

row = sqlite3.connect(db).execute(
    "SELECT credential_blob, updated_at FROM provider_credentials WHERE provider='kotak_neo'"
).fetchone()
if row is None:
    sys.exit("No kotak_neo credentials in the old store.")

blob, updated = row
creds = json.loads(Fernet(key_file.read_bytes()).decrypt(blob.encode()).decode())
print(f"Old store, saved {updated}. Fields it holds (values not shown):")
for name in sorted(creds):
    value = str(creds[name] or "")
    print(f"  {name:24} {len(value)} chars" if value else f"  {name:24} empty")

WANTED = {
    "consumer_key": "KOTAK_CONSUMER_KEY",
    "mobile_number": "KOTAK_MOBILE_NUMBER",
    "ucc": "KOTAK_UCC",
    "mpin": "KOTAK_MPIN",
    "totp_secret": "KOTAK_TOTP_SECRET",
}
lower = {k.lower(): v for k, v in creds.items() if str(v or "").strip()}
found = {env: lower[field] for field, env in WANTED.items() if field in lower}

print("\nAgainst what live-graph needs:")
for field, env in WANTED.items():
    print(f"  {env:22} {'found' if env in found else 'NOT in the old store'}")

if not found:
    sys.exit(
        "\nNothing usable. The old platform only ever stored an access_token, which is "
        "the REST credential and cannot open a streaming session. Register for TOTP and "
        "run ./scripts/setup-kotak.sh instead."
    )

env_path = pathlib.Path(".env")
if not env_path.exists():
    env_path.write_text(pathlib.Path(".env.example").read_text())

lines = env_path.read_text().splitlines()
kept = [ln for ln in lines if not any(ln.startswith(f"{k}=") for k in found)]
kept += [f"{k}={v}" for k, v in found.items()]
env_path.write_text("\n".join(kept) + "\n")
env_path.chmod(0o600)
print(f"\nWrote {len(found)} value(s) into .env. Run ./scripts/setup-kotak.sh for the rest.")
PY
