"""Settings from the environment (uvicorn loads ../.env via --env-file)."""

import os
from pathlib import Path

DATA = Path(os.environ.get("COMPI_DATA", "data")).resolve()
LLM_MODEL = os.environ.get("COMPI_LLM_MODEL", "claude-opus-5-5")
OPENROUTER_URL = "https://openrouter.ai/api/v1/images"


def openrouter_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set (add it to .env)")
    return key
