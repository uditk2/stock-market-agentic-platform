.PHONY: service-install service-test service-run desktop-install desktop-dev

service-install:
	cd apps/service && python3 -m venv .venv && . .venv/bin/activate && pip install -e .[dev]

service-test:
	cd apps/service && . .venv/bin/activate && pytest -q

service-run:
	cd apps/service && . .venv/bin/activate && uvicorn smap_service.main:app --reload --port 8787

desktop-install:
	cd apps/desktop && npm install

desktop-dev:
	cd apps/desktop && npm run dev
