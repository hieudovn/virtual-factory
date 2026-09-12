"""TIPA structural Workspace mapping (G5-A).

Builds the canonical G1 structural containment:

    Workspace "TIPA"
    └── Scope "ASSY"  (container-only)
        ├── ASSY-SL01 .. ASSY-SL03   (hydraulic, executable-capable)
        └── ASSY-SL04 .. ASSY-SL06   (thermal,  executable-capable)

Deterministic structural paths: ``TIPA/ASSY/ASSY-SLxx``.

G1 :class:`StructuralPath` is the runtime structural identity authority. The
TIPA demo deployment identity constants (``assembly.sub_line_identity``) are
reused ONLY to obtain the canonical sub-line ids; they are not turned into a new
generic platform identity model.

This module is additive and dependency-light: it depends only on the G1
workspace foundation and the frozen canonical id constants of the ASSY
sub-line identity module. It never fabricates PIM canonical identity.
"""

from __future__ import annotations

from virtual_factory.assembly.sub_line_identity import (
    CANONICAL_TIPA_SUB_LINE_IDS,
)
from virtual_factory.workspace import (
    ScopeMode,
    ScopeSpec,
    StructuralPath,
    Workspace,
    build_workspace,
)

PLANT_ID = "TIPA"
PRODUCTION_LINE_ID = "ASSY"

# Deterministic canonical sub-line ids (ASSY-SL01 .. ASSY-SL06).
SUB_LINE_IDS = tuple(sorted(CANONICAL_TIPA_SUB_LINE_IDS))


class FederationStructuralError(ValueError):
    """Raised when a TIPA structural mapping invariant is violated."""


def _validate_sub_line_id(sub_line_id: str) -> None:
    """A sub-line id must be one of the canonical TIPA ASSY sub-lines."""
    if sub_line_id not in CANONICAL_TIPA_SUB_LINE_IDS:
        raise FederationStructuralError(
            f"unknown TIPA ASSY sub-line id {sub_line_id!r}; "
            f"expected one of {sorted(CANONICAL_TIPA_SUB_LINE_IDS)}"
        )


def assy_scope_path() -> StructuralPath:
    """Structural path of the ASSY container scope (``TIPA/ASSY``)."""
    return StructuralPath((PLANT_ID, PRODUCTION_LINE_ID))


def sub_line_path(sub_line_id: str) -> StructuralPath:
    """Deterministic G1 structural path ``TIPA/ASSY/<sub_line_id>``.

    Fails closed for any non-canonical id.
    """
    _validate_sub_line_id(sub_line_id)
    return StructuralPath((PLANT_ID, PRODUCTION_LINE_ID, sub_line_id))


def build_tipa_workspace(
    *,
    display_name: str | None = None,
    description: str | None = None,
) -> Workspace:
    """Build the canonical TIPA Workspace -> ASSY -> six sub-line scopes.

    - ``ASSY`` is container-only and therefore owns no runtime participant.
    - ``ASSY-SL01..SL06`` are executable-capable child scopes.
    - The layout is validated by the G1 builder (deterministic regardless of
      iteration order); any structural violation fails closed.

    Raises ``StructuralValidationError`` on an invalid layout.
    """
    specs = [
        ScopeSpec(
            PRODUCTION_LINE_ID,
            ScopeMode.CONTAINER_ONLY,
            display_name="ASSY Line",
        )
    ]
    specs += [
        ScopeSpec(
            sub_line_id,
            ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=assy_scope_path(),
            display_name=sub_line_id,
        )
        for sub_line_id in SUB_LINE_IDS
    ]
    return build_workspace(
        PLANT_ID,
        specs,
        display_name=display_name or "TIPA Workspace",
        description=description
        or "Canonical TIPA ASSY federation containment (G5): "
        "TIPA -> ASSY (container) -> ASSY-SL01..SL06 (executable).",
    )
