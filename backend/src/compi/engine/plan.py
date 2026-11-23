"""Decide which nodes must run: the targets and their uncached ancestors."""

from collections.abc import Iterable

from compi.domain.spec import Incoming
from compi.engine.cache import Cache


async def plan(
    wires: Incoming, keys: dict[str, str], cache: Cache, targets: Iterable[str]
) -> set[str]:
    """Walk back from the targets; stop at any node whose output is cached."""
    todo, seen, to_run = list(targets), set[str](), set[str]()
    while todo:
        nid = todo.pop()
        if nid in seen:
            continue
        seen.add(nid)
        if await cache.get(keys[nid]) is not None:
            continue
        to_run.add(nid)
        todo.extend(src for src, _ in wires[nid].values())
    return to_run


def boundary(wires: Incoming, to_run: set[str]) -> set[str]:
    """Cached nodes whose outputs feed the nodes that will run."""
    return {src for nid in to_run for src, _ in wires[nid].values() if src not in to_run}
