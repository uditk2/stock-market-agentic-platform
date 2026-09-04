# One image, one container, one port.
#
# The backend serves the API, the WebSocket feed and the exported UI, and hosts
# the strategy sandbox in-process as a Pyodide (WASM) runtime. No Docker socket
# is mounted and no sibling containers are started.

# ---- 1. Build the UI -------------------------------------------------
FROM node:22-slim AS ui-builder
WORKDIR /build
COPY web/package.json web/package-lock.json* ./
RUN npm ci
COPY web/ ./
# Static export: the UI is entirely client-side, so it ships as files rather
# than as a second Node process.
RUN npm run build

# ---- 2. Build the sandbox worker ------------------------------------
FROM node:22-slim AS sandbox-builder
WORKDIR /worker
COPY src/livegraph/scratchpad/sandbox/worker/package.json ./
RUN npm install --omit=dev
COPY src/livegraph/scratchpad/sandbox/worker/sandbox_worker.mjs ./
# Pyodide fetches its wheels from a CDN on first use and caches them under
# node_modules. Warm that cache now so the running container needs no network
# to start a strategy.
RUN node -e "                                                     \
  const { loadPyodide } = require('pyodide');                     \
  loadPyodide({ jsglobals: {} })                                  \
    .then(py => py.loadPackage(['numpy','pandas','scipy','matplotlib'])) \
    .then(() => console.log('pyodide wheels cached'))             \
    .catch(e => { console.error(e); process.exit(1); });"

# ---- 3. Runtime ------------------------------------------------------
FROM python:3.13-slim AS runtime

# Node runs the sandbox worker. The binary alone is enough: the worker's
# node_modules are copied in already resolved, so npm is not needed at runtime.
COPY --from=node:22-slim /usr/local/bin/node /usr/local/bin/node

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY src/ ./src/
# git resolves the Kotak Neo SDK, which is not on PyPI. It is removed in the
# same layer so it does not ship in the final image.
#
# The SDK is installed with --no-deps on purpose: it hard-pins websockets==8.1
# (no Python 3.13 wheel, and it collides with uvicorn) and asyncio==3.4.3, a
# dead PyPI package that shadows the standard library. The [kotak] extra
# supplies the libraries it actually imports, at working versions.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && pip install --no-cache-dir ".[kotak]" \
 && pip install --no-cache-dir --no-deps \
      "neo_api_client @ git+https://github.com/Kotak-Neo/Kotak-neo-api-v2.git@v2.0.2" \
 && apt-get purge -y git && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

COPY data/ ./data/
COPY --from=ui-builder /build/out ./web/out

# The package is installed into site-packages, so the worker is staged at a
# fixed path and pointed at explicitly rather than found relative to __file__.
COPY --from=sandbox-builder /worker/node_modules ./sandbox-worker/node_modules
COPY src/livegraph/scratchpad/sandbox/worker/sandbox_worker.mjs ./sandbox-worker/
ENV LIVEGRAPH_DATA_DIR=/app/data \
    LIVEGRAPH_UI_DIR=/app/web/out \
    LIVEGRAPH_SANDBOX_WORKER_DIR=/app/sandbox-worker

# The sandbox already confines strategy code inside WASM; running the service
# itself as non-root keeps the blast radius small if the API is compromised.
RUN useradd --create-home --uid 10001 livegraph && chown -R livegraph:livegraph /app
USER livegraph

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/health',timeout=4)"

CMD ["python", "-m", "uvicorn", "livegraph.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
