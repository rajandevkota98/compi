from conftest import sample

from compi.domain.spec import NodeSpec, WorkflowSpec, set_params
from compi.engine.keys import node_keys


def test_changing_a_param_changes_only_that_node_and_downstream() -> None:
    before = node_keys(sample())
    after = node_keys(set_params(sample(), "b", value="changed"))
    changed = {nid for nid in before if before[nid] != after[nid]}
    assert changed == {"b", "j", "u2"}


def test_default_params_give_the_same_key() -> None:
    def one(params: dict[str, str]) -> str:
        node = NodeSpec(id="c", type="text.input", params=params)
        spec = WorkflowSpec(id="t", name="t", nodes=(node,))
        return node_keys(spec)["c"]

    assert one({}) == one({"text": ""})
    assert one({}) != one({"text": "hi"})
