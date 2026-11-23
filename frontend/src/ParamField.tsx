import type { Json, ParamSchema } from "./api";

const LONG = new Set(["text", "instructions", "rules"]);

/** One form control, chosen from the param's JSON schema (pydantic model_json_schema). */
export function ParamField({ name, schema, value, onChange }: {
  name: string; schema: ParamSchema; value: Json; onChange: (v: Json) => void;
}) {
  const s = schema.anyOf?.find((o) => o.type !== "null") ?? schema;
  const label = <span className="param-label" title={schema.description}>{name.replace(/_/g, " ")}</span>;
  let control;
  if (s.enum) {
    control = (
      <select value={String(value)} onChange={(e) => onChange(e.target.value)}>
        {s.enum.map((o) => <option key={String(o)}>{String(o)}</option>)}
      </select>
    );
  } else if (s.type === "boolean") {
    control = <input type="checkbox" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />;
  } else if (s.type === "integer" || s.type === "number") {
    control = (
      <input
        type="number" value={value === null ? "" : Number(value)} min={s.minimum} max={s.maximum}
        step={s.type === "integer" ? 1 : 0.05}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      />
    );
  } else if (s.type === "array") {
    const lines = Array.isArray(value) ? value.join("\n") : "";
    control = <textarea rows={3} value={lines} placeholder="one per line"
      onChange={(e) => onChange(e.target.value.split("\n").filter((l) => l.trim()))} />;
  } else {
    const text = value === null ? "" : String(value);
    control = LONG.has(name) || text.length > 40
      ? <textarea rows={3} value={text} onChange={(e) => onChange(e.target.value)} />
      : <input value={text} onChange={(e) => onChange(e.target.value)} />;
  }
  return <label className="param nodrag">{label}{control}</label>;
}
