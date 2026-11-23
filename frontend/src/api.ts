// Types mirror backend/src/compi/domain/spec.py and engine/registry.py:schema().

export type Socket = "text" | "number" | "image" | "mask" | "list" | "any";
export type Json = string | number | boolean | null | Json[] | { [k: string]: Json };
export type Outputs = Record<string, Json>;

export interface CheckSpec { type: string; params: Record<string, Json>; max_retries: number }
export interface NodeSpec { id: string; type: string; params: Record<string, Json>; check?: CheckSpec | null }
export interface EdgeSpec { source: string; source_port: string; target: string; target_port: string }
export interface WorkflowSpec { id: string; name: string; version: number; nodes: NodeSpec[]; edges: EdgeSpec[] }
export interface Workflow { spec: WorkflowSpec; layout: Record<string, { x: number; y: number }> }
export interface WorkflowInfo { id: string; name: string; builtin: boolean }

export interface ParamSchema {
  type?: string; enum?: Json[]; default?: Json; minimum?: number; maximum?: number;
  description?: string; title?: string; items?: { type?: string }; anyOf?: ParamSchema[];
}
export interface NodeSchema {
  type: string; category: string; version: number;
  inputs: Record<string, { socket: Socket; optional: boolean }>;
  outputs: Record<string, Socket>;
  params: { properties?: Record<string, ParamSchema> };
}
export interface Verdict { decision: "pass" | "retry" | "flag"; reasons: string[]; fix_hint: string | null }
export interface RunEvent {
  kind: "started" | "verdict" | "done" | "flagged" | "failed" | "blocked" | "finished" | "error";
  node?: string; outputs?: Outputs; cost?: number; error?: string; verdict?: Verdict;
  verdicts?: Verdict[]; waiting_on?: string[];
  result?: { outputs: Record<string, Outputs>; ran: string[]; held: Record<string, string> };
}
export type NodeState = { status: "done"; outputs: Outputs } | { status: "flagged"; outputs: Outputs; verdicts: Verdict[] };

async function call<T>(method: string, url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(Array.isArray(data.detail) ? data.detail.join("; ") : String(data.detail));
  return data as T;
}

export const api = {
  nodes: () => call<NodeSchema[]>("GET", "/api/nodes"),
  workflows: () => call<WorkflowInfo[]>("GET", "/api/workflows"),
  reset: (id: string) => call<Workflow>("POST", `/api/workflows/${id}/reset`),
  gallery: () => call<{ name: string; time: number }[]>("GET", "/api/media"),
  load: (id: string) => call<Workflow>("GET", `/api/workflows/${id}`),
  save: (w: Workflow) => call<{ errors: string[] }>("PUT", `/api/workflows/${w.spec.id}`, w),
  state: (spec: WorkflowSpec) => call<Record<string, NodeState>>("POST", "/api/state", spec),
  run: (spec: WorkflowSpec, targets?: string[]) => call<{ run_id: string }>("POST", "/api/runs", { spec, targets }),
  review: (spec: WorkflowSpec, node_id: string, outputs?: Outputs) =>
    call<{ ok: boolean }>("POST", "/api/review", { spec, node_id, outputs }),
  upload: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/media", { method: "POST", body: form });
    return ((await res.json()) as { asset: string }).asset;
  },
  /** Live events of a run; calls back until "finished" or "error". */
  events: (runId: string, onEvent: (e: RunEvent) => void) => {
    const source = new EventSource(`/api/runs/${runId}/events`);
    source.onmessage = (m) => {
      const event = JSON.parse(m.data) as RunEvent;
      onEvent(event);
      if (event.kind === "finished" || event.kind === "error") source.close();
    };
    source.onerror = () => source.close();
  },
};

export const isImage = (v: Json): v is string => typeof v === "string" && /^[0-9a-f]{24}\.(png|jpe?g|webp)$/.test(v);
export const mediaUrl = (name: string) => `/media/${name}`;
