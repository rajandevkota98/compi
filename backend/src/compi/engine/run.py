"""Run a workflow: validate → keys → plan → compile → stream events."""

from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from typing import Any, cast

from compi.domain.spec import WorkflowSpec, incoming, node_map
from compi.engine.cache import Cache
from compi.engine.compile import compile_plan
from compi.engine.keys import node_keys
from compi.engine.plan import boundary, plan
from compi.engine.registry import Outputs
from compi.engine.step import RunState
from compi.engine.validate import validate

Event = dict[str, Any]  # {"kind": started|verdict|done|flagged|failed|blocked|finished, ...}


class InvalidSpec(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class RunResult:
    outputs: dict[str, Outputs]  # outputs of each target node that finished
    ran: frozenset[str]  # node ids that executed (the rest came from cache or were blocked)
    held: dict[str, str]  # node id -> "flagged" (needs review), "failed" or "blocked"


async def _cached(cache: Cache, key: str, nid: str) -> Outputs:
    found = await cache.get(key)
    if found is None:
        raise RuntimeError(f"cache lost the output of {nid}")
    return found


async def stream(
    spec: WorkflowSpec, cache: Cache, targets: Iterable[str] | None = None
) -> AsyncIterator[Event]:
    """Run the target nodes (default: all), yielding live events; the last one is "finished"."""
    errors, nodes = validate(spec), node_map(spec)
    wanted = list(targets) if targets is not None else list(nodes)
    errors += [f"unknown target node: {t}" for t in wanted if t not in nodes]
    if errors:
        raise InvalidSpec(errors)

    keys, wires = node_keys(spec), incoming(spec)
    to_run = await plan(wires, keys, cache, wanted)
    seed = {s: await _cached(cache, keys[s], s) for s in boundary(wires, to_run)}
    state: RunState = {"outputs": seed, "held": {}}
    if to_run:
        graph = compile_plan(nodes, wires, keys, cache, to_run)
        parts = graph.astream(state, stream_mode=["custom", "values"])  # pyright: ignore
        async for mode, chunk in cast(AsyncIterator[tuple[str, Any]], parts):
            if mode == "custom":
                yield chunk
            else:
                state = chunk
    held = state["held"]
    outputs = {
        t: state["outputs"][t] if t in state["outputs"] else await _cached(cache, keys[t], t)
        for t in wanted
        if t not in held
    }
    ran = frozenset(n for n in to_run if held.get(n) != "blocked")
    yield {"kind": "finished", "result": RunResult(outputs, ran, held)}


async def run(spec: WorkflowSpec, cache: Cache, targets: Iterable[str] | None = None) -> RunResult:
    """Like stream(), but only returns the final result."""
    result = None
    async for event in stream(spec, cache, targets):
        result = event.get("result")
    assert isinstance(result, RunResult)
    return result
