"""G3 additive seam: carry G1/G2 structural/provenance identity on observations.

ARCH-03 / Issue #48 (A + F): Observation remains an immutable downstream fact
derived from runtime truth. The existing consumer-neutral ``ObservationEnvelope``
is preserved byte-compatible. This module adds a minimal, explicit seam so NEW
platform observations can carry/reference G1 workspace identity, structural scope
path, and G2 provenance/run context — WITHOUT collapsing existing ``run_id``,
``model_id``, source identity, idempotency, or PIM canonical identity, and
WITHOUT fabricating workspace/scope/provenance for legacy callers.

When no explicit structural context is supplied, the envelope is returned
unchanged (legacy observation flows remain supported and unmodified).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from virtual_factory.observation.envelope import ObservationEnvelope
from virtual_factory.provenance.envelope import ProvenanceV2
from virtual_factory.workspace.identity import StructuralPath


class ObservationContextError(ValueError):
    """Raised when an observation context invariant is violated."""


# Reserved context keys (never collide with consumer payload fields).
KEY_WORKSPACE_ID = "vf.workspace_id"
KEY_SCOPE_PATH = "vf.scope_path"
KEY_RUN_ID = "vf.run_id"
KEY_PROVENANCE = "vf.provenance"


@dataclass(frozen=True, slots=True)
class ObservationStructuralContext:
    """Explicit, validated G1/G2 structural context that may ride on an observation.

    Every field is optional except ``workspace_id``; presence is always
    explicit. Identity consistency is fail-closed (a ``scope_path`` or
    ``provenance`` rooted in a different workspace than ``workspace_id`` is
    rejected). No value is ever fabricated here.
    """

    workspace_id: str
    scope_path: StructuralPath | None = None
    run_id: str | None = None
    provenance: ProvenanceV2 | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, str) or not self.workspace_id.strip():
            raise ObservationContextError("workspace_id must be a non-empty str")
        if self.scope_path is not None:
            if not isinstance(self.scope_path, StructuralPath):
                raise ObservationContextError(
                    f"scope_path must be StructuralPath, "
                    f"got {type(self.scope_path).__name__}"
                )
            if self.scope_path.workspace_id != self.workspace_id:
                raise ObservationContextError(
                    "scope_path.workspace_id must match workspace_id"
                )
        if self.provenance is not None:
            if not isinstance(self.provenance, ProvenanceV2):
                raise ObservationContextError(
                    f"provenance must be ProvenanceV2, "
                    f"got {type(self.provenance).__name__}"
                )
            if self.provenance.workspace_id != self.workspace_id:
                raise ObservationContextError(
                    "provenance.workspace_id must match workspace_id"
                )
        if self.run_id is not None and (
            not isinstance(self.run_id, str) or not self.run_id.strip()
        ):
            raise ObservationContextError("run_id must be a non-empty str")


def carry_structural_context(
    envelope: ObservationEnvelope,
    context: ObservationStructuralContext | None,
) -> ObservationEnvelope:
    """Return an observation carrying an explicit G1/G2 structural context.

    - ``context`` is ``None`` → the SAME envelope is returned unchanged (legacy:
      nothing is fabricated, nothing is mutated).
    - otherwise a NEW envelope is returned with the structural/provenance
      identity carried in its read-only ``context`` mapping under reserved
      ``vf.*`` keys. The input envelope is never mutated.

    This is a reference/carry seam only — it never renames or fabricates PIM
    canonical identity, and it never turns Observation into runtime authority.
    """
    if context is None:
        return envelope
    if not isinstance(envelope, ObservationEnvelope):
        raise ObservationContextError(
            f"envelope must be ObservationEnvelope, "
            f"got {type(envelope).__name__}"
        )

    extra: dict[str, Any] = {KEY_WORKSPACE_ID: context.workspace_id}
    if context.scope_path is not None:
        extra[KEY_SCOPE_PATH] = context.scope_path.as_string()
    if context.run_id is not None:
        extra[KEY_RUN_ID] = context.run_id
    if context.provenance is not None:
        extra[KEY_PROVENANCE] = context.provenance.to_dict()

    new_context: Mapping[str, Any] = dict(envelope.context)
    new_context = {**new_context, **extra}
    return replace(envelope, context=new_context)
