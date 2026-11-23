from conftest import sample, wire

from compi.domain.spec import NodeSpec, WorkflowSpec
from compi.engine.validate import topo_order, validate


def spec_of(*nodes: NodeSpec, edges: tuple[object, ...] = ()) -> WorkflowSpec:
    return WorkflowSpec.model_validate({"id": "t", "name": "t", "nodes": nodes, "edges": edges})


def test_sample_is_valid_and_ordered() -> None:
    spec = sample()
    assert validate(spec) == []
    order = topo_order(spec)
    assert order.index("a") < order.index("u1") < order.index("j") < order.index("u2")


def test_rejects_cycle() -> None:
    spec = spec_of(
        NodeSpec(id="p", type="test.upper"),
        NodeSpec(id="q", type="test.upper"),
        edges=(wire("p", "q"), wire("q", "p")),
    )
    assert validate(spec) == ["workflow has a cycle"]


def test_rejects_socket_mismatch() -> None:
    spec = spec_of(
        NodeSpec(id="n", type="number.input"),
        NodeSpec(id="u", type="test.upper"),
        edges=(wire("n", "u", source_port="value"),),
    )
    assert validate(spec) == ["edge n->u: cannot wire number into text"]


def test_rejects_unknown_port_and_missing_input() -> None:
    spec = spec_of(
        NodeSpec(id="a", type="test.source"),
        NodeSpec(id="u", type="test.upper"),
        edges=(wire("a", "u", target_port="nope"),),
    )
    assert validate(spec) == [
        "edge a->u: u has no input 'nope'",
        "u: required input 'text' is not connected",
    ]


def test_rejects_bad_params_and_unknown_type() -> None:
    spec = spec_of(
        NodeSpec(id="n", type="number.input", params={"value": "abc"}),
        NodeSpec(id="z", type="does.not.exist"),
    )
    errors = validate(spec)
    assert errors[0].startswith("n: bad params:")
    assert errors[1] == "z: unknown node type 'does.not.exist'"


def test_rejects_input_wired_twice() -> None:
    spec = spec_of(
        NodeSpec(id="a", type="test.source"),
        NodeSpec(id="b", type="test.source"),
        NodeSpec(id="u", type="test.upper"),
        edges=(wire("a", "u"), wire("b", "u")),
    )
    assert validate(spec) == ["u: input 'text' is wired more than once"]
