import { createContext, useContext } from "react";
import type { CheckSpec, Json, NodeSchema, Outputs } from "./api";

/** Actions node cards and panels can take, provided by App. */
export interface Studio {
  schemas: Map<string, NodeSchema>;
  setParams: (id: string, patch: Record<string, Json>) => void;
  setCheck: (id: string, check: CheckSpec | null) => void;
  runNode: (id: string) => void;
  upload: (id: string, file: File) => void;
  accept: (id: string, outputs?: Outputs) => void;
}

export const StudioContext = createContext<Studio | null>(null);
export const useStudio = () => useContext(StudioContext)!;

export const TITLES: Record<string, string> = {
  "text.input": "Text", "number.input": "Number", "image.input": "Image",
  "prompt.concat": "Prompt join", "list.text": "List", "list.iterate": "Iterator",
  "list.collect": "Collect", router: "Router", "llm.run": "Run LLM",
  "llm.enhance": "Prompt enhancer", "llm.list": "LLM list", "image.generate": "Image model",
  "image.resize": "Resize", "image.adjust": "Adjust", "image.remove_bg": "Remove background",
  "image.composite": "Compositor", "check.text": "Text checker", "check.vision": "Vision checker",
};
export const title = (type: string) => TITLES[type] ?? type;
export const money = (usd?: number) => (usd ? `$${usd < 0.01 ? usd.toFixed(4) : usd.toFixed(2)}` : "");
