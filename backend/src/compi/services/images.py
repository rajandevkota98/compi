"""Image models through OpenRouter's images endpoint."""

import base64
from typing import Any

import httpx

from compi.services import costs, media
from compi.services.settings import OPENROUTER_URL, openrouter_key


async def generate(model: str, prompt: str, refs: list[str], aspect_ratio: str) -> str:
    """Make one image from a prompt and optional reference images; returns its media name."""
    body: dict[str, object] = {"model": model, "prompt": prompt, "n": 1}
    if aspect_ratio != "auto":
        body["aspect_ratio"] = aspect_ratio
    if refs:
        body["input_references"] = [
            {"type": "image_url", "image_url": {"url": media.data_url(r)}} for r in refs
        ]
    async with httpx.AsyncClient(timeout=300) as client:
        res = await client.post(
            OPENROUTER_URL, json=body, headers={"Authorization": f"Bearer {openrouter_key()}"}
        )
    if res.status_code != 200:
        raise RuntimeError(f"OpenRouter {res.status_code}: {res.text[:300]}")
    out: dict[str, Any] = res.json()
    usage: dict[str, Any] = out.get("usage") or {}
    costs.add(usage.get("cost"))
    image = out["data"][0]
    ext = str(image.get("media_type", "image/png")).split("/")[-1]
    return media.save(base64.b64decode(image["b64_json"]), ext)
