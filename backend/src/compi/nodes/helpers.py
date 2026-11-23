"""Helper nodes: plumbing between models."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from compi.domain.sockets import Items, Socket
from compi.engine.registry import Outputs, node

PARTS = ("part1", "part2", "part3", "part4")


class ConcatParams(BaseModel):
    separator: str = " "


@node(
    "prompt.concat",
    category="Helpers",
    inputs=dict.fromkeys(PARTS, Socket.TEXT),
    optional=PARTS[1:],
    outputs={"text": Socket.TEXT},
    params=ConcatParams,
)
async def prompt_concat(inputs: Mapping[str, Any], params: ConcatParams) -> Outputs:
    """Join the connected text pieces in port order, skipping empty ones."""
    pieces = [str(inputs[p]) for p in PARTS if inputs.get(p)]
    return {"text": params.separator.join(pieces)}


class ListParams(BaseModel):
    items: list[str] = []


@node("list.text", category="Helpers", outputs={"items": Socket.LIST}, params=ListParams)
async def text_list(inputs: Mapping[str, Any], params: ListParams) -> Outputs:
    return {"items": list(params.items)}


@node(
    "list.iterate", category="Helpers", inputs={"items": Socket.LIST}, outputs={"item": Socket.ANY}
)
async def iterate(inputs: Mapping[str, Any], params: BaseModel) -> Outputs:
    """Nodes after this run once per item, in parallel."""
    return {"item": Items(inputs["items"])}


@node(
    "list.collect",
    category="Helpers",
    inputs={"items": Socket.ANY},
    whole=("items",),
    outputs={"items": Socket.LIST},
)
async def collect(inputs: Mapping[str, Any], params: BaseModel) -> Outputs:
    """Gathers per-item results back into one list."""
    return {"items": list(inputs["items"])}


@node("router", category="Helpers", inputs={"in": Socket.ANY}, outputs={"out": Socket.ANY})
async def router(inputs: Mapping[str, Any], params: BaseModel) -> Outputs:
    """Pass-through, so one wire can fan out to many nodes from a tidy spot on the canvas."""
    return {"out": inputs["in"]}
