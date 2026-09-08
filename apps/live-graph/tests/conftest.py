import os
from pathlib import Path

import pytest

from livegraph.graph import GraphRepository

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="session", autouse=True)
def no_ambient_kotak_credentials():
    """Blank the Kotak fields for the whole run, whatever `.env` holds.

    pydantic-settings reads `.env` off disk, so once a developer configures the
    app for real the tests asserting "nothing is configured" start failing on
    their machine and nowhere else — and worse, a test that reaches a login
    path would use live credentials. Environment variables take precedence over
    the file, and an empty one is still a value, so setting them empty here
    detaches the suite from whatever is on disk. Tests that want a value set
    one with monkeypatch, which wins over this.
    """
    from livegraph.feed.config import KotakSettings

    saved = {}
    for field in KotakSettings.REQUIRED:
        name = f"KOTAK_{field.upper()}"
        saved[name] = os.environ.get(name)
        os.environ[name] = ""
    yield
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


@pytest.fixture(scope="session", autouse=True)
def isolated_state_dir(tmp_path_factory):
    """Point the credential store at a throwaway directory for the whole run.

    Without this the suite reads and writes the developer's own store, so a
    test asserting "no credentials configured" would pass or fail depending on
    whose machine it ran on, and a test that writes one would leave it behind.
    """
    os.environ["LIVEGRAPH_STATE_DIR"] = str(tmp_path_factory.mktemp("state"))
    yield
    os.environ.pop("LIVEGRAPH_STATE_DIR", None)


@pytest.fixture(scope="session")
def repo() -> GraphRepository:
    return GraphRepository.from_file(DATA_DIR / "stock_graph.json")


@pytest.fixture(scope="session")
def resolver(repo) -> "EntityResolver":
    from livegraph.graph import NodeType
    from livegraph.news import EntityResolver

    stock_names = {
        n.id: n.name for n in repo.nodes_of_type(NodeType.STOCK)
    }
    known = frozenset(n.id for n in repo.nodes_of_type(NodeType.STOCK)) | frozenset(
        n.id for n in repo.nodes_of_type(NodeType.MACRO)
    )
    return EntityResolver.from_file(DATA_DIR / "aliases.json", stock_names, known)
