"""Image model nodes, served by OpenRouter."""

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field

from compi.domain.sockets import Socket
from compi.engine.registry import Outputs, node
from compi.engine.step import feedback_note
from compi.services import images

REFS = ("ref1", "ref2", "ref3")
ImageModel = Literal[
    "google/gemini-3.1-flash-image",
    "google/gemini-3-pro-image",
    "openai/gpt-image-2",
    "black-forest-labs/flux-3-image",
    "qwen/qwen-image-3",
    "bytedance-seed/seedream-5-0-pro",
]
Aspect = Literal["auto", "1:1", "4:5", "3:4", "2:3", "9:16", "16:9", "3:2", "4:3"]


class GenerateParams(BaseModel):
    model: ImageModel = "google/gemini-3.1-flash-image"
    aspect_ratio: Aspect = "1:1"
    seed: int = Field(0, description="change it to get a new variation with the same settings")


@node(
    "image.generate",
    category="Models",
    inputs={"prompt": Socket.TEXT, **dict.fromkeys(REFS, Socket.IMAGE)},
    optional=REFS,
    outputs={"image": Socket.IMAGE},
    params=GenerateParams,
)
async def generate(inputs: Mapping[str, Any], params: GenerateParams) -> Outputs:
    """Text to image, or image edit when reference images are connected."""
    prompt = str(inputs["prompt"]) + feedback_note(inputs)
    refs = [inputs[r] for r in REFS if inputs.get(r)]
    return {"image": await images.generate(params.model, prompt, refs, params.aspect_ratio)}
