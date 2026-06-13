"""Typed port declarations for configured model interaction."""

from dataclasses import dataclass
from typing import Literal

PortKind = Literal["physical", "measurement", "signal", "command", "publication"]


@dataclass(frozen=True, slots=True)
class Port:
    """A typed interface exposed by a configured model node."""

    name: str
    kind: PortKind
    variable: str | None = None
    unit: str | None = None
    direction: Literal["in", "out", "inout"] = "inout"
