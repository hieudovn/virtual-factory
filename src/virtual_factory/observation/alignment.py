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
            if (
                self.scope_path is not None
                and self.provenance.scope_path is not None
                and self.provenance.scope_path != self.scope_path
            ):
                raise ObservationContextError(
                    "provenance.scope_path must match scope_path"
                )
        if self.run_id is not None and (
            not isinstance(self.run_id, str) or not self.run_id.strip()
        ):
            raise ObservationContextError("run_id must be a non-empty str")


def _conflict(key: str, existing: Any, incoming: Any) -> None:
    """Raise a fail-closed conflict for a reserved vf.* key."""
    raise ObservationContextError(
        f"reserved context key {key!r} already holds {existing!r}; "
        f"conflicts with {incoming!r}"
    )


def _parse_scope_path(raw: object, what: str) -> StructuralPath:
    """Parse a canonical structural-path string (a present value must be valid)."""
    if not isinstance(raw, str) or not raw.strip():
        raise ObservationContextError(
            f"{what} must be a non-empty canonical structural-path string, "
            f"got {raw!r}"
        )
    try:
        return StructuralPath.from_string(raw)
    except Exception as exc:
        raise ObservationContextError(
            f"{what} is not a valid structural path: {raw!r}"
        ) from exc


def _validate_existing_provenance(
    prov_raw: Any,
    *,
    env_run_id: str,
    env_time_s: float,
    workspace_id: str,
    scope_authorities: list[StructuralPath],
) -> None:
    """Fail closed when pre-existing ``vf.provenance`` contradicts the frozen
    workspace/run/scope/time authorities (C03)."""
    if not isinstance(prov_raw, Mapping):
        raise ObservationContextError(
            "existing vf.provenance must be a serialized mapping"
        )
    if prov_raw.get("workspace_id") != workspace_id:
        _conflict(KEY_PROVENANCE, prov_raw.get("workspace_id"), workspace_id)
    if prov_raw.get("run_id") != env_run_id:
        _conflict(KEY_PROVENANCE, prov_raw.get("run_id"), env_run_id)
    prov_time = prov_raw.get("simulation_time_s")
    if prov_time is not None and prov_time != env_time_s:
        _conflict(KEY_PROVENANCE, prov_time, env_time_s)
    prov_scope_raw = prov_raw.get("scope_path")
    if prov_scope_raw is not None:
        prov_scope = _parse_scope_path(
            prov_scope_raw, "existing vf.provenance.scope_path"
        )
        if prov_scope.workspace_id != workspace_id:
            _conflict(
                KEY_PROVENANCE,
                prov_scope_raw,
                f"workspace {workspace_id!r}",
            )
        if scope_authorities and prov_scope != scope_authorities[0]:
            _conflict(
                KEY_PROVENANCE, prov_scope_raw, scope_authorities[0].as_string()
            )


def carry_structural_context(
    envelope: ObservationEnvelope,
    context: ObservationStructuralContext | None,
) -> ObservationEnvelope:
    """Return an observation carrying an explicit G1/G2 structural context.

    - ``context`` is ``None`` → the SAME envelope is returned unchanged (legacy:
      nothing is fabricated, nothing is mutated). C03 validation applies only
      when this carry/merge seam is explicitly invoked.
    - otherwise a NEW envelope is returned with the structural/provenance
      identity carried in its read-only ``context`` mapping under reserved
      ``vf.*`` keys. The input envelope is never mutated.

    Identity coherence is fail-closed (Issue #48 C01-1/C02-1/C03):

    - when ``context.run_id`` is present it MUST equal ``envelope.run_id``;
    - when ``context.provenance`` is present, its ``run_id``/``simulation_time_s``
      (when present) MUST equal the envelope's, and its workspace/scope must
      match the incoming workspace/scope;
    - BEFORE merging, the ENTIRE existing reserved ``vf.*`` state is validated
      against the authoritative envelope + incoming explicit context/provenance
      (C03): existing ``vf.workspace_id`` must equal the incoming workspace;
      existing ``vf.run_id`` must equal ``envelope.run_id`` (even when the
      incoming run_id is omitted); existing ``vf.scope_path`` must be a valid
      canonical path rooted in the same workspace and agree with every other
      present scope authority; existing ``vf.provenance`` must be structurally
      compatible with the same workspace/run/scope/time authorities. An omitted
      incoming optional field is NOT permission to retain stale contradictory
      reserved authority.

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

    env_run_id = envelope.run_id
    env_time_s = envelope.simulation_time_s
    ctx_workspace = context.workspace_id

    # --- Incoming explicit authority vs envelope (C01/C02) ---
    if context.run_id is not None and context.run_id != env_run_id:
        raise ObservationContextError(
            f"context.run_id {context.run_id!r} must equal "
            f"envelope.run_id {env_run_id!r}"
        )
    if context.provenance is not None:
        if context.provenance.run_id != env_run_id:
            raise ObservationContextError(
                f"provenance.run_id {context.provenance.run_id!r} must equal "
                f"envelope.run_id {env_run_id!r}"
            )
        if (
            context.provenance.simulation_time_s is not None
            and context.provenance.simulation_time_s != env_time_s
        ):
            raise ObservationContextError(
                f"provenance.simulation_time_s "
                f"{context.provenance.simulation_time_s!r} must equal "
                f"envelope.simulation_time_s {env_time_s!r}"
            )

    # --- Validate the ENTIRE existing reserved vf.* state (C03) ---
    existing = dict(envelope.context)

    if KEY_WORKSPACE_ID in existing and existing[KEY_WORKSPACE_ID] != ctx_workspace:
        _conflict(KEY_WORKSPACE_ID, existing[KEY_WORKSPACE_ID], ctx_workspace)

    if KEY_RUN_ID in existing and existing[KEY_RUN_ID] != env_run_id:
        _conflict(KEY_RUN_ID, existing[KEY_RUN_ID], env_run_id)

    # Every present scope authority must be a valid path rooted in the incoming
    # workspace, and all present scope authorities must agree.
    scope_authorities: list[StructuralPath] = []
    if KEY_SCOPE_PATH in existing:
        scope_authorities.append(
            _parse_scope_path(existing[KEY_SCOPE_PATH], "existing vf.scope_path")
        )
    if context.scope_path is not None:
        scope_authorities.append(context.scope_path)
    if (
        context.provenance is not None
        and context.provenance.scope_path is not None
    ):
        scope_authorities.append(context.provenance.scope_path)
    for sp in scope_authorities:
        if sp.workspace_id != ctx_workspace:
            raise ObservationContextError(
                f"scope authority {sp.as_string()!r} must be rooted in "
                f"workspace_id {ctx_workspace!r}"
            )
    distinct_scopes = {sp.as_string() for sp in scope_authorities}
    if len(distinct_scopes) > 1:
        raise ObservationContextError(
            "multiple scope authorities disagree: "
            + ", ".join(sorted(distinct_scopes))
        )

    if KEY_PROVENANCE in existing:
        _validate_existing_provenance(
            existing[KEY_PROVENANCE],
            env_run_id=env_run_id,
            env_time_s=env_time_s,
            workspace_id=ctx_workspace,
            scope_authorities=scope_authorities,
        )
    # Two provenance authorities both present and different -> fail closed (never
    # silently overwrite a differing pre-existing vf.provenance with incoming).
    if (
        context.provenance is not None
        and KEY_PROVENANCE in existing
        and existing[KEY_PROVENANCE] != context.provenance.to_dict()
    ):
        _conflict(KEY_PROVENANCE, existing[KEY_PROVENANCE], context.provenance.to_dict())

    # --- Merge: existing (fully validated) + incoming explicit values ---
    new_context = dict(existing)
    new_context[KEY_WORKSPACE_ID] = ctx_workspace
    if context.scope_path is not None:
        new_context[KEY_SCOPE_PATH] = context.scope_path.as_string()
    if context.run_id is not None:
        new_context[KEY_RUN_ID] = context.run_id
    if context.provenance is not None:
        new_context[KEY_PROVENANCE] = context.provenance.to_dict()

    return replace(envelope, context=new_context)
