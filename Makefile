.PHONY: install test run docker proxy check-kotak

install:
	cd apps/live-graph && uv venv --python 3.13 .venv && uv pip install -e ".[dev,kotak]"
	# The Neo SDK is not on PyPI and hard-pins a broken tree, so it is resolved
	# from git without its own deps; [kotak] above supplies what it imports.
	cd apps/live-graph && .venv/bin/python -m pip install --no-deps -q \
		"neo_api_client @ git+https://github.com/Kotak-Neo/Kotak-neo-api-v2.git@v2.0.2"
	cd apps/live-graph/web && npm install
	cd apps/live-graph/src/livegraph/scratchpad/sandbox/worker && npm install

test:
	cd apps/live-graph && PYTHONPATH=src .venv/bin/python -m pytest tests/ -q

run:
	cd apps/live-graph && npm --prefix web run build && \
		PYTHONPATH=src .venv/bin/python -m uvicorn livegraph.api.app:app --port 8000

# Walk the Kotak path stage by stage and name the first thing that fails.
# `make check-kotak ARGS="--prompt --save"` to type missing credentials in.
check-kotak:
	cd apps/live-graph && ./scripts/check-kotak.py $(ARGS)

docker:
	cd apps/live-graph && docker compose up --build

# A CLIProxyAPI of your own, for a machine that has none. Skip it if one is
# already running; see apps/live-graph/README.md#a-proxy-of-your-own.
proxy:
	cd apps/live-graph && docker compose --profile local-proxy up --build cliproxy
