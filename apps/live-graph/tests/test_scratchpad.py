"""Regressions guarded here:

Strategy code is written by a model and executed by us, so the isolation
boundary is the whole point. These assert it directly against the live runtime
rather than trusting the design:

- `js.globalThis.process.env` must be unreachable. Without `jsglobals: {}` in
  the worker it resolves to the backend's real environment, handing generated
  code the Kotak credentials and the CLIProxy key.
- `pyodide.code.run_js` must be unreachable, or a strategy can execute
  arbitrary JavaScript on the host.
- The network must be dead. Raw sockets connect cosmetically under Emscripten,
  so this asserts no bytes can actually move, not merely that connect failed.
- A runaway loop must be killed and the sandbox must recover for the next run.
"""

import time

import pytest

from livegraph.scratchpad import (
    MarketSnapshot,
    PyodideSandbox,
    RunStatus,
    validate,
)


@pytest.fixture
def snapshot():
    return MarketSnapshot(
        taken_at=1725441000.0,
        prices={
            "RELIANCE": {"ltp": 1400.0, "change_pct": 2.0, "segment": "nse_fo"},
            "INFY": {"ltp": 1500.0, "change_pct": -1.0, "segment": "nse_fo"},
            "TCS": {"ltp": 3200.0, "change_pct": -1.2, "segment": "nse_fo"},
        },
        peers={"INFY": ["TCS", "WIPRO"], "TCS": ["INFY", "WIPRO"]},
        sectors={"INFY": "Information Technology", "TCS": "Information Technology"},
        sector_members={"Information Technology": ["INFY", "TCS", "WIPRO"]},
        news={"INFY": [{"title": "Infosys wins deal", "ts": 1.0, "source": "ET"}]},
        fo_symbols=["RELIANCE", "INFY", "TCS"],
    )


@pytest.fixture(scope="module")
def sandbox():
    box = PyodideSandbox(timeout_seconds=45)
    if not box.is_available():
        pytest.skip(f"sandbox unavailable: {box.unavailable_reason()}")
    box.start()
    yield box
    box.stop()


# ---- validator (linting only; WASM is the boundary) ------------------


def test_validator_requires_the_entrypoint():
    assert not validate("def other(ctx): return {}").ok
    assert not validate("def run(): return {}").ok
    assert validate("def run(ctx): return {}").ok


def test_validator_reports_syntax_errors():
    assert "syntax error" in validate("def run(ctx) return {}").message


def test_validator_allows_the_scientific_stack():
    assert validate("import numpy as np\nimport pandas as pd\ndef run(ctx): return {}").ok


# ---- isolation -------------------------------------------------------


@pytest.mark.sandbox
def test_host_environment_is_unreachable(sandbox, snapshot):
    """The single most important guarantee: no access to backend credentials."""
    code = (
        "import js\n"
        "def run(ctx):\n"
        "    return {'env': str(js.globalThis.process.env)}\n"
    )
    result = sandbox.run(code, snapshot)
    assert result.status is RunStatus.ERROR
    assert "env" not in str(result.output or "")


@pytest.mark.sandbox
def test_os_environ_is_the_sandbox_not_the_host(sandbox, snapshot):
    result = sandbox.run("import os\ndef run(ctx): return dict(os.environ)", snapshot)
    assert result.ok, result.error
    #: Emscripten's synthetic environment, never the backend's.
    assert result.output.get("USER") == "web_user"
    assert "KOTAK_CONSUMER_KEY" not in result.output
    assert "CLIPROXY_API_KEY" not in result.output


@pytest.mark.sandbox
def test_javascript_execution_is_unreachable(sandbox, snapshot):
    code = (
        "from pyodide.code import run_js\n"
        "def run(ctx):\n"
        "    return {'got': str(run_js('globalThis.process.env.HOME'))}\n"
    )
    assert sandbox.run(code, snapshot).status is RunStatus.ERROR


@pytest.mark.sandbox
def test_network_cannot_transfer_data(sandbox, snapshot):
    """Emscripten sockets connect cosmetically, so assert on bytes, not connect."""
    code = (
        "import socket\n"
        "def run(ctx):\n"
        "    s = socket.create_connection(('example.com', 80), timeout=3)\n"
        "    s.sendall(b'GET / HTTP/1.0\\r\\nHost: example.com\\r\\n\\r\\n')\n"
        "    return {'received': len(s.recv(100))}\n"
    )
    result = sandbox.run(code, snapshot)
    assert result.status in (RunStatus.ERROR, RunStatus.TIMEOUT)
    assert not (result.output or {})


@pytest.mark.sandbox
def test_https_is_unavailable(sandbox, snapshot):
    code = (
        "import urllib.request\n"
        "def run(ctx):\n"
        "    return {'status': urllib.request.urlopen('https://example.com', timeout=3).status}\n"
    )
    assert sandbox.run(code, snapshot).status in (RunStatus.ERROR, RunStatus.TIMEOUT)


@pytest.mark.sandbox
def test_subprocesses_are_unavailable(sandbox, snapshot):
    code = "import subprocess\ndef run(ctx): return {'out': str(subprocess.run(['ls']))}"
    assert sandbox.run(code, snapshot).status is RunStatus.ERROR


@pytest.mark.sandbox
def test_host_files_are_unreachable(sandbox, snapshot):
    code = "def run(ctx): return {'passwd': open('/etc/passwd').read()[:20]}"
    assert sandbox.run(code, snapshot).status is RunStatus.ERROR


# ---- execution -------------------------------------------------------


@pytest.mark.sandbox
def test_runs_a_plain_strategy(sandbox, snapshot):
    code = (
        "def run(ctx):\n"
        "    rows = sorted(\n"
        "        ({'symbol': s, 'change_pct': p.get('change_pct') or 0.0}\n"
        "         for s, p in ctx.prices.items()),\n"
        "        key=lambda r: -r['change_pct'])\n"
        "    return {'rows': rows}\n"
    )
    result = sandbox.run(code, snapshot)
    assert result.ok, result.error
    assert result.output["rows"][0]["symbol"] == "RELIANCE"


@pytest.mark.sandbox
def test_peers_and_sectors_reach_the_strategy(sandbox, snapshot):
    code = (
        "def run(ctx):\n"
        "    return {'peers': ctx.peers.get('INFY', []), 'sector': ctx.sectors.get('INFY')}\n"
    )
    result = sandbox.run(code, snapshot)
    assert result.ok, result.error
    assert result.output["peers"] == ["TCS", "WIPRO"]
    assert result.output["sector"] == "Information Technology"


@pytest.mark.sandbox
def test_pandas_dataframe_survives_the_json_boundary(sandbox, snapshot):
    code = (
        "import pandas as pd\n"
        "def run(ctx):\n"
        "    df = pd.DataFrame([{'symbol': s, 'ltp': p['ltp']} for s, p in ctx.prices.items()])\n"
        "    return {'rows': df.sort_values('ltp', ascending=False)}\n"
    )
    result = sandbox.run(code, snapshot)
    assert result.ok, result.error
    assert result.output["rows"][0]["symbol"] == "TCS"


@pytest.mark.sandbox
def test_numpy_scalars_are_coerced(sandbox, snapshot):
    code = (
        "import numpy as np\n"
        "def run(ctx):\n"
        "    moves = np.array([p.get('change_pct') or 0.0 for p in ctx.prices.values()])\n"
        "    return {'mean': moves.mean(), 'all': moves}\n"
    )
    result = sandbox.run(code, snapshot)
    assert result.ok, result.error
    assert isinstance(result.output["mean"], float)
    assert isinstance(result.output["all"], list)


@pytest.mark.sandbox
def test_matplotlib_figure_is_returned_as_png(sandbox, snapshot):
    import base64

    code = (
        "import matplotlib.pyplot as plt\n"
        "def run(ctx):\n"
        "    symbols = list(ctx.prices)\n"
        "    plt.figure()\n"
        "    plt.bar(symbols, [ctx.prices[s]['ltp'] for s in symbols])\n"
        "    return {'plotted': symbols}\n"
    )
    result = sandbox.run(code, snapshot)
    assert result.ok, result.error
    assert result.has_figures
    assert base64.b64decode(result.figures[0])[:4] == b"\x89PNG"


@pytest.mark.sandbox
def test_figures_do_not_leak_into_the_next_run(sandbox, snapshot):
    """A figure left open by one strategy must not be attributed to the next."""
    plotting = (
        "import matplotlib.pyplot as plt\n"
        "def run(ctx):\n    plt.figure()\n    plt.plot([1, 2, 3])\n    return {'ok': 1}\n"
    )
    assert sandbox.run(plotting, snapshot).has_figures
    assert not sandbox.run("def run(ctx): return {'ok': 1}", snapshot).has_figures


@pytest.mark.sandbox
def test_runtime_error_is_reported_not_raised(sandbox, snapshot):
    result = sandbox.run("def run(ctx): return 1 / 0", snapshot)
    assert result.status is RunStatus.ERROR
    assert "ZeroDivisionError" in result.error


@pytest.mark.sandbox
def test_rejected_code_never_reaches_the_sandbox(sandbox, snapshot):
    result = sandbox.run("def wrong(ctx): return {}", snapshot)
    assert result.status is RunStatus.REJECTED
    assert result.duration_ms == 0


@pytest.mark.sandbox
def test_runaway_loop_is_killed_and_the_sandbox_recovers():
    """WASM cannot be interrupted, so the worker is killed and respawned."""
    box = PyodideSandbox(timeout_seconds=8)
    if not box.is_available():
        pytest.skip(box.unavailable_reason())
    snap = MarketSnapshot(taken_at=1.0, prices={"A": {"ltp": 1.0, "change_pct": 0.0}})

    started = time.monotonic()
    result = box.run("def run(ctx):\n    while True: pass\n", snap)
    assert result.status is RunStatus.TIMEOUT
    assert time.monotonic() - started < 40

    #: The next run must work, proving the worker respawned.
    recovered = box.run("def run(ctx): return {'ok': 1}", snap)
    assert recovered.ok, recovered.error
    box.stop()


@pytest.mark.sandbox
def test_warm_worker_keeps_runs_fast(sandbox, snapshot):
    """Boot cost is paid once, not per run."""
    sandbox.run("def run(ctx): return {'ok': 1}", snapshot)
    result = sandbox.run("def run(ctx): return {'ok': 2}", snapshot)
    assert result.ok
    assert result.duration_ms < 3000, f"warm run took {result.duration_ms}ms"
