"""LLM nodes, served by Claude."""

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field

from compi.domain.sockets import Socket
from compi.engine.registry import Outputs, node
from compi.engine.step import feedback_note
from compi.services import llm

INPUTS = {"prompt": Socket.TEXT, "image": Socket.IMAGE}
Effort = Literal["low", "medium", "high"]


class Answer(BaseModel):
    text: str


class Ideas(BaseModel):
    items: list[str]


class RunParams(BaseModel):
    instructions: str = "You are a sharp creative assistant. Reply with the answer only."
    effort: Effort = "medium"


class EnhanceParams(RunParams):
    instructions: str = (
        "Rewrite the user's image prompt so an image model gets it right: subject, setting, "
        "composition, lighting, lens and mood. Keep every fact the user gave. "
        "Return only the prompt."
    )


class ListParams(RunParams):
    count: int = Field(3, ge=1, le=10)


def _ask_args(inputs: Mapping[str, Any]) -> tuple[str, list[str]]:
    image = inputs.get("image")
    return str(inputs["prompt"]) + feedback_note(inputs), [image] if image else []


async def run_llm(inputs: Mapping[str, Any], params: RunParams) -> Outputs:
    prompt, images = _ask_args(inputs)
    answer = await llm.ask(Answer, params.instructions, prompt, images, params.effort)
    return {"text": answer.text}


for type_, params_model in (("llm.run", RunParams), ("llm.enhance", EnhanceParams)):
    node(
        type_,
        category="LLM",
        inputs=INPUTS,
        optional=("image",),
        outputs={"text": Socket.TEXT},
        params=params_model,
    )(run_llm)


@node(
    "llm.list",
    category="LLM",
    inputs=INPUTS,
    optional=("image",),
    outputs={"items": Socket.LIST},
    params=ListParams,
)
async def list_llm(inputs: Mapping[str, Any], params: ListParams) -> Outputs:
    prompt, images = _ask_args(inputs)
    prompt += f"\n\nGive exactly {params.count} distinct items."
    ideas = await llm.ask(Ideas, params.instructions, prompt, images, params.effort)
    return {"items": ideas.items[: params.count]}
