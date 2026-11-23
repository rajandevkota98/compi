"""Socket types: what kind of data flows along a wire between two nodes."""

from enum import StrEnum
from typing import Any


class Socket(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    IMAGE = "image"
    MASK = "mask"
    LIST = "list"
    ANY = "any"


def compatible(output: Socket, input_: Socket) -> bool:
    """True when an output socket may be wired into an input socket."""
    return output == input_ or Socket.ANY in (output, input_)


class Items(tuple[Any, ...]):
    """Values from an Iterator. A node fed Items runs once per item, except on `whole` inputs."""
