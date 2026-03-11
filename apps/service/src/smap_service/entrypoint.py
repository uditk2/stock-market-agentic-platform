from uvicorn import run


def main() -> None:
    run("smap_service.main:app", host="127.0.0.1", port=8787)


if __name__ == "__main__":
    main()
