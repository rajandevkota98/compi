import type { RunEvent } from "./api";
import { money } from "./studio";

const VERB: Record<RunEvent["kind"], string> = {
  started: "started", verdict: "checked", done: "done", flagged: "flagged for review",
  failed: "failed", blocked: "waiting", finished: "run finished", error: "run error",
};

/** Every event of the session's runs, newest first, like a weaver's tally. */
export function Ledger({ events, onPick }: { events: RunEvent[]; onPick: (id: string) => void }) {
  const total = events.reduce((sum, e) => sum + (e.cost ?? 0), 0);
  return (
    <section className="ledger">
      <h2>Ledger <span className="muted">{money(total)}</span></h2>
      {events.length === 0 && <p className="muted">Run a node to see each step here.</p>}
      <ol>
        {events.map((e, i) => (
          <li key={events.length - i} className={`ev ${e.kind} ${e.verdict?.decision ?? ""}`}
            onClick={() => e.node && onPick(e.node)}>
            <code>{e.node ?? "·"}</code> {VERB[e.kind]}
            {e.verdict && <> — <b>{e.verdict.decision}</b> {e.verdict.reasons.join("; ")}</>}
            {e.error && <> — {e.error}</>}
            {e.result && <> — ran {e.result.ran.length}, held {Object.keys(e.result.held).length}</>}
            {e.cost ? <span className="cost">{money(e.cost)}</span> : null}
          </li>
        )).reverse()}
      </ol>
    </section>
  );
}
