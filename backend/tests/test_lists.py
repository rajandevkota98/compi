from conftest import CALLS, wire

from compi.domain.spec import NodeSpec, WorkflowSpec
from compi.engine.cache import MemoryCache
from compi.engine.run import run


def spec_for(items: list[str]) -> WorkflowSpec:
    """list → iterate → router → upper → collect"""
    return WorkflowSpec(
        id="l",
        name="lists",
        nodes=(
            NodeSpec(id="list", type="list.text", params={"items": items}),
            NodeSpec(id="it", type="list.iterate"),
            NodeSpec(id="route", type="router"),
            NodeSpec(id="up", type="test.upper"),
            NodeSpec(id="done", type="list.collect"),
        ),
        edges=(
            wire("list", "it", "items", "items"),
            wire("it", "route", "in", "item"),
            wire("route", "up", "text", "out"),
            wire("up", "done", "items"),
        ),
    )


async def test_iterator_runs_downstream_once_per_item_then_collects() -> None:
    result = await run(spec_for(["a", "b", "c"]), MemoryCache())
    assert result.outputs["done"] == {"items": ["A", "B", "C"]}
    assert CALLS.count("upper") == 3


async def test_empty_list_runs_nothing_per_item() -> None:
    result = await run(spec_for([]), MemoryCache())
    assert result.outputs["done"] == {"items": []}
    assert CALLS.count("upper") == 0
