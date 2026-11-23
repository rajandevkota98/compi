"""Node registry: each node type is one async function registered with @node."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from compi.domain.sockets import Socket

Outputs = Mapping[str, Any]
NodeFn = Callable[[Mapping[str, Any], Any], Awaitable[Outputs]]


class NoParams(BaseModel):
    pass


@dataclass(frozen=True)
class NodeDef:
    name: str  # the node type, e.g. "prompt.concat"
    category: str
    inputs: Mapping[str, Socket]
    outputs: Mapping[str, Socket]
    optional: frozenset[str]
    whole: frozenset[str]  # inputs that take Items as one list instead of once per item
    params_model: type[BaseModel]
    version: int
    fn: NodeFn


_REGISTRY: dict[str, NodeDef] = {}


def node(
    type_: str,
    *,
    category: str,
    outputs: Mapping[str, Socket],
    inputs: Mapping[str, Socket] | None = None,
    optional: tuple[str, ...] = (),
    whole: tuple[str, ...] = (),
    params: type[BaseModel] = NoParams,
    version: int = 1,
) -> Callable[[NodeFn], NodeFn]:
    """Register a node type. Bump `version` when its behaviour changes (invalidates cache)."""

    def register(fn: NodeFn) -> NodeFn:
        if type_ in _REGISTRY:
            raise ValueError(f"node type already registered: {type_}")
        _REGISTRY[type_] = NodeDef(
            type_,
            category,
            dict(inputs or {}),
            dict(outputs),
            frozenset(optional),
            frozenset(whole),
            params,
            version,
            fn,
        )
        return fn

    return register


def find(type_: str) -> NodeDef | None:
    return _REGISTRY.get(type_)


def get(type_: str) -> NodeDef:
    found = find(type_)
    if found is None:
        raise KeyError(f"unknown node type: {type_}")
    return found


def schema(type_: str) -> dict[str, Any]:
    """What the canvas needs to draw a node: sockets and a params form."""
    d = get(type_)
    return {
        "type": d.name,
        "category": d.category,
        "version": d.version,
        "inputs": {
            k: {"socket": s.value, "optional": k in d.optional} for k, s in d.inputs.items()
        },
        "outputs": {k: s.value for k, s in d.outputs.items()},
        "params": d.params_model.model_json_schema(),
    }


def all_types() -> list[str]:
    return sorted(_REGISTRY)
