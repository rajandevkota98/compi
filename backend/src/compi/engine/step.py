"""One graph step: map over items, call the node, check it, retry, or hold it for review."""

import asyncio
from collections.abc import Callable, Mapping
from typing import Annotated, Any, TypedDict

from langgraph.config import get_stream_writer

from compi.domain.sockets import Items
from compi.domain.spec import CheckSpec, NodeSpec
from compi.domain.verdict import Verdict
from compi.engine.cache import Cache
from compi.engine.registry import NodeDef, Outputs, get
from compi.services import costs

FEEDBACK = "feedback"  # extra input a node gets on retry: the checker's fix hints so far
Emit = Callable[..., None]


def merge[K, V](old: Mapping[K, V], new: Mapping[K, V]) -> dict[K, V]:
    return {**old, **new}


class RunState(TypedDict):
    outputs: Annotated[dict[str, Outputs], merge]  # node id -> that node's outputs
    held: Annotated[dict[str, str], merge]  # node id -> "flagged", "failed" or "blocked"


def feedback_note(inputs: Mapping[str, Any]) -> str:
    """Text a model node adds to its prompt on retry: the checker's fix hints so far."""
    hints: list[str] = inputs.get(FEEDBACK) or []
    return "\n\nA reviewer rejected the last attempt. Fix: " + "; ".join(hints) if hints else ""


def review_key(key: str) -> str:
    return f"{key}:review"


def _per_item(d: NodeDef, inputs: dict[str, Any]) -> list[dict[str, Any]] | None:
    """One input dict per item when Items arrive (except on `whole` inputs); None if none do."""
    mapped = {p: v for p, v in inputs.items() if isinstance(v, Items) and p not in d.whole}
    sizes = {len(v) for v in mapped.values()}
    if len(sizes) > 1:
        raise ValueError(f"iterated inputs differ in length: {sizes}")
    if not mapped:
        return None
    return [{**inputs, **{p: v[i] for p, v in mapped.items()}} for i in range(sizes.pop())]


async def _check(check: CheckSpec, outputs: Outputs, inputs: Mapping[str, Any]) -> Verdict:
    """Checkers get the node's outputs as "value" and what it was given as "inputs"."""
    d = get(check.type)
    params = d.params_model.model_validate(check.params)
    out = await d.fn({"value": outputs, "inputs": inputs}, params)
    return Verdict.model_validate(out["verdict"])


async def _attempt(n: NodeSpec, inputs: dict[str, Any], emit: Emit) -> tuple[Outputs, Verdict]:
    """Call the node; while its checker says retry, call again with the feedback."""
    d, feedback = get(n.type), list[str]()
    params = d.params_model.model_validate(n.params)
    while True:
        result = await d.fn({**inputs, FEEDBACK: feedback} if feedback else inputs, params)
        if missing := set(d.outputs) - set(result):
            raise RuntimeError(f"{n.id} ({n.type}) did not return outputs: {sorted(missing)}")
        if n.check is None:
            return result, Verdict(decision="pass")
        verdict = await _check(n.check, result, inputs)
        emit(kind="verdict", node=n.id, verdict=verdict.model_dump())
        if verdict.decision != "retry":
            return result, verdict
        if len(feedback) == n.check.max_retries:
            return result, verdict.model_copy(update={"decision": "flag"})
        feedback.append(verdict.fix_hint or "; ".join(verdict.reasons))


def make_step(n: NodeSpec, ports: Mapping[str, tuple[str, str]], key: str, cache: Cache):
    d = get(n.type)

    async def step(state: RunState) -> dict[str, Any]:
        writer = get_stream_writer()

        def emit(**event: Any) -> None:
            writer(event)

        if waiting := sorted({s for s, _ in ports.values() if s in state["held"]}):
            emit(kind="blocked", node=n.id, waiting_on=waiting)
            return {"held": {n.id: "blocked"}}
        emit(kind="started", node=n.id)
        spent = costs.track()
        try:
            inputs = {port: state["outputs"][src][sp] for port, (src, sp) in ports.items()}
            batch = _per_item(d, inputs)
            calls = [inputs] if batch is None else batch
            tries = await asyncio.gather(*(_attempt(n, i, emit) for i in calls))
        except Exception as exc:  # a failing node holds its branch; other branches go on
            emit(kind="failed", node=n.id, error=f"{type(exc).__name__}: {exc}", cost=sum(spent))
            return {"held": {n.id: "failed"}}
        results = [r for r, _ in tries]
        result = (
            results[0] if batch is None else {k: Items(r[k] for r in results) for k in d.outputs}
        )
        verdicts = [v.model_dump() for _, v in tries if v.decision != "pass"]
        if verdicts:
            await cache.put(review_key(key), {"outputs": result, "verdicts": verdicts})
            emit(kind="flagged", node=n.id, verdicts=verdicts, outputs=result, cost=sum(spent))
            return {"held": {n.id: "flagged"}}
        await cache.put(key, result)
        emit(kind="done", node=n.id, outputs=result, cost=sum(spent))
        return {"outputs": {n.id: result}}

    return step
