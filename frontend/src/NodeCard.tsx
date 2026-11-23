import { Handle, Position, type NodeProps } from "@xyflow/react";
import { isImage, mediaUrl } from "./api";
import { SOCKET_COLOR, type Card } from "./graph";
import { ParamField } from "./ParamField";
import { Preview } from "./Preview";
import { money, title, useStudio } from "./studio";

const HIDDEN = new Set(["asset"]); // set by upload, not typed

export function NodeCard({ id, data, selected }: NodeProps<Card>) {
  const studio = useStudio();
  const schema = studio.schemas.get(data.type);
  if (!schema) return <div className="card status-failed">Unknown node {data.type}</div>;
  const props = Object.entries(schema.params.properties ?? {}).filter(([k]) => !HIDDEN.has(k));
  const last = data.verdicts?.at(-1);
  const asset = data.params.asset;

  return (
    <div className={`card status-${data.status} cat-${schema.category.toLowerCase()} ${selected ? "selected" : ""}`}>
      <header>
        <span className="cat">{schema.category}</span>
        <b>{title(data.type)}</b>
        <code className="nid">{id}</code>
        <button className="run nodrag" title="Run this node" onClick={() => studio.runNode(id)}>▶</button>
      </header>

      {Object.entries(schema.inputs).map(([port, { socket, optional }]) => (
        <div className="port in" key={port}>
          <Handle type="target" position={Position.Left} id={port} style={{ background: SOCKET_COLOR[socket] }} />
          {port}{optional ? "" : "*"} <i>{socket}</i>
        </div>
      ))}

      {data.type === "image.input" && (
        <label className="drop nodrag">
          {isImage(asset ?? null) ? <img src={mediaUrl(String(asset))} alt="" /> : <span>Drop or pick a photo</span>}
          <input type="file" accept="image/*" hidden
            onChange={(e) => e.target.files?.[0] && studio.upload(id, e.target.files[0])} />
        </label>
      )}

      {props.length > 0 && (
        <div className="params">
          {props.map(([k, p]) => (
            <ParamField key={k} name={k} schema={p} value={data.params[k] ?? p.default ?? null}
              onChange={(v) => studio.setParams(id, { [k]: v })} />
          ))}
        </div>
      )}

      {Object.entries(schema.outputs).map(([port, socket]) => (
        <div className="port out" key={port}>
          <i>{socket}</i> {port}
          <Handle type="source" position={Position.Right} id={port} style={{ background: SOCKET_COLOR[socket] }} />
        </div>
      ))}

      {data.outputs && data.type !== "image.input" && (
        <div className="preview">{Object.values(data.outputs).map((v, i) => <Preview key={i} value={v} />)}</div>
      )}

      <footer>
        {data.check && (
          <span className={`stamp ${last?.decision ?? "wait"}`} title={last?.reasons.join("; ")}>
            {last?.decision === "pass" ? "✓ checked" : last?.decision === "flag" ? "✕ flagged" : last ? "↻ retrying" : "checker"}
          </span>
        )}
        {data.status === "flagged" && (
          <button className="nodrag accept" onClick={() => studio.accept(id)}>Accept</button>
        )}
        {data.error && <span className="error" title={data.error}>{data.error}</span>}
        <span className="cost">{money(data.cost)}</span>
      </footer>
    </div>
  );
}
