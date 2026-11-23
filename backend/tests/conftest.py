"""Test-only nodes that record every call, plus a small sample workflow.

a(source "x") ─► u1(upper) ─► j.a
b(source "y") ──────────────► j.b      j(join "+") ─► u2(upper)
"""

import os
import tempfile
from collections.abc import Mapping
from typing import Any

os.environ["COMPI_DATA"] = tempfile.mkdtemp(prefix="compi-test-")  # before compi is imported

import pytest
from pydantic import BaseModel

import compi.nodes  # noqa: F401  # pyright: ignore[reportUnusedImport]  (registers built-ins)
from compi.domain.sockets import Socket
from compi.domain.spec import EdgeSpec, NodeSpec, WorkflowSpec
from compi.engine.registry import Outputs, node

CALLS: list[str] = []  # node type of every call, in order


class SourceParams(BaseModel):
    value: str = ""


@node("test.source", category="Test", outputs={"text": Socket.TEXT}, params=SourceParams)
async def source(inputs: Mapping[str, Any], params: SourceParams) -> Outputs:
    CALLS.append("source")
    return {"text": params.value}


@node("test.upper", category="Test", inputs={"text": Socket.TEXT}, outputs={"text": Socket.TEXT})
async def upper(inputs: Mapping[str, Any], params: BaseModel) -> Outputs:
    CALLS.append("upper")
    return {"text": str(inputs["text"]).upper()}


@node(
    "test.join",
    category="Test",
    inputs={"a": Socket.TEXT, "b": Socket.TEXT},
    outputs={"text": Socket.TEXT},
)
async def join(inputs: Mapping[str, Any], params: BaseModel) -> Outputs:
    CALLS.append("join")
    return {"text": f"{inputs['a']}+{inputs['b']}"}


@node("test.flaky", category="Test", inputs={"text": Socket.TEXT}, outputs={"text": Socket.TEXT})
async def flaky(inputs: Mapping[str, Any], params: BaseModel) -> Outputs:
    """Bad output until it gets checker feedback, like a model that improves when told how."""
    CALLS.append("flaky")
    return {"text": "good " + inputs["text"] if inputs.get("feedback") else "bad"}


def wire(
    source: str, target: str, target_port: str = "text", source_port: str = "text"
) -> EdgeSpec:
    return EdgeSpec(source=source, source_port=source_port, target=target, target_port=target_port)


def sample() -> WorkflowSpec:
    return WorkflowSpec(
        id="wf",
        name="sample",
        nodes=(
            NodeSpec(id="a", type="test.source", params={"value": "x"}),
            NodeSpec(id="b", type="test.source", params={"value": "y"}),
            NodeSpec(id="u1", type="test.upper"),
            NodeSpec(id="j", type="test.join"),
            NodeSpec(id="u2", type="test.upper"),
        ),
        edges=(wire("a", "u1"), wire("u1", "j", "a"), wire("b", "j", "b"), wire("j", "u2")),
    )


@pytest.fixture(autouse=True)
def reset_calls() -> None:
    CALLS.clear()
