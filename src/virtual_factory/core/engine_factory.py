"""Engine factory — resolve engine type and create engines.

This module is the single construction seam for simulation engines.
All CLI/API engine creation should route through this factory.

Per SA-ADR-017:
- Legacy configs with no discriminator default to ``continuous_process``.
- Unsupported engine types raise a typed error.
- No schema changes are required for legacy configs.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from virtual_factory.core.engine_contract import SimulationEngineProtocol


class UnsupportedEngineError(ValueError):
    """Raised when the requested engine type is not supported."""


def resolve_engine_kind(config: Any) -> str:
    """Determine the engine kind from a loaded configuration.

    Resolution order:
    1. Top-level ``model_type`` field if present.
    2. Default: ``"continuous_process"`` for backward compatibility.

    Args:
        config: A loaded plant configuration (Pydantic model or dict).

    Returns:
        An engine-kind string, currently always ``"continuous_process"``.

    Raises:
        UnsupportedEngineError: If the resolved kind is not supported.
    """
    # Check for a top-level model_type discriminator
    model_type = _safe_get_attr(config, "model_type")

    if model_type is not None:
        kind = str(model_type)
        if kind not in _SUPPORTED_KINDS:
            raise UnsupportedEngineError(
                f"Unsupported engine kind: {kind!r}. "
                f"Supported: {sorted(_SUPPORTED_KINDS)}"
            )
        return kind

    # Legacy default
    return "continuous_process"


def create_engine(
    config: Any,
    *,
    dt_s: float = 1.0,
    scenario: Any | None = None,
) -> SimulationEngineProtocol:
    """Create a simulation engine from a loaded configuration.

    Args:
        config: A loaded plant configuration.
        dt_s: Simulation tick duration in seconds.
        scenario: Optional scenario configuration.

    Returns:
        An engine satisfying ``SimulationEngineProtocol``.

    Raises:
        UnsupportedEngineError: If the resolved engine kind is not
            supported in the current build.
    """
    kind = resolve_engine_kind(config)

    if kind == "continuous_process":
        # Deferred import avoids circular dependency with engine_contract.
        from virtual_factory.core.simulation_engine import SimulationEngine

        return SimulationEngine(config, dt_s=dt_s, scenario=scenario)

    raise UnsupportedEngineError(
        f"Engine kind {kind!r} is recognized but has no implementation."
    )


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

_SUPPORTED_KINDS: set[str] = {"continuous_process"}


def _safe_get_attr(obj: Any, name: str) -> Any | None:
    """Safely get a key or attribute from a config object.

    Mapping-like objects (including dict) use ``.get(name)``.
    Other objects use ``getattr(obj, name, None)``.

    Does NOT catch all exceptions — genuine access errors propagate.
    """
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)
