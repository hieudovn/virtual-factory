"""Assembly domain — reusable primitives for discrete material-flow modeling.

M3-S01: Domain vocabulary only. No TIPA hardcoding, no runtime handlers,
no topology loader, no KPI engine.
"""

from virtual_factory.assembly.primitives import (
    AssemblyPrimitive,
    Source,
    Buffer,
    Processor,
    Router,
    Sink,
    QualityGate,
    PrimitiveType,
)
from virtual_factory.assembly.wip import WipId, WipState, WipStatus
from virtual_factory.assembly.quality import QualityDisposition

__all__ = [
    "AssemblyPrimitive",
    "Source",
    "Buffer",
    "Processor",
    "Router",
    "Sink",
    "QualityGate",
    "PrimitiveType",
    "WipId",
    "WipState",
    "WipStatus",
    "QualityDisposition",
]
