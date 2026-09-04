/**
 * Long-lived Pyodide host for strategy code.
 *
 * Runs inside the backend rather than a sibling container, so the isolation is
 * the WASM boundary itself. Measured against this runtime with `jsglobals: {}`:
 * the host filesystem, the host environment, `js.globalThis`, `js.fetch`,
 * `pyodide.code.run_js`, subprocesses and TLS are all unreachable, and raw
 * sockets connect cosmetically but can never transfer a byte.
 *
 * `jsglobals: {}` is load-bearing. Without it `js.globalThis.process.env`
 * hands generated code the backend's Kotak and CLIProxy credentials.
 *
 * Protocol: one JSON request per line on stdin, one JSON reply per line on
 * stdout. The parent kills this process to enforce a timeout, so nothing here
 * needs its own watchdog.
 */

import { loadPyodide } from "pyodide";
import { createInterface } from "node:readline";

const PACKAGES = ["numpy", "pandas", "scipy", "matplotlib"];

const RUNTIME = `
import base64, io, json, sys
from types import SimpleNamespace

MAX_FIGURES = 6
MAX_STDOUT_CHARS = 8000


def _capture_figures():
    """Render any figures the strategy left open, then clear them."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    figures = []
    for num in plt.get_fignums()[:MAX_FIGURES]:
        buffer = io.BytesIO()
        try:
            plt.figure(num).savefig(buffer, format="png", dpi=110, bbox_inches="tight")
        except Exception:
            continue
        figures.append(base64.b64encode(buffer.getvalue()).decode("ascii"))
    plt.close("all")
    return figures


def _jsonable(value):
    """Coerce numpy and pandas results into plain JSON."""
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        pass
    if hasattr(value, "columns") and hasattr(value, "to_dict"):
        return _jsonable(value.to_dict(orient="records"))
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)


def _run(code, snapshot):
    """Execute one strategy in a fresh namespace and report, never raise."""
    import traceback

    captured = io.StringIO()
    real_stdout, sys.stdout = sys.stdout, captured
    try:
        namespace = {}
        exec(compile(code, "<strategy>", "exec"), namespace)
        if "run" not in namespace:
            raise NameError("no run(ctx) function was defined")
        output = namespace["run"](SimpleNamespace(**snapshot))
        payload = {
            "output": _jsonable(output),
            "figures": _capture_figures(),
            "stdout": captured.getvalue()[:MAX_STDOUT_CHARS],
        }
    except Exception as exc:
        lines = traceback.format_exc().splitlines()
        # Keep only the strategy's own frames. Runner frames ("<exec>") are
        # noise to the model and send it fixing code it did not write.
        own = [l for l in lines if "<exec>" not in l or "line 1" in l]
        payload = {
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": "\\n".join(own)[:3000],
            "stdout": captured.getvalue()[:MAX_STDOUT_CHARS],
        }
    finally:
        sys.stdout = real_stdout
        _capture_figures()  # never leak figures into the next run
    return json.dumps(payload)
`;

function emit(payload) {
  process.stdout.write(JSON.stringify(payload) + "\n");
}

async function main() {
  let pyodide;
  try {
    // jsglobals: {} severs the bridge from Python to this Node process.
    pyodide = await loadPyodide({ jsglobals: {}, stdout: () => {}, stderr: () => {} });
    await pyodide.loadPackage(PACKAGES);
    pyodide.runPython(RUNTIME);
  } catch (error) {
    emit({ type: "fatal", error: String(error) });
    process.exit(1);
  }

  emit({ type: "ready", packages: PACKAGES });

  const lines = createInterface({ input: process.stdin });
  for await (const line of lines) {
    if (!line.trim()) continue;
    let request;
    try {
      request = JSON.parse(line);
    } catch {
      continue;
    }
    try {
      const run = pyodide.globals.get("_run");
      const raw = run(request.code, pyodide.toPy(request.snapshot));
      emit({ type: "result", id: request.id, payload: JSON.parse(raw) });
    } catch (error) {
      emit({
        type: "result",
        id: request.id,
        payload: { error: `sandbox host error: ${String(error).slice(0, 500)}` },
      });
    }
  }
}

main();
