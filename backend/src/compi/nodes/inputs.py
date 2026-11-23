"""Input nodes: values typed by the user on the canvas."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from compi.domain.sockets import Socket
from compi.engine.registry import Outputs, node


class TextParams(BaseModel):
    text: str = ""


class NumberParams(BaseModel):
    value: float = 0.0


@node("text.input", category="Inputs", outputs={"text": Socket.TEXT}, params=TextParams)
async def text_input(inputs: Mapping[str, Any], params: TextParams) -> Outputs:
    return {"text": params.text}


@node("number.input", category="Inputs", outputs={"value": Socket.NUMBER}, params=NumberParams)
async def number_input(inputs: Mapping[str, Any], params: NumberParams) -> Outputs:
    return {"value": params.value}


class ImageParams(BaseModel):
    asset: str = ""  # media file name, set by uploading on the canvas


@node("image.input", category="Inputs", outputs={"image": Socket.IMAGE}, params=ImageParams)
async def image_input(inputs: Mapping[str, Any], params: ImageParams) -> Outputs:
    if not params.asset:
        raise ValueError("upload an image first")
    return {"image": params.asset}
