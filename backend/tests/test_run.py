import pytest
from conftest import CALLS, sample, wire

from compi.domain.spec import NodeSpec, WorkflowSpec, set_params
from compi.engine.cache import MemoryCache
from compi.engine.registry import schema
from compi.engine.run import InvalidSpec, run


async def test_run_all_then_nothing_reruns() -> None:
    cache = MemoryCache()
    first = await run(sample(), cache)
    assert first.ran == {"a", "b", "u1", "j", "u2"}
    assert first.outputs["u2"] == {"text": "X+Y"}
    assert len(CALLS) == 5

    second = await run(sample(), cache)
    assert second.ran == frozenset()
    assert second.outputs["u2"] == {"text": "X+Y"}
    assert len(CALLS) == 5


async def test_param_change_reruns_exactly_downstream() -> None:
    cache = MemoryCache()
    await run(sample(), cache)
    CALLS.clear()

    result = await run(set_params(sample(), "b", value="z"), cache)
    assert result.ran == {"b", "j", "u2"}
    assert sorted(CALLS) == ["join", "source", "upper"]
    assert result.outputs["u2"] == {"text": "X+Z"}


async def test_run_one_target_runs_only_its_uncached_ancestors() -> None:
    cache = MemoryCache()
    result = await run(sample(), cache, targets=["u1"])
    assert result.ran == {"a", "u1"}
    assert result.outputs == {"u1": {"text": "X"}}

    rest = await run(sample(), cache, targets=["u2"])
    assert rest.ran == {"b", "j", "u2"}


async def test_join_waits_for_both_inputs_and_runs_once() -> None:
    # s feeds j directly and through p, so j's inputs arrive in different steps.
    spec = WorkflowSpec(
        id="d",
        name="diamond",
        nodes=(
            NodeSpec(id="s", type="test.source", params={"value": "d"}),
            NodeSpec(id="p", type="test.upper"),
            NodeSpec(id="j", type="test.join"),
        ),
        edges=(wire("s", "p"), wire("p", "j", "a"), wire("s", "j", "b")),
    )
    result = await run(spec, MemoryCache())
    assert result.outputs["j"] == {"text": "D+d"}
    assert CALLS.count("join") == 1


async def test_prompt_concat_joins_connected_parts() -> None:
    spec = WorkflowSpec(
        id="c",
        name="concat",
        nodes=(
            NodeSpec(id="subject", type="text.input", params={"text": "red sneaker"}),
            NodeSpec(id="style", type="text.input", params={"text": "studio light"}),
            NodeSpec(id="prompt", type="prompt.concat", params={"separator": ", "}),
        ),
        edges=(wire("subject", "prompt", "part1"), wire("style", "prompt", "part3")),
    )
    result = await run(spec, MemoryCache(), targets=["prompt"])
    assert result.outputs["prompt"] == {"text": "red sneaker, studio light"}


async def test_invalid_spec_and_unknown_target_raise() -> None:
    with pytest.raises(InvalidSpec, match="unknown target node: nope"):
        await run(sample(), MemoryCache(), targets=["nope"])


def test_schema_describes_sockets_and_params() -> None:
    s = schema("prompt.concat")
    assert s["inputs"]["part1"] == {"socket": "text", "optional": False}
    assert s["inputs"]["part2"]["optional"] is True
    assert s["outputs"] == {"text": "text"}
    assert s["params"]["properties"]["separator"]["default"] == " "
