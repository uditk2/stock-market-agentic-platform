from pathlib import Path

import pytest

from livegraph.graph import GraphRepository

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


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
