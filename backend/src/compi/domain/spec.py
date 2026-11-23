"""WorkflowSpec: the JSON the canvas saves. Pure data plus small pure helpers."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

NODE_ID = r"^[A-Za-z0-9_-]+$"

# target node id -> {target port: (source node id, source port)}
Incoming = dict[str, dict[str, tuple[str, str]]]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CheckSpec(_Frozen):
    """A checker node type run on a node's outputs; retries with its feedback, then flags."""

    type: str
    params: dict[str, Any] = Field(default_factory=dict[str, Any])
    max_retries: int = Field(default=2, ge=0, le=5)


class NodeSpec(_Frozen):
    id: str = Field(pattern=NODE_ID)
    type: str
    params: dict[str, Any] = Field(default_factory=dict[str, Any])
    check: CheckSpec | None = None


class EdgeSpec(_Frozen):
    source: str
    source_port: str
    target: str
    target_port: str


class WorkflowSpec(_Frozen):
    id: str
    name: str
    version: int = 1
    nodes: tuple[NodeSpec, ...] = ()
    edges: tuple[EdgeSpec, ...] = ()


def node_map(spec: WorkflowSpec) -> dict[str, NodeSpec]:
    return {n.id: n for n in spec.nodes}


def incoming(spec: WorkflowSpec) -> Incoming:
    wires: Incoming = {n.id: {} for n in spec.nodes}
    for e in spec.edges:
        wires.setdefault(e.target, {})[e.target_port] = (e.source, e.source_port)
    return wires


def set_params(spec: WorkflowSpec, node_id: str, **params: Any) -> WorkflowSpec:
    """A copy of the spec with some params of one node changed."""
    nodes = tuple(
        n.model_copy(update={"params": {**n.params, **params}}) if n.id == node_id else n
        for n in spec.nodes
    )
    return spec.model_copy(update={"nodes": nodes})
