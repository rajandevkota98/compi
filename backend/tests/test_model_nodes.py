"""The product-ad workflow end to end, with fake image and LLM services."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from test_media_nodes import photo

from compi.domain.spec import WorkflowSpec, set_params
from compi.domain.verdict import Verdict
from compi.engine.cache import MemoryCache
from compi.engine.run import stream
from compi.nodes.llm import Ideas
from compi.services import costs, images, llm

WORKFLOW = Path(__file__).parents[2] / "workflows" / "product-ad.json"


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    prompts: list[str] = []
    checks = iter(["retry", "pass", "pass", "pass"])

    async def generate(model: str, prompt: str, refs: list[str], aspect_ratio: str) -> str:
        prompts.append(prompt)
        costs.add(0.04)
        return photo("green")

    async def ask(schema: type[BaseModel], instructions: str, prompt: str, *_: Any) -> Any:
        if schema is Ideas:
            return Ideas(items=["rooftop at dusk", "rainy street", "gift box"])
        verdict = {
            "decision": next(checks),
            "reasons": ["logo missing"],
            "fix_hint": "show the logo",
        }
        return Verdict.model_validate(verdict)

    monkeypatch.setattr(images, "generate", generate)
    monkeypatch.setattr(llm, "ask", ask)
    return prompts


async def test_product_ad_runs_per_idea_with_checker_retry(fakes: list[str]) -> None:
    spec = WorkflowSpec.model_validate(json.loads(WORKFLOW.read_text())["spec"])
    spec = set_params(spec, "photo", asset=photo())
    events = [e async for e in stream(spec, MemoryCache())]
    result = events[-1]["result"]

    assert len(result.outputs["board"]["items"]) == 3
    assert len(fakes) == 4  # 3 ideas + 1 retry
    assert sum("Fix: show the logo" in p for p in fakes) == 1
    shot = next(e for e in events if e["kind"] == "done" and e["node"] == "shot")
    assert shot["cost"] == pytest.approx(0.16)
