// Canvas <-> WorkflowSpec. React Flow holds the truth while editing; the spec is derived.
import type { Edge, Node } from "@xyflow/react";
import type { CheckSpec, Json, NodeSchema, Outputs, Socket, Verdict, Workflow, WorkflowSpec } from "./api";

export type Status = "idle" | "running" | "done" | "flagged" | "failed" | "blocked";
export interface CardData extends Record<string, unknown> {
  type: string;
  params: Record<string, Json>;
  check: CheckSpec | null;
  status: Status;
  outputs?: Outputs;
  verdicts?: Verdict[];
  cost?: number;
  error?: string;
}
export type Card = Node<CardData, "card">;

export const SOCKET_COLOR: Record<Socket, string> = {
  text: "var(--indigo)", image: "var(--madder)", list: "var(--turmeric)",
  number: "var(--leaf)", mask: "var(--ink-soft)", any: "var(--ink-soft)",
};

export function toCanvas(w: Workflow): { nodes: Card[]; edges: Edge[] } {
  const nodes = w.spec.nodes.map((n): Card => ({
    id: n.id,
    type: "card",
    position: w.layout[n.id] ?? { x: 0, y: 0 },
    data: { type: n.type, params: n.params, check: n.check ?? null, status: "idle" },
  }));
  const edges = w.spec.edges.map((e) => wire(e.source, e.source_port, e.target, e.target_port));
  return { nodes, edges };
}

export function wire(source: string, sourceHandle: string, target: string, targetHandle: string): Edge {
  return { id: `${source}.${sourceHandle}>${target}.${targetHandle}`, source, sourceHandle, target, targetHandle };
}

export function toWorkflow(meta: { id: string; name: string }, nodes: Card[], edges: Edge[]): Workflow {
  const spec: WorkflowSpec = {
    ...meta,
    version: 1,
    nodes: nodes.map((n) => ({ id: n.id, type: n.data.type, params: n.data.params, check: n.data.check })),
    edges: edges.map((e) => ({
      source: e.source, source_port: e.sourceHandle ?? "", target: e.target, target_port: e.targetHandle ?? "",
    })),
  };
  const layout = Object.fromEntries(nodes.map((n) => [n.id, { x: Math.round(n.position.x), y: Math.round(n.position.y) }]));
  return { spec, layout };
}

/** Same rule as backend domain/sockets.py:compatible. */
export const compatible = (out: Socket, inp: Socket) => out === inp || out === "any" || inp === "any";

export function defaults(schema: NodeSchema): Record<string, Json> {
  const props = schema.params.properties ?? {};
  return Object.fromEntries(Object.entries(props).map(([k, p]) => [k, p.default ?? null]));
}

export function newId(type: string, taken: Set<string>): string {
  const base = type.split(".").pop()!.replace(/[^A-Za-z0-9_-]/g, "");
  let i = 1;
  while (taken.has(`${base}${i}`)) i++;
  return `${base}${i}`;
}

/** Edge colour follows the socket type of the output it comes from. */
export function edgeColor(e: Edge, nodes: Card[], schemas: Map<string, NodeSchema>): string {
  const src = nodes.find((n) => n.id === e.source);
  const socket = src && schemas.get(src.data.type)?.outputs[e.sourceHandle ?? ""];
  return socket ? SOCKET_COLOR[socket] : "var(--ink-soft)";
}
