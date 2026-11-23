import type { NodeSchema } from "./api";
import { title } from "./studio";

const ORDER = ["Inputs", "LLM", "Models", "Editing", "Helpers"];

/** Spools of node types; click one to add it to the canvas. Checkers attach in the inspector. */
export function Palette({ schemas, onAdd }: { schemas: NodeSchema[]; onAdd: (type: string) => void }) {
  return (
    <nav className="palette">
      {ORDER.map((cat) => (
        <div key={cat} className={`spool cat-${cat.toLowerCase()}`}>
          <h4>{cat}</h4>
          {schemas.filter((s) => s.category === cat).map((s) => (
            <button key={s.type} onClick={() => onAdd(s.type)}>{title(s.type)}</button>
          ))}
        </div>
      ))}
    </nav>
  );
}
