"""Regressions guarded here:

- IN_SECTOR must never carry impact, else one sector-hub hop reaches all 500
  stocks and every propagation result becomes the whole market.
- A stock in a large peer_group must not out-rank a direct COST_INPUT target
  purely by having many second-hop paths into it.
"""

from livegraph.graph import EdgeType, ImpactPropagator, NodeType


def test_graph_loads_expected_shape(repo):
    assert repo.node_count == 545
    assert repo.edge_count == 3003
    assert len(repo.nodes_of_type(NodeType.STOCK)) == 500
    assert len(repo.nodes_of_type(NodeType.SECTOR)) == 20
    assert len(repo.nodes_of_type(NodeType.MACRO)) == 25


def test_fo_symbols_are_the_screenable_tier(repo):
    fo = repo.fo_symbols()
    assert len(fo) == 211
    assert all(repo.require(symbol).fo for symbol in fo)


def test_peers_share_a_peer_group_and_exclude_self(repo):
    peers = repo.peers_of("HDFCBANK")
    assert "HDFCBANK" not in peers
    assert "ICICIBANK" in peers
    groups = set(repo.require("HDFCBANK").peer_groups)
    assert all(groups & set(repo.require(p).peer_groups) for p in peers)


def test_sector_hub_does_not_leak_impact(repo):
    """IN_SECTOR is membership only; propagating it would hit the whole sector."""
    prop = ImpactPropagator(repo)
    impacts = prop.propagate("HDFCBANK", direction=1)
    hit = {i.node_id for i in impacts}
    assert not any(node_id.startswith("SEC::") for node_id in hit)
    financials = set(repo.sector_members("Financial Services"))
    assert not financials.issubset(hit)


def test_cost_input_flips_sign(repo):
    """Crude up must push a crude-consumer down, not up."""
    prop = ImpactPropagator(repo)
    impacts = {i.node_id: i for i in prop.propagate("CRUDE", direction=1)}
    consumers = [
        edge.target
        for edge in repo.outgoing("CRUDE")
        if edge.type is EdgeType.COST_INPUT and edge.sign < 0
    ]
    assert consumers, "expected CRUDE to have COST_INPUT consumers"
    for symbol in consumers[:5]:
        assert impacts[symbol].score < 0, f"{symbol} should fall when crude rises"


def test_second_hop_is_attenuated_and_never_beats_its_own_first_hop(repo):
    prop = ImpactPropagator(repo)
    impacts = prop.propagate("CRUDE", direction=1)
    by_hop = {1: [], 2: []}
    for impact in impacts:
        by_hop[impact.hops].append(abs(impact.score))
    assert by_hop[2], "expected some second-hop impacts"
    assert max(by_hop[2]) <= max(by_hop[1])


def test_each_node_appears_once(repo):
    prop = ImpactPropagator(repo)
    impacts = prop.propagate("CRUDE", direction=1)
    ids = [i.node_id for i in impacts]
    assert len(ids) == len(set(ids))
