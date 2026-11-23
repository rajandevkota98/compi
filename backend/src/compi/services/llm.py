"""Claude: one structured call used by every LLM and checker node."""

from typing import Any

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from compi.services import costs, media
from compi.services.settings import LLM_MODEL

# $ per million tokens (input, output) for cost display.
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0)}

_client: AsyncAnthropic | None = None


def client() -> AsyncAnthropic:
    global _client
    _client = _client or AsyncAnthropic()
    return _client


async def ask[T: BaseModel](
    schema: type[T], instructions: str, prompt: str, images: list[str], effort: str = "medium"
) -> T:
    """Ask Claude for an answer shaped like `schema`, optionally showing it images."""
    content: list[dict[str, Any]] = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": media.media_type(i), "data": media.b64(i)},
        }
        for i in images
    ]
    content.append({"type": "text", "text": prompt})
    res = await client().beta.messages.parse(
        model=LLM_MODEL,
        max_tokens=16000,
        system=instructions,
        messages=[{"role": "user", "content": content}],  # pyright: ignore[reportArgumentType]
        output_format=schema,
        output_config={"effort": effort},  # pyright: ignore[reportArgumentType]
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    price_in, price_out = PRICES.get(res.model, PRICES["claude-opus-5-5"])
    costs.add((res.usage.input_tokens * price_in + res.usage.output_tokens * price_out) / 1e6)
    if res.stop_reason == "refusal" or res.parsed_output is None:
        raise RuntimeError(f"Claude gave no answer (stop reason: {res.stop_reason})")
    return res.parsed_output
