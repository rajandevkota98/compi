"""What a checker decides about one node's output."""

from typing import Literal

from pydantic import BaseModel


class Verdict(BaseModel):
    decision: Literal["pass", "retry", "flag"]
    reasons: list[str] = []
    fix_hint: str | None = None
