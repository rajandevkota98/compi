"""Check a WorkflowSpec before running it, and order its nodes."""

from collections import Counter
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from compi.domain.sockets import compatible
from compi.domain.spec import EdgeSpec, WorkflowSpec, incoming
from compi.engine.registry import NodeDef, find


def topo_order(spec: WorkflowSpec) -> list[str]:
    """Node ids so every node comes after its inputs. Raises ValueError on a cycle."""
    wires = incoming(spec)
    waiting = {nid: {src for src, _ in ports.values()} for nid, ports in wires.items()}
    order: list[str] = []
    ready = [nid for nid, deps in waiting.items() if not deps]
    while ready:
        nid = ready.pop(0)
        order.append(nid)
        for other, deps in waiting.items():
            if nid in deps:
                deps.discard(nid)
                if not deps:
                    ready.append(other)
    if len(order) != len(waiting):
        raise ValueError("workflow has a cycle")
    return order


def _edge_errors(e: EdgeSpec, defs: dict[str, NodeDef]) -> list[str]:
    src, dst = defs.get(e.source), defs.get(e.target)
    if src is None or dst is None:
        return [f"edge {e.source}->{e.target}: unknown node"]
    out, inp = src.outputs.get(e.source_port), dst.inputs.get(e.target_port)
    if out is None:
        return [f"edge {e.source}->{e.target}: {e.source} has no output '{e.source_port}'"]
    if inp is None:
        return [f"edge {e.source}->{e.target}: {e.target} has no input '{e.target_port}'"]
    if not compatible(out, inp):
        return [f"edge {e.source}->{e.target}: cannot wire {out} into {inp}"]
    return []


def _type_errors(owner: str, type_: str, params: Mapping[str, Any]) -> list[str]:
    d = find(type_)
    if d is None:
        return [f"{owner}: unknown node type '{type_}'"]
    try:
        d.params_model.model_validate(params)
    except ValidationError as exc:
        return [f"{owner}: bad params: {exc.errors()[0]['msg']}"]
    return []


def validate(spec: WorkflowSpec) -> list[str]:
    """All problems found, as readable messages. Empty list means the spec can run."""
    ids = Counter(n.id for n in spec.nodes)
    errors = [f"duplicate node id: {i}" for i, count in ids.items() if count > 1]
    for n in spec.nodes:
        errors += _type_errors(n.id, n.type, n.params)
        if n.check:
            errors += _type_errors(f"{n.id} check", n.check.type, n.check.params)
    defs = {n.id: d for n in spec.nodes if (d := find(n.type))}

    wired = Counter((e.target, e.target_port) for e in spec.edges)
    errors += [f"{t}: input '{p}' is wired more than once" for (t, p), c in wired.items() if c > 1]
    for e in spec.edges:
        errors += _edge_errors(e, defs)
    for nid, d in defs.items():
        errors += [
            f"{nid}: required input '{p}' is not connected"
            for p in d.inputs
            if p not in d.optional and (nid, p) not in wired
        ]
    if not errors:
        try:
            topo_order(spec)
        except ValueError as exc:
            errors.append(str(exc))
    return errors
