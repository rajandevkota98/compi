"""Human review of flagged nodes. Approving caches the output, so the next run continues."""

from typing import cast

from compi.domain.spec import WorkflowSpec
from compi.engine.cache import Cache
from compi.engine.keys import node_keys
from compi.engine.registry import Outputs
from compi.engine.step import review_key
from compi.engine.validate import validate


async def pending(spec: WorkflowSpec, cache: Cache, node_id: str) -> Outputs | None:
    """The flagged output and the checker's verdicts, if this node waits for review."""
    return await cache.get(review_key(node_keys(spec)[node_id]))


async def approve(
    spec: WorkflowSpec, cache: Cache, node_id: str, outputs: Outputs | None = None
) -> None:
    """Accept the flagged output as is, or replace it with a fixed one."""
    if outputs is None:
        flagged = await pending(spec, cache, node_id)
        if flagged is None:
            raise KeyError(f"{node_id} has nothing waiting for review")
        outputs = cast(Outputs, flagged["outputs"])
    await cache.put(node_keys(spec)[node_id], outputs)


async def node_states(spec: WorkflowSpec, cache: Cache) -> dict[str, dict[str, object]]:
    """What the canvas shows on load: each node's cached outputs or its waiting review."""
    if validate(spec):
        return {}
    states: dict[str, dict[str, object]] = {}
    for nid, key in node_keys(spec).items():
        if (outputs := await cache.get(key)) is not None:
            states[nid] = {"status": "done", "outputs": outputs}
        elif (flagged := await cache.get(review_key(key))) is not None:
            states[nid] = {"status": "flagged", **flagged}
    return states
