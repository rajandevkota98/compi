from conftest import CALLS, wire

from compi.domain.spec import CheckSpec, NodeSpec, WorkflowSpec
from compi.engine.cache import MemoryCache
from compi.engine.review import approve, pending
from compi.engine.run import run, stream


def spec_with(check: CheckSpec) -> WorkflowSpec:
    """src → flaky(checked) → after;  other runs on its own branch."""
    return WorkflowSpec(
        id="c",
        name="checks",
        nodes=(
            NodeSpec(id="src", type="test.source", params={"value": "shoe"}),
            NodeSpec(id="flaky", type="test.flaky", check=check),
            NodeSpec(id="after", type="test.upper"),
            NodeSpec(id="other", type="test.source", params={"value": "o"}),
        ),
        edges=(wire("src", "flaky"), wire("flaky", "after")),
    )


async def test_checker_retry_with_feedback_fixes_the_output() -> None:
    spec = spec_with(CheckSpec(type="check.text", params={"must_include": ["good"]}))
    events = [e async for e in stream(spec, MemoryCache())]
    result = events[-1]["result"]
    assert result.outputs["after"] == {"text": "GOOD SHOE"}
    assert CALLS.count("flaky") == 2
    decisions = [e["verdict"]["decision"] for e in events if e["kind"] == "verdict"]
    assert decisions == ["retry", "pass"]
    assert {e["node"] for e in events if e["kind"] == "done"} == {"src", "flaky", "after", "other"}


async def test_flagged_node_holds_its_branch_until_approved() -> None:
    cache = MemoryCache()
    spec = spec_with(
        CheckSpec(type="check.text", params={"must_include": ["never"]}, max_retries=1)
    )

    first = await run(spec, cache)
    assert first.held == {"flaky": "flagged", "after": "blocked"}
    assert "other" in first.outputs  # the independent branch still finished
    assert CALLS.count("flaky") == 2  # first try + one retry
    review = await pending(spec, cache, "flaky")
    assert review is not None
    assert review["verdicts"][0]["reasons"] == ["must include 'never'"]

    await approve(spec, cache, "flaky", {"text": "fixed by hand"})
    second = await run(spec, cache)
    assert second.ran == {"after"}
    assert second.outputs["after"] == {"text": "FIXED BY HAND"}
