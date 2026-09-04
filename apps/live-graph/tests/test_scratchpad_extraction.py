"""Regressions guarded here, all observed against a live model:

- ```py (and other tags) must be recognised. The original regex only accepted
  ```python, so a py-tagged function was invisible and a chart-only trailing
  block was extracted instead, costing a repair round and losing the chart.
- When a reply carries several blocks, the one defining the entrypoint wins,
  never simply the last one.
"""

from livegraph.scratchpad.thread import extract_code, strip_code_blocks

FUNCTION = "def run(ctx):\n    return {'rows': []}"


def test_extracts_from_python_fence():
    assert extract_code(f"Here you go:\n\n```python\n{FUNCTION}\n```\n") == FUNCTION


def test_extracts_from_py_fence():
    assert extract_code(f"```py\n{FUNCTION}\n```") == FUNCTION


def test_extracts_from_bare_fence():
    assert extract_code(f"```\n{FUNCTION}\n```") == FUNCTION


def test_prefers_the_block_defining_the_entrypoint():
    reply = (
        f"The strategy:\n\n```python\n{FUNCTION}\n```\n\n"
        "And to chart it:\n\n```python\nplt.bar(['a'], [1])\n```\n"
    )
    assert extract_code(reply) == FUNCTION


def test_prefers_the_last_entrypoint_block_on_a_revision():
    older = "def run(ctx):\n    return {'old': True}"
    reply = f"```python\n{older}\n```\nOn reflection:\n```python\n{FUNCTION}\n```"
    assert extract_code(reply) == FUNCTION


def test_falls_back_to_unfenced_code():
    assert extract_code(f"{FUNCTION}\n") == FUNCTION


def test_returns_empty_when_there_is_no_code():
    assert extract_code("I need more detail before I can write this.") == ""


def test_strip_code_blocks_leaves_the_prose():
    reply = f"Ranks peers.\n\n```python\n{FUNCTION}\n```\n\nAssumes peers exist."
    prose = strip_code_blocks(reply)
    assert "def run" not in prose
    assert "Ranks peers." in prose and "Assumes peers exist." in prose


def test_opening_turn_restates_the_contract_in_the_user_message():
    """Regression: CLIProxyAPI's Claude backends drop the system prompt.

    Measured directly against the live proxy: a system-only instruction is
    honoured by the GPT backend and ignored by Claude, which meant the strategy
    contract never reached Claude and charts were silently never drawn. The
    contract therefore has to ride in the first user turn.
    """
    import time

    from livegraph.scratchpad import MarketSnapshot
    from livegraph.scratchpad.thread import ScratchpadService

    snapshot = MarketSnapshot(
        taken_at=time.time(), prices={"INFY": {"ltp": 1500.0, "change_pct": -1.0}}
    )
    opening = ScratchpadService._opening_turn("rank the movers", snapshot)

    assert "def run(ctx)" in opening
    assert "matplotlib" in opening
    assert "ctx.prices" in opening
    assert "rank the movers" in opening
