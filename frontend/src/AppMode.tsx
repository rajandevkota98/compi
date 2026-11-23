import type { Edge } from "@xyflow/react";
import { isImage, mediaUrl } from "./api";
import type { Card } from "./graph";
import { ParamField } from "./ParamField";
import { Preview } from "./Preview";
import { title, useStudio } from "./studio";

/** The workflow as a simple tool: its inputs as a form, its last steps as results. */
export function AppMode({ nodes, edges, running, onRun }: {
  nodes: Card[]; edges: Edge[]; running: boolean; onRun: () => void;
}) {
  const studio = useStudio();
  const inputs = nodes.filter((n) => studio.schemas.get(n.data.type)?.category === "Inputs");
  const results = nodes.filter((n) => !edges.some((e) => e.source === n.id));
  return (
    <div className="appmode">
      <form className="form" onSubmit={(e) => { e.preventDefault(); onRun(); }}>
        {inputs.map((n) => (
          <fieldset key={n.id}>
            <legend>{title(n.data.type)} <code>{n.id}</code></legend>
            {n.data.type === "image.input" ? (
              <label className="drop">
                {isImage(n.data.params.asset ?? null)
                  ? <img src={mediaUrl(String(n.data.params.asset))} alt="" /> : <span>Pick a photo</span>}
                <input type="file" accept="image/*" hidden
                  onChange={(e) => e.target.files?.[0] && studio.upload(n.id, e.target.files[0])} />
              </label>
            ) : (
              Object.entries(studio.schemas.get(n.data.type)?.params.properties ?? {}).map(([k, p]) => (
                <ParamField key={k} name={k} schema={p} value={n.data.params[k] ?? p.default ?? null}
                  onChange={(v) => studio.setParams(n.id, { [k]: v })} />
              ))
            )}
          </fieldset>
        ))}
        <button className="primary" disabled={running}>{running ? "Weaving…" : "Run"}</button>
      </form>
      <div className="results">
        {results.map((n) => (
          <figure key={n.id} className={`status-${n.data.status}`}>
            <figcaption>{title(n.data.type)} <code>{n.id}</code> · {n.data.status}</figcaption>
            {n.data.outputs ? Object.values(n.data.outputs).map((v, i) => <Preview key={i} value={v} big />)
              : <p className="muted">Not run yet.</p>}
          </figure>
        ))}
      </div>
    </div>
  );
}
