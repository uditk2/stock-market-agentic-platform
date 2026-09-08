#!/usr/bin/env python
"""Walk the Kotak Neo path one step at a time and say where it breaks.

The app reports a failed feed as one line — "Kotak login failed: ..." — which
is enough to know something is wrong and not enough to fix it. This runs the
same path in stages and names the first one that fails, so a bad MPIN is
distinguishable from a clock skew, an unregistered TOTP, or a market that is
simply closed.

It deliberately goes through `livegraph.feed` rather than the SDK directly.
Testing a parallel implementation would prove the SDK works while leaving open
the question this is actually asked to answer: will the app work.

    ./scripts/check-kotak.py                 # use .env and the admin store
    ./scripts/check-kotak.py --prompt        # type missing values, in memory only
    ./scripts/check-kotak.py --save          # ...and write them to the store
    ./scripts/check-kotak.py --seconds 30    # watch the socket for longer
    ./scripts/check-kotak.py --skip-socket   # stop after the REST checks

No credential is ever printed. Values are reported by presence and length, and
the failure text from the SDK is passed through unchanged, so read it before
pasting it anywhere.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
import threading
import time
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]

#: Guards against a loop if the venv python somehow still cannot import the SDK.
_REEXEC_FLAG = "LIVEGRAPH_CHECK_REEXEC"

#: Run from a checkout without installing anything: scripts/ -> repo -> src/.
sys.path.insert(0, str(APP_ROOT / "src"))


def _reexec_in_venv() -> None:
    """Restart under .venv/bin/python when started by some other interpreter.

    `#!/usr/bin/env python` finds whatever is on PATH, which on a machine with
    a system Python is not the one holding the Neo SDK. Without this the script
    reports the SDK as missing when it is installed a directory away, which is
    the most misleading failure it could possibly open with.
    """
    venv_python = APP_ROOT / ".venv" / "bin" / "python"
    already_here = Path(sys.executable).resolve() == venv_python.resolve()
    if already_here or not venv_python.exists() or os.environ.get(_REEXEC_FLAG):
        return
    os.environ[_REEXEC_FLAG] = "1"
    print(f"Re-running under {venv_python}")
    os.execv(str(venv_python), [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]])


PASS, FAIL, INFO, WARN = "  PASS", "  FAIL", "  ....", "  WARN"

#: Headroom for the login round trip. `TotpCode.about_to_rotate` allows three
#: seconds, which suits displaying a code and not spending one.
MIN_TOTP_SECONDS = 6


class Stage:
    """A named step that prints its own verdict and stops the run on failure."""

    def __init__(self, number: int, title: str):
        self.number = number
        self.title = title

    def __enter__(self):
        print(f"\n{self.number}. {self.title}")
        return self

    def __exit__(self, kind, value, traceback):
        if kind is None:
            return False
        print(f"{FAIL} {value}")
        #: Later stages depend on this one, so continuing would report a cascade
        #: of failures that all have the same single cause.
        print("\nStopped here. Fix this and run again.")
        sys.exit(1)


def main() -> int:
    options = parse_args()
    #: `.env` is read relative to the working directory by pydantic-settings, so
    #: the script must behave the same whichever directory it was invoked from.
    os.chdir(APP_ROOT)
    print("Kotak Neo connectivity check")
    print("Credentials are never printed; fields are reported by presence only.")

    with Stage(1, "The Neo SDK is importable"):
        import neo_api_client

        location = Path(neo_api_client.__file__).parent
        print(f"{PASS} neo_api_client at {location}")

    with Stage(2, "Credentials resolve"):
        settings = resolve_credentials(options)
        report_fields(settings)
        missing = settings.missing_fields()
        if missing:
            raise RuntimeError(
                f"missing or placeholder: {', '.join(missing)}. "
                "Re-run with --prompt, use the Admin tab, or ./scripts/setup-kotak.sh"
            )
        print(f"{PASS} all five present")

    with Stage(3, "TOTP derives from the stored secret"):
        from livegraph.feed.totp import current_code

        code = current_code(settings.totp_secret)
        if code.expires_in < MIN_TOTP_SECONDS:
            #: A code still valid when sent can expire before Kotak checks it,
            #: which comes back as "invalid TOTP" and reads like a wrong secret.
            #: `about_to_rotate` allows 3s, which is fine for showing a code on
            #: screen and too tight for a login over the network.
            print(f"{INFO} {code.expires_in}s left on this code, waiting for the next")
            time.sleep(code.expires_in + 1)
            code = current_code(settings.totp_secret)
        print(f"{PASS} current code {code.code}, rotates in {code.expires_in}s")
        print(f"{INFO} check this matches your authenticator app right now")

    with Stage(4, "Login: totp_login then totp_validate"):
        from livegraph.feed import KotakSession

        session = KotakSession(settings)
        client = session.login()
        print(f"{PASS} session established for UCC ending {settings.ucc[-3:]}")

    with Stage(5, "Scrip master downloads and parses"):
        from livegraph.feed import Segment, nearest_expiry_per_underlying, parse_instruments

        rows = client.scrip_master(exchange_segment=str(Segment.FNO))
        if isinstance(rows, dict) and "Error Message" in rows:
            raise RuntimeError(f"scrip_master rejected: {rows['Error Message']}")
        instruments = parse_instruments(rows, Segment.FNO)
        nearest = nearest_expiry_per_underlying(instruments)
        print(f"{PASS} {len(instruments)} F&O contracts, {len(nearest)} at nearest expiry")
        if not nearest:
            raise RuntimeError("no contracts parsed; the scrip master format may have changed")

    with Stage(6, "Contracts intersect the graph universe"):
        from livegraph.graph import GraphRepository, NodeType
        from livegraph.paths import data_dir

        repo = GraphRepository.from_file(data_dir() / "stock_graph.json")
        tradable = {node.id for node in repo.nodes_of_type(NodeType.STOCK)}
        selected = [i for i in nearest if i.underlying in tradable]
        print(f"{PASS} {len(selected)} of {len(nearest)} map onto the {len(tradable)}-stock graph")
        if not selected:
            raise RuntimeError(
                "no contract matched a graph symbol; the app would show an empty screen"
            )

    if options.skip_socket:
        print("\nSkipped the socket check. REST access works.")
        return 0

    with Stage(7, f"WebSocket delivers ticks (watching {options.seconds}s)"):
        from livegraph.feed import TickStream

        received: list = []
        first_tick = threading.Event()

        def on_tick(tick) -> None:
            received.append(tick)
            first_tick.set()

        stream = TickStream(client, selected)
        stream.add_handler(on_tick)
        stream.start()
        try:
            first_tick.wait(timeout=options.seconds)
            #: Give a quiet book a moment past the first print, so the count
            #: below reflects a short window rather than a single instant.
            time.sleep(min(2.0, options.seconds))
            connected = stream.is_connected
            symbols = len(stream.snapshot())
        finally:
            stream.stop()

        print(f"{PASS if connected else FAIL} socket connected={connected}")
        print(f"{INFO} {len(received)} ticks for {symbols} symbols in {options.seconds}s")
        if not received:
            print(f"{WARN} no ticks. Outside 09:15-15:30 IST on a trading day this is")
            print(f"{WARN} expected: the socket connects and simply stays quiet.")

    print("\nAll checks passed. The app will run on this configuration.")
    if options.prompt and not options.save:
        print("Values were held in memory only. Re-run with --save to keep them.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--prompt", action="store_true",
        help="type any missing credentials, with terminal echo off",
    )
    parser.add_argument(
        "--save", action="store_true",
        help="with --prompt, write them to the admin credential store",
    )
    parser.add_argument(
        "--seconds", type=int, default=15, help="how long to watch the socket (default 15)",
    )
    parser.add_argument("--skip-socket", action="store_true", help="stop after the REST checks")
    return parser.parse_args()


def resolve_credentials(options: argparse.Namespace):
    """Settings as the app sees them, optionally topped up from the terminal."""
    from livegraph.feed.config import KotakSettings, load_kotak_settings

    settings = load_kotak_settings()
    if not options.prompt:
        return settings

    typed: dict[str, str] = {}
    for name in KotakSettings.REQUIRED:
        if name not in settings.missing_fields():
            continue
        value = getpass.getpass(f"    {name} (hidden, blank to skip): ").strip()
        if value:
            typed[name] = value

    if not typed:
        return settings
    if options.save:
        from livegraph.credentials import write

        print(f"{INFO} saved to the credential store: {', '.join(write(typed))}")
        return load_kotak_settings()
    return settings.model_copy(update=typed)


def report_fields(settings) -> None:
    """Presence, length and origin. Never the value."""
    from livegraph.credentials import sources
    from livegraph.feed.config import KotakSettings

    missing = set(settings.missing_fields())
    placeholders = set(settings.placeholder_fields())
    origin = sources(
        {name: "" if name in missing else getattr(settings, name) for name in KotakSettings.REQUIRED}
    )
    for name in KotakSettings.REQUIRED:
        value = getattr(settings, name) or ""
        if name in placeholders:
            state = "placeholder text, not a value"
        elif name in missing:
            state = "missing"
        else:
            state = f"set, {len(value)} chars, from {origin.get(name, '?')}"
        print(f"{INFO} {name:14} {state}")


if __name__ == "__main__":
    _reexec_in_venv()
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
