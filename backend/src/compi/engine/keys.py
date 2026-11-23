"""Merkle cache keys: a node's key covers its type, params and everything upstream."""

import hashlib
import json

from compi.domain.spec import WorkflowSpec, incoming, node_map
from compi.engine.registry import get
from compi.engine.validate import topo_order


def node_keys(spec: WorkflowSpec) -> dict[str, str]:
    """Key per node id. It changes when the node or anything before it changes."""
    nodes, wires = node_map(spec), incoming(spec)
    keys: dict[str, str] = {}
    for nid in topo_order(spec):
        n = nodes[nid]
        d = get(n.type)
        payload = {
            "type": n.type,
            "version": d.version,
            "params": d.params_model.model_validate(n.params).model_dump(mode="json"),
            "check": n.check.model_dump(mode="json") if n.check else None,
            "inputs": {port: [keys[src], sp] for port, (src, sp) in sorted(wires[nid].items())},
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        keys[nid] = hashlib.sha256(blob.encode()).hexdigest()
    return keys
