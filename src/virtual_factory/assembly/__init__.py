"""Assembly domain — reusable primitives for discrete material-flow modeling.

M3-S01: Domain vocabulary only. No TIPA hardcoding, no runtime handlers,
no topology loader, no KPI engine.

M6-S02: Indexed ASSY line runtime (carrier, conveyor, genealogy, upstream,
line_runtime).
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

# M6-S02 indexed line runtime
from virtual_factory.assembly.carrier import CarrierId, CarrierState, CarrierError
from virtual_factory.assembly.conveyor import (
    ConveyorConfig,
    ConveyorLine,
    ConveyorState,
    ConveyorError,
)
from virtual_factory.assembly.genealogy import (
    GenealogyRecord,
    GenealogyStore,
    GenealogyError,
)
from virtual_factory.assembly.upstream import (
    UpstreamConfig,
    UpstreamProducer,
    UpstreamWip,
)
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    AssyWipState,
    WipLifecycle,
    LineEvent,
    AssyLineError,
    load_assy_config_from_yaml,
)

# M6-S03 quality
from virtual_factory.assembly.quality_records import (
    QualityConfig,
    StationQualityConfig,
    QualityRecord,
    QualityHistory,
    QualityStatus,
    CheckType,
    MeasurementValue,
    resolve_quality_disposition,
)

__all__ = [
    # M3
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
    # M6-S02
    "CarrierId",
    "CarrierState",
    "CarrierError",
    "ConveyorConfig",
    "ConveyorLine",
    "ConveyorState",
    "ConveyorError",
    "GenealogyRecord",
    "GenealogyStore",
    "GenealogyError",
    "UpstreamConfig",
    "UpstreamProducer",
    "UpstreamWip",
    "AssyLineConfig",
    "AssyLineRuntime",
    "AssyWipState",
    "WipLifecycle",
    "LineEvent",
    "AssyLineError",
    "load_assy_config_from_yaml",
    # M6-S03
    "QualityConfig",
    "StationQualityConfig",
    "QualityRecord",
    "QualityHistory",
    "QualityStatus",
    "CheckType",
    "MeasurementValue",
    "resolve_quality_disposition",
]
