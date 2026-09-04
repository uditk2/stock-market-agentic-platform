"""Regressions guarded here:

The repair loop is what makes the scratchpad usable: the model rarely gets a
strategy right against unfamiliar data on the first try, and it can only fix
what it is told. These pin the feedback path with a scripted model, so a
runtime change cannot quietly sever it.

- The sandbox failure must be fed back as the next user turn, carrying the
  traceback, and the corrected strategy must be the one that is kept.
- The traceback handed to the model must name the strategy's own frames and
  not the sandbox runner's, or the model tries to fix code it never wrote.
- A timeout must produce different guidance from a crash; telling a model that
  looped forever to "fix the exception" gets the same loop back.
"""

import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from livegraph.scratchpad import MarketSnapshot, PyodideSandbox, RunStatus, StrategyRun
from livegraph.scratchpad.thread import ScratchpadService, ScratchpadThread, _repair_prompt

BROKEN = "def run(ctx):\n    return {'x': ctx.prices['MISSING']['ltp']}\n"
FIXED = "def run(ctx):\n    return {'rows': [{'symbol': s} for s in ctx.prices]}\n"


@pytest.fixture
def snapshot():
    return MarketSnapshot(
        taken_at=1725441000.0,
        prices={"INFY": {"ltp": 1500.0, "change_pct": -1.0, "segment": "nse_fo"}},
        peers={"INFY": ["TCS"]},
        sectors={"INFY": "Information Technology"},
        fo_symbols=["INFY"],
    )


def scripted_model(replies: list[str]) -> FunctionModel:
    """Returns the given code one reply per call, recording each prompt it saw.

    Indexed by call count, not by message parts: a single call carries several
    parts, so counting parts silently skips replies.
    """
    sent: list[str] = []

    def respond(messages, info: AgentInfo) -> ModelResponse:
        prompt = "\n".join(
            content
            for part in getattr(messages[-1], "parts", [])
            if isinstance(content := getattr(part, "content", None), str)
        )
        sent.append(prompt)
        code = replies[min(len(sent) - 1, len(replies) - 1)]
        return ModelResponse(
            parts=[TextPart(content=f'{{"code": {code!r}, "explanation": "scripted"}}')]
        )

    model = FunctionModel(respond)
    model.sent = sent  # type: ignore[attr-defined]
    return model


# ---- repair prompt shape --------------------------------------------


def test_crash_feedback_carries_the_traceback():
    run = StrategyRun(
        status=RunStatus.ERROR,
        error="KeyError: 'MISSING'",
        traceback='Traceback:\n  File "<strategy>", line 2, in run\nKeyError: \'MISSING\'',
    )
    prompt = _repair_prompt(run)
    assert "<strategy>" in prompt
    assert "KeyError" in prompt
    assert "guard every lookup" in prompt


def test_timeout_feedback_is_not_crash_feedback():
    timed_out = _repair_prompt(StrategyRun(status=RunStatus.TIMEOUT, error="exceeded 30s"))
    assert "timeout" in timed_out.lower()
    assert "unbounded loops" in timed_out


def test_rejection_feedback_names_the_rejection():
    rejected = _repair_prompt(
        StrategyRun(status=RunStatus.REJECTED, error="no top-level `def run(ctx)` found")
    )
    assert "rejected before it ran" in rejected
    assert "def run(ctx)" in rejected


# ---- the loop, against the real sandbox -----------------------------


@pytest.fixture(scope="module")
def sandbox():
    box = PyodideSandbox(timeout_seconds=45)
    if not box.is_available():
        pytest.skip(f"sandbox unavailable: {box.unavailable_reason()}")
    box.start()
    yield box
    box.stop()


@pytest.mark.sandbox
@pytest.mark.asyncio
async def test_failure_is_fed_back_and_the_fix_is_kept(sandbox, snapshot):
    model = scripted_model([BROKEN, FIXED])
    service = ScratchpadService(sandbox=sandbox, model=model)
    thread = ScratchpadThread()

    turn = await service.send(thread, "rank the symbols", snapshot)

    assert turn.repairs == 1, "the broken strategy should have triggered exactly one repair"
    assert turn.run.ok, turn.run.error
    #: The second thing the model was told must be the sandbox's own failure.
    assert "KeyError" in model.sent[1]
    assert "<strategy>" in model.sent[1]
    #: Only the working strategy is retained for re-runs.
    assert thread.latest_code == FIXED.strip()


@pytest.mark.sandbox
@pytest.mark.asyncio
async def test_feedback_hides_the_sandbox_runner_frames(sandbox, snapshot):
    """The model must not be shown frames from code it did not write."""
    model = scripted_model([BROKEN, FIXED])
    service = ScratchpadService(sandbox=sandbox, model=model)

    await service.send(ScratchpadThread(), "rank the symbols", snapshot)

    feedback = model.sent[1]
    assert "<exec>" not in feedback
    assert "_run" not in feedback


@pytest.mark.sandbox
@pytest.mark.asyncio
async def test_repairs_are_bounded(sandbox, snapshot):
    """A model that never fixes its code must not loop forever."""
    model = scripted_model([BROKEN])
    service = ScratchpadService(sandbox=sandbox, model=model)
    thread = ScratchpadThread()

    turn = await service.send(thread, "rank the symbols", snapshot)

    assert turn.repairs == 2
    assert not turn.run.ok
    assert thread.latest_code == "", "a failing strategy must never be stored"
