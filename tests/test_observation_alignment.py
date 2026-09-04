"""VF-vNEXT-G3 — Observation context/provenance seam tests (A + F).

Proves (Issue #48): Observation legacy behavior remains compatible; the new
G1/G2 observation context seam carries workspace/scope/provenance ONLY when
explicitly supplied; it never fabricates G1/G2 identity for legacy callers and
never mutates the original envelope.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from virtual_factory.observation.alignment import (
    KEY_PROVENANCE,
    KEY_RUN_ID,
    KEY_SCOPE_PATH,
    KEY_WORKSPACE_ID,
    ObservationContextError,
    ObservationStructuralContext,
    carry_structural_context,
)
from virtual_factory.observation.envelope import (
    ObservationEnvelope,
    ObservationType,
    make_idempotency_key,
)
from virtual_factory.provenance import DataStatus, ProvenanceV2
from virtual_factory.workspace import StructuralPath


def _envelope() -> ObservationEnvelope:
    return ObservationEnvelope(
        observation_id="obs-00001",
        idempotency_key=make_idempotency_key(
            run_id="run-1", source_event_id="evt-001", point_id="ap04"
        ),
        observation_type=ObservationType.EVENT,
        run_id="run-1",
        model_id="tipa",
        simulation_time_s=12.5,
    )


def test_legacy_flow_unchanged_without_context() -> None:
    """No context -> same envelope, no fabricated vf.* identity."""
    env = _envelope()
    result = carry_structural_context(env, None)
    assert result is env
    assert KEY_WORKSPACE_ID not in env.context
    assert KEY_SCOPE_PATH not in env.context
    assert KEY_PROVENANCE not in env.context


def test_observation_envelope_is_immutable_downstream_fact() -> None:
    env = _envelope()
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        env.run_id = "other"  # type: ignore[misc]


def test_carries_explicit_structural_context() -> None:
    env = _envelope()  # envelope run_id = "run-1"
    ctx = ObservationStructuralContext(
        workspace_id="W",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
        run_id="run-1",  # MUST equal envelope.run_id (C01-1)
    )
    result = carry_structural_context(env, ctx)
    # A NEW envelope is returned; the original is never mutated.
    assert result is not env
    assert KEY_WORKSPACE_ID not in env.context
    assert result.context[KEY_WORKSPACE_ID] == "W"
    assert result.context[KEY_SCOPE_PATH] == "W/AREA/UNIT"
    assert result.context[KEY_RUN_ID] == "run-1"
    d = result.to_dict()
    assert d["context"][KEY_WORKSPACE_ID] == "W"
    # Existing observation identity is not collapsed or replaced.
    assert d["run_id"] == "run-1"
    assert d["model_id"] == "tipa"
    assert d["idempotency_key"].startswith("run-1|")


def test_context_run_id_mismatch_fails_closed() -> None:
    env = _envelope()  # envelope run_id = "run-1"
    ctx = ObservationStructuralContext(workspace_id="W", run_id="run-9")
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx)


def test_provenance_run_id_mismatch_fails_closed() -> None:
    env = _envelope()  # envelope run_id = "run-1"
    prov = ProvenanceV2(workspace_id="W", run_id="run-9")
    ctx = ObservationStructuralContext(workspace_id="W", provenance=prov)
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx)


def test_all_run_authorities_agree_when_context_and_provenance_present() -> None:
    env = _envelope()  # envelope run_id = "run-1"
    prov = ProvenanceV2(workspace_id="W", run_id="run-1")
    ctx = ObservationStructuralContext(
        workspace_id="W", run_id="run-1", provenance=prov
    )
    result = carry_structural_context(env, ctx)
    assert result.context[KEY_RUN_ID] == "run-1"
    assert result.context[KEY_PROVENANCE]["run_id"] == "run-1"


def test_reserved_key_conflict_fails_closed_not_silently_overwritten() -> None:
    env = _envelope()
    conflicting = replace(env, context={"vf.workspace_id": "OTHER"})
    ctx = ObservationStructuralContext(workspace_id="W")
    with pytest.raises(ObservationContextError):
        carry_structural_context(conflicting, ctx)


def test_reserved_key_same_value_is_allowed() -> None:
    env = _envelope()
    same = replace(env, context={"vf.workspace_id": "W"})
    ctx = ObservationStructuralContext(workspace_id="W")
    result = carry_structural_context(same, ctx)
    assert result.context[KEY_WORKSPACE_ID] == "W"


def test_context_is_fail_closed_on_workspace_mismatch() -> None:
    with pytest.raises(ObservationContextError):
        ObservationStructuralContext(
            workspace_id="W1",
            scope_path=StructuralPath(("W2", "AREA", "UNIT")),
        )
    provenance = ProvenanceV2(workspace_id="W2", run_id="run-1")
    with pytest.raises(ObservationContextError):
        ObservationStructuralContext(workspace_id="W1", provenance=provenance)


def test_context_requires_non_empty_workspace() -> None:
    with pytest.raises(ObservationContextError):
        ObservationStructuralContext(workspace_id="  ")


def test_carried_provenance_serialized_without_canonical_identity() -> None:
    env = _envelope()
    provenance = ProvenanceV2(
        workspace_id="W",
        run_id="run-1",
        data_status=DataStatus.SYNTHETIC,
    )
    ctx = ObservationStructuralContext(
        workspace_id="W",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
        provenance=provenance,
    )
    result = carry_structural_context(env, ctx)
    prov = result.context[KEY_PROVENANCE]
    assert prov["workspace_id"] == "W"
    assert prov["run_id"] == "run-1"
    assert prov["data_status"] == "synthetic"
    # No PIM canonical identity or evidence maturity is fabricated.
    assert "canonical_signal_id" not in prov
    assert "evidence" not in prov


def test_no_fabrication_when_scope_or_provenance_absent() -> None:
    env = _envelope()
    ctx = ObservationStructuralContext(workspace_id="W")
    result = carry_structural_context(env, ctx)
    assert result.context[KEY_WORKSPACE_ID] == "W"
    assert KEY_SCOPE_PATH not in result.context
    assert KEY_PROVENANCE not in result.context
