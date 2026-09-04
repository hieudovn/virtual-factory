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

import json
from dataclasses import dataclass, replace
from typing import Any, Mapping

from virtual_factory.observation.envelope import ObservationEnvelope
from virtual_factory.provenance.envelope import ProvenanceV2
from virtual_factory.provenance.enums import DataStatus, Fidelity, OriginKind
from virtual_factory.workspace.identity import StructuralPath


class ObservationContextError(ValueError):
    """Raised when an observation context invariant is violated."""


# Reserved context keys (never collide with consumer payload fields).
# ``vf.provenance`` is carried as a canonical, immutable JSON string encoding of
# the G2 ``ProvenanceV2`` serialized dict (C04) — never a nested-mutable dict —
# so a completed Observation's provenance cannot be mutated after validation.
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
) -> str:
    """Fail closed when pre-existing ``vf.provenance`` is not a valid G2
    ``ProvenanceV2`` serialization or contradicts the frozen workspace/run/scope/
    time authorities (C03/C04). Returns the canonical immutable JSON encoding.

    A present reserved provenance must be a VALID ``ProvenanceV2`` serialization:
    it is rehydrated through the G2 enums/invariants exactly (no competing,
    weaker validator), so invalid truth labels such as ``origin_kind='measured'``,
    unsupported ``data_status``/``fidelity``, or malformed/missing fields fail
    closed. Optional fields are preserved; nothing is fabricated.
    """
    data = _coerce_existing_provenance(prov_raw)
    prov = _rehydrate_provenance(data)  # full G2 validation (no weaker semantics)
    if prov.workspace_id != workspace_id:
        _conflict(KEY_PROVENANCE, data.get("workspace_id"), workspace_id)
    if prov.run_id != env_run_id:
        _conflict(KEY_PROVENANCE, data.get("run_id"), env_run_id)
    if prov.simulation_time_s is not None and prov.simulation_time_s != env_time_s:
        _conflict(KEY_PROVENANCE, data.get("simulation_time_s"), env_time_s)
    if prov.scope_path is not None:
        if prov.scope_path.workspace_id != workspace_id:
            raise ObservationContextError(
                "existing vf.provenance scope_path must be rooted in "
                f"workspace_id {workspace_id!r}"
            )
        if scope_authorities and prov.scope_path != scope_authorities[0]:
            _conflict(
                KEY_PROVENANCE,
                data.get("scope_path"),
                scope_authorities[0].as_string(),
            )
    return _canonical_prov_json(prov.to_dict())


_PROVENANCE_SERIALIZED_KEYS = (
    "workspace_id",
    "run_id",
    "scope_path",
    "scenario_id",
    "origin_kind",
    "fidelity",
    "data_status",
    "semantic_contract_version",
    "semantic_contract_sha",
    "evidence_note",
    "simulation_time_s",
    "step",
)


def _canonical_prov_json(prov_dict: Mapping[str, Any]) -> str:
    """Deterministic, immutable canonical JSON encoding of a ``ProvenanceV2``
    serialized dict (the reserved ``vf.provenance`` value form)."""
    return json.dumps(dict(prov_dict), sort_keys=True, separators=(",", ":"))


def _coerce_existing_provenance(prov_raw: Any) -> dict[str, Any]:
    """Coerce the pre-existing reserved ``vf.provenance`` value to a dict.

    Accepts the canonical JSON-string form (immutable) or a plain serialized
    mapping; anything else fails closed.
    """
    if isinstance(prov_raw, str):
        try:
            parsed = json.loads(prov_raw)
        except Exception as exc:
            raise ObservationContextError(
                "existing vf.provenance is not valid canonical JSON"
            ) from exc
        if not isinstance(parsed, dict):
            raise ObservationContextError(
                "existing vf.provenance JSON must encode a mapping"
            )
        return parsed
    if isinstance(prov_raw, Mapping):
        return dict(prov_raw)
    raise ObservationContextError(
        "existing vf.provenance must be a serialized mapping or canonical JSON"
    )


def _rehydrate_provenance(data: Mapping[str, Any]) -> ProvenanceV2:
    """Reconstruct a G2 ``ProvenanceV2`` from its serialized dict, reusing the
    G2 enums/invariants exactly (no competing schema/validator).

    Raises ``ObservationContextError`` fail-closed when the mapping is not a
    faithful, valid ``ProvenanceV2`` serialization (e.g. ``origin_kind`` not
    simulation, unsupported ``data_status``/``fidelity``, invalid time/step,
    malformed or missing required fields, or unknown/extra keys). Optional
    fields are preserved as-is; nothing is fabricated.
    """
    try:
        raw_scope = data.get("scope_path")
        scope_path = (
            StructuralPath.from_string(raw_scope) if raw_scope is not None else None
        )
        prov = ProvenanceV2(
            workspace_id=data["workspace_id"],
            run_id=data["run_id"],
            scope_path=scope_path,
            scenario_id=data.get("scenario_id"),
            origin_kind=OriginKind(data["origin_kind"]),
            fidelity=(
                Fidelity(data["fidelity"])
                if data.get("fidelity") is not None
                else None
            ),
            data_status=(
                DataStatus(data["data_status"])
                if data.get("data_status") is not None
                else None
            ),
            semantic_contract_version=data.get("semantic_contract_version"),
            semantic_contract_sha=data.get("semantic_contract_sha"),
            evidence_note=data.get("evidence_note"),
            simulation_time_s=data.get("simulation_time_s"),
            step=data.get("step"),
        )
    except ObservationContextError:
        raise
    except Exception as exc:
        raise ObservationContextError(
            "existing vf.provenance is not a valid ProvenanceV2 serialization: "
            f"{exc}"
        ) from exc
    if set(data) != set(_PROVENANCE_SERIALIZED_KEYS):
        raise ObservationContextError(
            "existing vf.provenance must serialize exactly the ProvenanceV2 "
            "field set"
        )
    if prov.to_dict() != dict(data):
        raise ObservationContextError(
            "existing vf.provenance is not a faithful ProvenanceV2 serialization"
        )
    return prov


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
      present scope authority; existing ``vf.provenance`` must be a VALID G2
      ``ProvenanceV2`` serialization (rehydrated through the G2 enums/invariants
      — invalid truth labels/fields fail closed) AND structurally compatible
      with the same workspace/run/scope/time authorities (C04). An omitted
      incoming optional field is NOT permission to retain stale contradictory
      reserved authority.
    - ``vf.provenance`` is carried as an immutable canonical JSON string (C04):
      the resulting Observation's provenance is not a nested-mutable dict, so it
      cannot be mutated after validation; serialization stays deterministic and
      plain-data compatible (same G2 serialized dict, JSON-encoded).

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

    existing_prov_canonical: str | None = None
    if KEY_PROVENANCE in existing:
        existing_prov_canonical = _validate_existing_provenance(
            existing[KEY_PROVENANCE],
            env_run_id=env_run_id,
            env_time_s=env_time_s,
            workspace_id=ctx_workspace,
            scope_authorities=scope_authorities,
        )
    incoming_prov_canonical: str | None = None
    if context.provenance is not None:
        incoming_prov_canonical = _canonical_prov_json(
            context.provenance.to_dict()
        )
        if (
            existing_prov_canonical is not None
            and existing_prov_canonical != incoming_prov_canonical
        ):
            _conflict(
                KEY_PROVENANCE, existing[KEY_PROVENANCE], incoming_prov_canonical
            )

    # --- Merge: existing (fully validated) + incoming explicit values ---
    new_context = dict(existing)
    new_context[KEY_WORKSPACE_ID] = ctx_workspace
    if context.scope_path is not None:
        new_context[KEY_SCOPE_PATH] = context.scope_path.as_string()
    if context.run_id is not None:
        new_context[KEY_RUN_ID] = context.run_id
    if incoming_prov_canonical is not None:
        # immutable canonical encoding — no nested-mutable provenance leaf.
        new_context[KEY_PROVENANCE] = incoming_prov_canonical
    elif existing_prov_canonical is not None:
        # normalize any pre-existing provenance to the immutable canonical
        # encoding so the returned observation cannot be mutated afterwards.
        new_context[KEY_PROVENANCE] = existing_prov_canonical

    return replace(envelope, context=new_context)
