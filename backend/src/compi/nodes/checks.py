"""Checker nodes: run on another node's outputs (input "value") and return a Verdict."""

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel

from compi.domain.sockets import Socket
from compi.domain.verdict import Verdict
from compi.engine.registry import Outputs, node
from compi.services import llm, media


class TextRules(BaseModel):
    port: str = "text"
    must_include: list[str] = []
    max_chars: int | None = None


@node(
    "check.text",
    category="Checkers",
    inputs={"value": Socket.ANY},
    outputs={"verdict": Socket.ANY},
    params=TextRules,
)
async def check_text(inputs: Mapping[str, Any], params: TextRules) -> Outputs:
    text = str(inputs["value"][params.port])
    problems = [f"must include '{w}'" for w in params.must_include if w.lower() not in text.lower()]
    if params.max_chars is not None and len(text) > params.max_chars:
        problems.append(f"must be at most {params.max_chars} characters")
    decision = "retry" if problems else "pass"
    verdict = Verdict(decision=decision, reasons=problems, fix_hint="; ".join(problems) or None)
    return {"verdict": verdict.model_dump()}


class VisionRules(BaseModel):
    rules: str = "The image follows the prompt, looks professional, and has no garbled text."
    effort: Literal["low", "medium", "high"] = "low"


INSTRUCTIONS = (
    "You are an art director checking one step of an image pipeline. Judge only against the "
    "rules. decision: pass if every rule holds; retry if a new attempt could fix it (give a "
    "concrete fix_hint the generator can follow); flag only if a person must decide."
)


@node(
    "check.vision",
    category="Checkers",
    inputs={"value": Socket.ANY},
    outputs={"verdict": Socket.ANY},
    params=VisionRules,
)
async def check_vision(inputs: Mapping[str, Any], params: VisionRules) -> Outputs:
    given: Mapping[str, Any] = inputs.get("inputs") or {}
    refs = [v for k, v in given.items() if k != "feedback" and media.is_image(v)]
    made = [v for v in inputs["value"].values() if media.is_image(v)]
    texts = {k: v for k, v in given.items() if isinstance(v, str) and not media.is_image(v)}
    prompt = (
        f"Rules: {params.rules}\nThe step was given: {texts}\n"
        f"The first {len(refs)} image(s) are what it was given; "
        f"the last {len(made)} are its output."
    )
    verdict = await llm.ask(Verdict, INSTRUCTIONS, prompt, refs + made, params.effort)
    return {"verdict": verdict.model_dump()}
