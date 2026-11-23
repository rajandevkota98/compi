"""Node output cache, keyed by Merkle key. Swappable: memory for tests, disk for the app."""

import json
from pathlib import Path
from typing import Any, Protocol

from compi.domain.sockets import Items
from compi.engine.registry import Outputs


class Cache(Protocol):
    async def get(self, key: str) -> Outputs | None: ...
    async def put(self, key: str, outputs: Outputs) -> None: ...


class MemoryCache:
    def __init__(self) -> None:
        self._items: dict[str, Outputs] = {}

    async def get(self, key: str) -> Outputs | None:
        return self._items.get(key)

    async def put(self, key: str, outputs: Outputs) -> None:
        self._items[key] = outputs


def _encode(value: Any) -> Any:
    if isinstance(value, Items):
        return {"__items__": [_encode(v) for v in value]}
    if isinstance(value, dict):
        return {k: _encode(v) for k, v in value.items()}  # pyright: ignore[reportUnknownVariableType]
    return value


def _decode(value: Any) -> Any:
    if isinstance(value, dict):
        if "__items__" in value:
            return Items(_decode(v) for v in value["__items__"])  # pyright: ignore[reportUnknownVariableType]
        return {k: _decode(v) for k, v in value.items()}  # pyright: ignore[reportUnknownVariableType]
    return value


class DiskCache:
    """One JSON file per key. Outputs must be JSON values (images are media file names)."""

    def __init__(self, root: Path) -> None:
        self._root = root
        root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._root / f"{key.replace(':', '.')}.json"

    async def get(self, key: str) -> Outputs | None:
        path = self._path(key)
        return _decode(json.loads(path.read_text())) if path.exists() else None

    async def put(self, key: str, outputs: Outputs) -> None:
        self._path(key).write_text(json.dumps(_encode(dict(outputs))))
