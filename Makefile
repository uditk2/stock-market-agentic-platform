.PHONY: install test run docker

install:
	cd apps/live-graph && uv venv --python 3.13 .venv && uv pip install -e ".[dev,kotak]"
	cd apps/live-graph/web && npm install
	cd apps/live-graph/src/livegraph/scratchpad/sandbox/worker && npm install

test:
	cd apps/live-graph && PYTHONPATH=src .venv/bin/python -m pytest tests/ -q

run:
	cd apps/live-graph && npm --prefix web run build && \
		LIVEGRAPH_SIMULATE=1 PYTHONPATH=src .venv/bin/python -m uvicorn livegraph.api.app:app --port 8000

docker:
	cd apps/live-graph && docker compose up --build
