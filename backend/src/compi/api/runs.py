"""Runs in the background; every event is kept so a viewer can join late and replay."""

import asyncio
import dataclasses
import json
import uuid
from collections.abc import AsyncIterator, Iterable
from typing import Any

from compi.domain.spec import WorkflowSpec
from compi.engine.cache import Cache
from compi.engine.run import Event, stream


@dataclasses.dataclass
class Run:
    events: list[str] = dataclasses.field(default_factory=list[str])
    done: bool = False
    changed: asyncio.Condition = dataclasses.field(default_factory=asyncio.Condition)


RUNS: dict[str, Run] = {}
_tasks: set[asyncio.Task[None]] = set()


def _default(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    if isinstance(value, (set, frozenset)):
        return sorted(value)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
    raise TypeError(f"cannot send {type(value).__name__}")


async def _add(run: Run, event: Event, done: bool = False) -> None:
    async with run.changed:
        run.events.append(json.dumps(event, default=_default))
        run.done = done
        run.changed.notify_all()


async def _drive(run: Run, spec: WorkflowSpec, cache: Cache, targets: Iterable[str] | None) -> None:
    try:
        async for event in stream(spec, cache, targets):
            await _add(run, event, done=event["kind"] == "finished")
    except Exception as exc:
        await _add(run, {"kind": "error", "error": f"{type(exc).__name__}: {exc}"}, done=True)


def start(spec: WorkflowSpec, cache: Cache, targets: Iterable[str] | None) -> str:
    run_id, run = uuid.uuid4().hex[:12], Run()
    RUNS[run_id] = run
    task = asyncio.create_task(_drive(run, spec, cache, targets))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return run_id


async def sse(run: Run) -> AsyncIterator[str]:
    """Server-sent events: everything so far, then live until the run ends."""
    sent = 0
    while True:
        async with run.changed:
            await run.changed.wait_for(lambda seen=sent: len(run.events) > seen or run.done)
            new, done = run.events[sent:], run.done
        sent += len(new)
        for event in new:
            yield f"data: {event}\n\n"
        if done and sent == len(run.events):
            return
