import {
  Background, BackgroundVariant, Controls, ReactFlow, useEdgesState, useNodesState, useReactFlow,
  type Connection, type Edge,
} from "@xyflow/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  api, type CheckSpec, type Json, type NodeSchema, type NodeState, type Outputs, type RunEvent, type WorkflowInfo,
} from "./api";
import { AppMode } from "./AppMode";
import {
  compatible, defaults, edgeColor, newId, toCanvas, toWorkflow, wire, type Card, type CardData,
} from "./graph";
import { Gallery } from "./Gallery";
import { useHistory } from "./history";
import { Inspector } from "./Inspector";
import { Ledger } from "./Ledger";
import { NodeCard } from "./NodeCard";
import { Palette } from "./Palette";
import { StudioContext, type Studio } from "./studio";

const nodeTypes = { card: NodeCard };

export default function App() {
  const flow = useReactFlow<Card, Edge>();
  const [schemas, setSchemas] = useState<NodeSchema[]>([]);
  const [list, setList] = useState<WorkflowInfo[]>([]);
  const [meta, setMeta] = useState({ id: "", name: "" });
  const [nodes, setNodes, onNodesChange] = useNodesState<Card>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [mode, setMode] = useState<"loom" | "app" | "gallery">("loom");
  const [confirmReset, setConfirmReset] = useState(false);
  const [running, setRunning] = useState(0);
  const [errors, setErrors] = useState<string[]>([]);
  const byType = useMemo(() => new Map(schemas.map((s) => [s.type, s])), [schemas]);

  // Latest canvas, for callbacks that outlive a render.
  const live = useRef({ meta, nodes, edges, running });
  live.current = { meta, nodes, edges, running };
  const workflow = () => toWorkflow(live.current.meta, live.current.nodes, live.current.edges);

  const patch = (id: string, change: Partial<CardData>) =>
    setNodes((ns) => ns.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...change } } : n)));

  /** Show what the cache holds for the current spec: anything edited upstream turns idle. */
  const applyState = (state: Record<string, NodeState>) =>
    setNodes((ns) => ns.map((n) => {
      const s = state[n.id];
      const data: CardData = s
        ? { ...n.data, status: s.status, outputs: s.outputs, verdicts: s.status === "flagged" ? s.verdicts : n.data.verdicts }
        : { ...n.data, status: "idle", outputs: undefined };
      return { ...n, data };
    }));

  const saveTimer = useRef<number | undefined>(undefined);
  const save = () => {
    window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(async () => {
      const w = workflow();
      if (!w.spec.id) return;
      setErrors((await api.save(w)).errors);
      if (!live.current.running) applyState(await api.state(w.spec));
    }, 500);
  };

  const history = useHistory(
    () => ({ nodes: live.current.nodes, edges: live.current.edges }),
    (s) => { setNodes(s.nodes); setEdges(s.edges); save(); },
  );
  const undoRef = useRef(history);
  undoRef.current = history;

  const open = async (id: string) => {
    const w = await api.load(id);
    const canvas = toCanvas(w);
    setMeta({ id: w.spec.id, name: w.spec.name });
    setNodes(canvas.nodes);
    setEdges(canvas.edges);
    setSelected(null);
    history.clear();
    applyState(await api.state(w.spec));
    // Fit the workflow on screen, but never zoom past 100% (a lone node would fill the screen).
    window.setTimeout(() => (canvas.nodes.length
      ? flow.fitView({ padding: 0.15, maxZoom: 1 })
      : flow.setViewport({ x: 0, y: 0, zoom: 1 })), 50);
  };

  useEffect(() => {
    void api.nodes().then(setSchemas);
    void api.workflows().then((ws) => { setList(ws); if (ws[0]) void open(ws[0].id); });
    // Ctrl+Z / Ctrl+Shift+Z (or Ctrl+Y); text fields keep their own undo.
    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey) || (e.target as HTMLElement).closest("input, textarea, select")) return;
      const key = e.key.toLowerCase();
      if (key === "z" && !e.shiftKey) { e.preventDefault(); undoRef.current.undo(); }
      if ((key === "z" && e.shiftKey) || key === "y") { e.preventDefault(); undoRef.current.redo(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const create = async () => {
    const id = `workflow-${Date.now().toString(36)}`;
    await api.save({ spec: { id, name: "Untitled workflow", version: 1, nodes: [], edges: [] }, layout: {} });
    setList(await api.workflows());
    await open(id);
  };

  /** Two clicks: the first asks, the second resets. */
  const reset = async () => {
    if (!confirmReset) {
      setConfirmReset(true);
      window.setTimeout(() => setConfirmReset(false), 3000);
      return;
    }
    setConfirmReset(false);
    await api.reset(meta.id);
    setList(await api.workflows());
    await open(meta.id);
  };

  const onEvent = (e: RunEvent) => {
    setEvents((es) => [...es, e]);
    if (!e.node) return;
    if (e.kind === "started") patch(e.node, { status: "running", error: undefined, verdicts: [] });
    if (e.kind === "verdict" && e.verdict) {
      const v = e.verdict;
      setNodes((ns) => ns.map((n) => n.id === e.node
        ? { ...n, data: { ...n.data, verdicts: [...(n.data.verdicts ?? []), v] } } : n));
    }
    if (e.kind === "done") patch(e.node, { status: "done", outputs: e.outputs, cost: e.cost });
    if (e.kind === "flagged") patch(e.node, { status: "flagged", outputs: e.outputs, cost: e.cost });
    if (e.kind === "failed") patch(e.node, { status: "failed", error: e.error, cost: e.cost });
    if (e.kind === "blocked") patch(e.node, { status: "blocked" });
  };

  const run = async (targets?: string[]) => {
    window.clearTimeout(saveTimer.current);
    const w = workflow();
    try {
      await api.save(w);
      const { run_id } = await api.run(w.spec, targets);
      setRunning((r) => r + 1);
      api.events(run_id, (e) => {
        onEvent(e);
        if (e.kind === "finished" || e.kind === "error") setRunning((r) => r - 1);
      });
    } catch (err) {
      setErrors(String(err instanceof Error ? err.message : err).split("; "));
    }
  };

  const studio: Studio = {
    schemas: byType,
    setParams: (id, change: Record<string, Json>) => {
      history.remember(true);
      setNodes((ns) => ns.map((n) => n.id === id ? { ...n, data: { ...n.data, params: { ...n.data.params, ...change } } } : n));
      save();
    },
    setCheck: (id, check: CheckSpec | null) => { history.remember(true); patch(id, { check }); save(); },
    runNode: (id) => void run([id]),
    upload: async (id, file) => studio.setParams(id, { asset: await api.upload(file) }),
    accept: async (id, outputs?: Outputs) => {
      const w = workflow();
      await api.review(w.spec, id, outputs);
      applyState(await api.state(w.spec));
    },
  };

  const add = (type: string) => {
    const schema = byType.get(type)!;
    const id = newId(type, new Set(nodes.map((n) => n.id)));
    const position = flow.screenToFlowPosition({ x: window.innerWidth / 2 - 140, y: window.innerHeight / 3 });
    history.remember();
    setNodes((ns) => [...ns, { id, type: "card", position, data: { type, params: defaults(schema), check: null, status: "idle" } }]);
    setSelected(id);
    save();
  };

  const socketOf = (c: Connection | Edge, side: "source" | "target") => {
    const n = nodes.find((x) => x.id === c[side]);
    const s = n && byType.get(n.data.type);
    if (!s) return undefined;
    return side === "source" ? s.outputs[c.sourceHandle ?? ""] : s.inputs[c.targetHandle ?? ""]?.socket;
  };
  const isValidConnection = useCallback((c: Connection | Edge) => {
    const out = socketOf(c, "source"), inp = socketOf(c, "target");
    return Boolean(out && inp && c.source !== c.target && compatible(out, inp));
  }, [nodes, byType]);
  const onConnect = (c: Connection) => {
    // One wire per input: a new one replaces the old.
    history.remember();
    setEdges((es) => [...es.filter((e) => !(e.target === c.target && e.targetHandle === c.targetHandle)),
      wire(c.source, c.sourceHandle ?? "", c.target, c.targetHandle ?? "")]);
    save();
  };

  const threads = useMemo(() => edges.map((e) => ({
    ...e,
    animated: nodes.find((n) => n.id === e.target)?.data.status === "running",
    style: { stroke: edgeColor(e, nodes, byType), strokeWidth: 2.5 },
  })), [edges, nodes, byType]);

  const chosen = nodes.find((n) => n.id === selected);

  return (
    <StudioContext.Provider value={studio}>
      <div className={`studio mode-${mode}`}>
        <header className="bar">
          <h1>Compi</h1>
          <select value={meta.id} onChange={(e) => void open(e.target.value)}>
            {list.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <button className="ghost" onClick={() => void create()} title="Start a blank canvas">＋ New</button>
          <input className="name" value={meta.name} aria-label="Workflow name"
            onChange={(e) => {
              setMeta({ ...meta, name: e.target.value });
              setList((l) => l.map((w) => (w.id === meta.id ? { ...w, name: e.target.value } : w)));
              save();
            }} />
          <button className="ghost" onClick={history.undo} disabled={!history.canUndo} title="Undo (Ctrl+Z)">↶</button>
          <button className="ghost" onClick={history.redo} disabled={!history.canRedo} title="Redo (Ctrl+Shift+Z)">↷</button>
          {list.find((w) => w.id === meta.id)?.builtin && (
            <button className={confirmReset ? "ghost warn" : "ghost"} onClick={() => void reset()}
              title="Put this ready-made workflow back to the original">
              {confirmReset ? "Sure? Reset" : "Reset"}
            </button>
          )}
          <div className="modes" role="tablist">
            <button className={mode === "loom" ? "on" : ""} onClick={() => setMode("loom")}>Canvas</button>
            <button className={mode === "app" ? "on" : ""} onClick={() => setMode("app")}>App</button>
            <button className={mode === "gallery" ? "on" : ""} onClick={() => setMode("gallery")}>Gallery</button>
          </div>
          <button className="primary" onClick={() => void run()} disabled={running > 0}>
            {running > 0 ? "Running…" : "Run all"}
          </button>
        </header>

        {errors.length > 0 && (
          <div className="errors" onClick={() => setErrors([])}>{errors.map((e) => <p key={e}>{e}</p>)}</div>
        )}

        {mode === "gallery" ? (
          <Gallery refresh={events.length} />
        ) : mode === "app" ? (
          <AppMode nodes={nodes} edges={edges} running={running > 0} onRun={() => void run()} />
        ) : (
          <main className="loom">
            <Palette schemas={schemas} onAdd={add} />
            <div className="canvas">
              <ReactFlow
                nodes={nodes} edges={threads} nodeTypes={nodeTypes}
                onNodesChange={(ch) => {
                  const removing = ch.getByType("remove").length > 0;
                  if (removing) history.remember(true);
                  onNodesChange(ch);
                  if (removing) save();
                }}
                onEdgesChange={(ch) => {
                  const removing = ch.getByType("remove").length > 0;
                  if (removing) history.remember(true); // merges with the node removal that caused it
                  onEdgesChange(ch);
                  if (removing) save();
                }}
                onConnect={onConnect} isValidConnection={isValidConnection}
                onNodeDragStart={() => history.remember()} onNodeDragStop={save} onNodeClick={(_, n) => setSelected(n.id)} onPaneClick={() => setSelected(null)}
                minZoom={0.2} fitView fitViewOptions={{ maxZoom: 1 }} proOptions={{ hideAttribution: true }}
              >
                <Background variant={BackgroundVariant.Lines} gap={24} lineWidth={0.6} color="var(--weft)" />
                <Controls showInteractive={false} />
              </ReactFlow>
            </div>
            <aside className="side">
              {chosen ? <Inspector key={chosen.id} node={chosen} /> : null}
              <Ledger events={events} onPick={setSelected} />
            </aside>
          </main>
        )}
      </div>
    </StudioContext.Provider>
  );
}
