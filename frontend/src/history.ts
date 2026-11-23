import type { Edge } from "@xyflow/react";
import { useRef, useState } from "react";
import type { Card } from "./graph";

export interface Snapshot { nodes: Card[]; edges: Edge[] }

const LIMIT = 50;
const MERGE_MS = 800; // typing in one field is one undo step

/** Undo/redo over canvas snapshots. Call remember() just before each change. */
export function useHistory(current: () => Snapshot, restore: (s: Snapshot) => void) {
  const past = useRef<Snapshot[]>([]);
  const future = useRef<Snapshot[]>([]);
  const lastAt = useRef(0);
  const [, rerender] = useState(0);
  const changed = () => rerender((n) => n + 1);

  const remember = (merge = false) => {
    const now = Date.now();
    const recent = now - lastAt.current < MERGE_MS;
    lastAt.current = now;
    if (merge && recent) return;
    past.current = [...past.current.slice(1 - LIMIT), current()];
    future.current = [];
    changed();
  };
  const step = (from: { current: Snapshot[] }, to: { current: Snapshot[] }) => {
    const target = from.current.pop();
    if (!target) return;
    to.current.push(current());
    restore(target);
    lastAt.current = 0;
    changed();
  };

  return {
    remember,
    undo: () => step(past, future),
    redo: () => step(future, past),
    clear: () => { past.current = []; future.current = []; changed(); },
    canUndo: past.current.length > 0,
    canRedo: future.current.length > 0,
  };
}
