"""Turn the nodes that must run into a LangGraph StateGraph."""

from collections.abc import Mapping

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from compi.domain.spec import Incoming, NodeSpec
from compi.engine.cache import Cache
from compi.engine.step import RunState, make_step


def graph_name(node_id: str) -> str:
    """LangGraph node name; prefixed so it can never clash with a state key."""
    return f"node_{node_id}"


def compile_plan(
    nodes: Mapping[str, NodeSpec],
    wires: Incoming,
    keys: dict[str, str],
    cache: Cache,
    to_run: set[str],
) -> CompiledStateGraph[RunState, None, RunState, RunState]:
    g = StateGraph(RunState)
    for nid in sorted(to_run):
        step = make_step(nodes[nid], wires[nid], keys[nid], cache)
        g.add_node(graph_name(nid), step)  # pyright: ignore[reportUnknownMemberType]

    feeds_run = set[str]()
    for nid in sorted(to_run):
        srcs = sorted({graph_name(s) for s, _ in wires[nid].values() if s in to_run})
        feeds_run.update(s for s, _ in wires[nid].values() if s in to_run)
        if not srcs:
            g.add_edge(START, graph_name(nid))
        elif len(srcs) == 1:
            g.add_edge(srcs[0], graph_name(nid))
        else:
            g.add_edge(srcs, graph_name(nid))  # waits for all of them
    for nid in sorted(to_run - feeds_run):
        g.add_edge(graph_name(nid), END)
    return g.compile()  # pyright: ignore[reportUnknownMemberType]
