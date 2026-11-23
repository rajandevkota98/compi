"""Editing nodes: plain Pillow (and rembg for backgrounds). No AI model, no cost."""

import asyncio
from collections.abc import Callable, Mapping
from functools import cache
from typing import Any, Literal

from PIL import Image, ImageEnhance, ImageOps
from pydantic import BaseModel, Field

from compi.domain.sockets import Socket
from compi.engine.registry import Outputs, node
from compi.services import media

IMG = {"image": Socket.IMAGE}
Edit = Callable[[Image.Image], Image.Image]


async def _edit(name: str, fn: Edit) -> Outputs:
    """Open → edit → save, off the event loop."""
    out = await asyncio.to_thread(
        lambda: media.save_image(fn(media.open_image(name).convert("RGBA")))
    )
    return {"image": out}


class ResizeParams(BaseModel):
    width: int = Field(1080, ge=16, le=4096)
    height: int = Field(1080, ge=16, le=4096)
    fit: Literal["cover", "contain", "stretch"] = "cover"


@node("image.resize", category="Editing", inputs=IMG, outputs=IMG, params=ResizeParams)
async def resize(inputs: Mapping[str, Any], params: ResizeParams) -> Outputs:
    size = (params.width, params.height)
    fits: dict[str, Edit] = {
        "cover": lambda im: ImageOps.fit(im, size),
        "contain": lambda im: ImageOps.pad(im, size, color=(0, 0, 0, 0)),
        "stretch": lambda im: im.resize(size),
    }
    return await _edit(inputs["image"], fits[params.fit])


class AdjustParams(BaseModel):
    brightness: float = Field(1.0, ge=0, le=3)
    contrast: float = Field(1.0, ge=0, le=3)
    saturation: float = Field(1.0, ge=0, le=3)


@node("image.adjust", category="Editing", inputs=IMG, outputs=IMG, params=AdjustParams)
async def adjust(inputs: Mapping[str, Any], params: AdjustParams) -> Outputs:
    def run(im: Image.Image) -> Image.Image:
        rgb, alpha = im.convert("RGB"), im.getchannel("A")
        for enhancer, amount in (
            (ImageEnhance.Brightness, params.brightness),
            (ImageEnhance.Contrast, params.contrast),
            (ImageEnhance.Color, params.saturation),
        ):
            rgb = enhancer(rgb).enhance(amount)
        rgb.putalpha(alpha)
        return rgb

    return await _edit(inputs["image"], run)


# ISNet (Apache-2.0). rembg's default, BRIA RMBG 2.0, is non-commercial and 1 GB.
BG_MODEL = "isnet-general-use"


@cache
def _bg_session() -> Any:
    from rembg import new_session  # pyright: ignore  (untyped, slow import: load on first use)

    return new_session(BG_MODEL)


@node("image.remove_bg", category="Editing", inputs=IMG, outputs=IMG)
async def remove_bg(inputs: Mapping[str, Any], params: BaseModel) -> Outputs:
    from rembg import remove  # pyright: ignore[reportMissingTypeStubs]

    return await _edit(inputs["image"], lambda im: remove(im, session=_bg_session()))  # pyright: ignore


class CompositeParams(BaseModel):
    x: float = Field(0.5, ge=0, le=1, description="centre of the foreground, 0 = left")
    y: float = Field(0.5, ge=0, le=1, description="centre of the foreground, 0 = top")
    scale: float = Field(0.6, ge=0.05, le=2, description="foreground width / background width")


@node(
    "image.composite",
    category="Editing",
    inputs={"background": Socket.IMAGE, "foreground": Socket.IMAGE},
    outputs=IMG,
    params=CompositeParams,
)
async def composite(inputs: Mapping[str, Any], params: CompositeParams) -> Outputs:
    fg = media.open_image(inputs["foreground"]).convert("RGBA")

    def run(bg: Image.Image) -> Image.Image:
        width = max(1, int(bg.width * params.scale))
        top = fg.resize((width, max(1, int(fg.height * width / fg.width))))
        pos = (int(bg.width * params.x - top.width / 2), int(bg.height * params.y - top.height / 2))
        bg.alpha_composite(top, (max(pos[0], 0), max(pos[1], 0)))
        return bg

    return await _edit(inputs["background"], run)
