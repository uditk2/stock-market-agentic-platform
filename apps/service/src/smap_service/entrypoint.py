import os

from uvicorn import run
from smap_service.main import app


def main() -> None:
    raw_port = os.getenv("SMAP_SERVICE_PORT", "18787")
    try:
        port = int(raw_port)
    except ValueError:
        port = 18787
    run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
