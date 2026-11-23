import { useState } from "react";
import type { CheckSpec } from "./api";
import type { Card } from "./graph";
import { ParamField } from "./ParamField";
import { Preview } from "./Preview";
import { money, title, useStudio } from "./studio";

/** The selected node in full: its checker, every verdict, outputs, and review actions. */
export function Inspector({ node }: { node: Card }) {
  const studio = useStudio();
  const { data } = node;
  const checkers = [...studio.schemas.values()].filter((s) => s.category === "Checkers");
  const check = data.check;
  const checkSchema = check && studio.schemas.get(check.type);
  const textOut = data.outputs && typeof data.outputs.text === "string" ? data.outputs.text : null;
  const [draft, setDraft] = useState<string | null>(null);
  const setCheck = (patch: Partial<CheckSpec>) => check && studio.setCheck(node.id, { ...check, ...patch });

  return (
    <section className="inspector">
      <h2>{title(data.type)} <code>{node.id}</code></h2>
      <p className="muted">{data.status}{data.cost ? ` · ${money(data.cost)}` : ""}</p>

      <h3>Checker agent</h3>
      <select value={check?.type ?? ""} onChange={(e) => studio.setCheck(node.id, e.target.value
        ? { type: e.target.value, params: {}, max_retries: 2 } : null)}>
        <option value="">None</option>
        {checkers.map((c) => <option key={c.type} value={c.type}>{title(c.type)}</option>)}
      </select>
      {check && checkSchema && (
        <div className="params">
          {Object.entries(checkSchema.params.properties ?? {}).map(([k, p]) => (
            <ParamField key={k} name={k} schema={p} value={check.params[k] ?? p.default ?? null}
              onChange={(v) => setCheck({ params: { ...check.params, [k]: v } })} />
          ))}
          <ParamField name="max_retries" schema={{ type: "integer", minimum: 0, maximum: 5 }}
            value={check.max_retries} onChange={(v) => setCheck({ max_retries: Number(v) })} />
        </div>
      )}

      {data.verdicts?.length ? (
        <>
          <h3>Verdicts</h3>
          <ol className="verdicts">
            {data.verdicts.map((v, i) => (
              <li key={i} className={v.decision}><b>{v.decision}</b> {v.reasons.join("; ")}
                {v.fix_hint && <em> → {v.fix_hint}</em>}</li>
            ))}
          </ol>
        </>
      ) : null}

      {data.status === "flagged" && (
        <div className="review">
          <h3>Needs your call</h3>
          <button onClick={() => studio.accept(node.id)}>Accept as is</button>
          {textOut !== null && (
            <>
              <textarea rows={5} value={draft ?? textOut} onChange={(e) => setDraft(e.target.value)} />
              <button onClick={() => studio.accept(node.id, { text: draft ?? textOut })}>Use my fix</button>
            </>
          )}
        </div>
      )}
      {data.error && <p className="error">{data.error}</p>}

      {data.outputs && (
        <>
          <h3>Output</h3>
          {Object.entries(data.outputs).map(([k, v]) => <div key={k}><code>{k}</code><Preview value={v} big /></div>)}
        </>
      )}
    </section>
  );
}
