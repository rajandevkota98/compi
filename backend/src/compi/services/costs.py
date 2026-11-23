"""Collect the dollar cost of model calls made while one node runs."""

from contextvars import ContextVar

_spent: ContextVar[list[float] | None] = ContextVar("spent", default=None)


def track() -> list[float]:
    """Start collecting for the current task (child tasks share the list)."""
    spent: list[float] = []
    _spent.set(spent)
    return spent


def add(usd: float | None) -> None:
    spent = _spent.get()
    if spent is not None and usd:
        spent.append(usd)
