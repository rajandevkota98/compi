# Compi backend

Node-based AI image/video workflow engine on LangGraph.

```
uv sync
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest   # the gate
```

Layers: `domain` (pure types) ← `engine` (validate, keys, plan, compile, run) ← `nodes` (node types).
A node type is one async function registered with `@node(...)` in `compi/nodes/`.
