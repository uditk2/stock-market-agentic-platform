import os
from pathlib import Path

import pytest

from livegraph.graph import GraphRepository

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


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
