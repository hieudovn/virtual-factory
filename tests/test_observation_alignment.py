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


def test_reserved_key_present_none_conflicts_with_new_value() -> None:
    """Key PRESENCE is used: a present reserved key whose value is None is still
    a pre-existing key and must not be silently overwritten (C02-2)."""
    env = _envelope()
    present_none = replace(env, context={"vf.workspace_id": None})
    ctx = ObservationStructuralContext(workspace_id="W")
    with pytest.raises(ObservationContextError):
        carry_structural_context(present_none, ctx)


def test_scope_vs_provenance_scope_mismatch_fails_closed() -> None:
    provenance = ProvenanceV2(
        workspace_id="W",
        run_id="run-1",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
    )
    with pytest.raises(ObservationContextError):
        ObservationStructuralContext(
            workspace_id="W",
            scope_path=StructuralPath(("W", "AREA", "OTHER")),  # conflicts
            provenance=provenance,
        )


def test_provenance_simulation_time_mismatch_fails_closed() -> None:
    env = _envelope()  # envelope simulation_time_s = 12.5
    provenance = ProvenanceV2(
        workspace_id="W", run_id="run-1", simulation_time_s=13.5
    )
    ctx = ObservationStructuralContext(workspace_id="W", provenance=provenance)
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx)


def test_all_scope_run_time_authorities_agree() -> None:
    env = _envelope()  # run_id=run-1, simulation_time_s=12.5
    provenance = ProvenanceV2(
        workspace_id="W",
        run_id="run-1",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
        simulation_time_s=12.5,
    )
    ctx = ObservationStructuralContext(
        workspace_id="W",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
        run_id="run-1",
        provenance=provenance,
    )
    result = carry_structural_context(env, ctx)
    assert result.context[KEY_SCOPE_PATH] == "W/AREA/UNIT"
    assert result.context[KEY_RUN_ID] == "run-1"
    assert result.context[KEY_PROVENANCE]["scope_path"] == "W/AREA/UNIT"
    assert result.context[KEY_PROVENANCE]["simulation_time_s"] == 12.5


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


# ═══════════════════════════════════════════════════════════════════
# C03 + self-audit: validate the ENTIRE pre-existing reserved vf.* state
# Matrix: envelope field / pre-existing vf.* / incoming context-provenance.
# Any two present authorities that differ must fail closed. No fabricated value.
# ═══════════════════════════════════════════════════════════════════

def _prov(workspace_id="W", run_id="run-1", scope=None, time_s=None, **kw):
    kwargs: dict = {"workspace_id": workspace_id, "run_id": run_id}
    if scope is not None:
        kwargs["scope_path"] = scope
    if time_s is not None:
        kwargs["simulation_time_s"] = time_s
    kwargs.update(kw)
    return ProvenanceV2(**kwargs)


# ── workspace ──────────────────────────────────────────────────────

def test_existing_vf_workspace_must_match_incoming_workspace() -> None:
    env = replace(_envelope(), context={"vf.workspace_id": "W"})
    ctx = ObservationStructuralContext(workspace_id="W2")
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx)


def test_existing_vf_provenance_workspace_conflict_fails_closed() -> None:
    env = replace(
        _envelope(), context={"vf.provenance": _prov(workspace_id="W2").to_dict()}
    )
    ctx = ObservationStructuralContext(workspace_id="W")
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx)


# ── run_id ─────────────────────────────────────────────────────────

def test_existing_vf_run_id_conflicts_when_incoming_omits_run() -> None:
    """C03: incoming run_id omitted must NOT retain stale contradictory vf.run_id."""
    env = replace(_envelope(), context={"vf.run_id": "run-9"})  # != envelope run-1
    ctx = ObservationStructuralContext(workspace_id="W")  # run_id omitted
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx)


def test_existing_vf_run_id_coherent_when_incoming_omits_run_is_accepted() -> None:
    env = replace(_envelope(), context={"vf.run_id": "run-1"})  # == envelope
    ctx = ObservationStructuralContext(workspace_id="W")  # run_id omitted
    result = carry_structural_context(env, ctx)
    assert result.context[KEY_RUN_ID] == "run-1"
    assert result.context[KEY_WORKSPACE_ID] == "W"


def test_existing_vf_provenance_run_id_conflict_fails_closed() -> None:
    env = replace(
        _envelope(), context={"vf.provenance": _prov(run_id="run-9").to_dict()}
    )
    ctx = ObservationStructuralContext(workspace_id="W")
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx)


# ── scope_path ─────────────────────────────────────────────────────

def test_existing_vf_scope_path_conflicts_via_incoming_provenance_scope() -> None:
    """C03: existing scope retained while provenance supplies another -> fail."""
    env = replace(_envelope(), context={"vf.scope_path": "W/AREA/OTHER"})
    prov = _prov(scope=StructuralPath(("W", "AREA", "UNIT")))
    ctx = ObservationStructuralContext(workspace_id="W", provenance=prov)
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx)


def test_existing_vf_scope_path_must_be_rooted_in_workspace() -> None:
    env = replace(_envelope(), context={"vf.scope_path": "W2/AREA"})
    ctx = ObservationStructuralContext(workspace_id="W")
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx)


def test_existing_vf_scope_path_must_be_valid_structural_path() -> None:
    env = replace(_envelope(), context={"vf.scope_path": "W//AREA"})
    ctx = ObservationStructuralContext(workspace_id="W")
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx)


def test_existing_vf_scope_path_coherent_is_accepted_when_incoming_omits_scope() -> None:
    env = replace(_envelope(), context={"vf.scope_path": "W/AREA/UNIT"})
    ctx = ObservationStructuralContext(workspace_id="W")  # scope omitted
    result = carry_structural_context(env, ctx)
    assert result.context[KEY_SCOPE_PATH] == "W/AREA/UNIT"


def test_existing_vf_provenance_scope_conflict_fails_closed() -> None:
    env = replace(
        _envelope(),
        context={
            "vf.provenance": _prov(
                scope=StructuralPath(("W", "AREA", "OTHER"))
            ).to_dict()
        },
    )
    prov = _prov(scope=StructuralPath(("W", "AREA", "UNIT")))
    ctx = ObservationStructuralContext(workspace_id="W", provenance=prov)
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx)


# ── simulation_time_s (carried in provenance) ──────────────────────

def test_existing_vf_provenance_time_conflict_fails_closed() -> None:
    env = replace(
        _envelope(), context={"vf.provenance": _prov(time_s=13.5).to_dict()}
    )  # != envelope 12.5
    ctx = ObservationStructuralContext(workspace_id="W")
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx)


def test_existing_vf_provenance_time_coherent_is_accepted() -> None:
    env = replace(
        _envelope(), context={"vf.provenance": _prov(time_s=12.5).to_dict()}
    )  # == envelope
    ctx = ObservationStructuralContext(workspace_id="W")
    result = carry_structural_context(env, ctx)
    assert result.context[KEY_PROVENANCE]["simulation_time_s"] == 12.5


# ── provenance (whole authority) ───────────────────────────────────

def test_existing_vf_provenance_must_equal_incoming_provenance_when_both_present() -> None:
    prov = _prov(scope=StructuralPath(("W", "AREA", "UNIT")), time_s=12.5)
    env = replace(_envelope(), context={"vf.provenance": prov.to_dict()})
    ctx = ObservationStructuralContext(
        workspace_id="W",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
        provenance=prov,
    )
    result = carry_structural_context(env, ctx)
    assert result.context[KEY_PROVENANCE] == prov.to_dict()
    # A DIFFERING incoming provenance must not silently overwrite the existing one.
    other = _prov(
        scope=StructuralPath(("W", "AREA", "UNIT")),
        time_s=12.5,
        data_status=DataStatus.SIMULATED_GROUND_TRUTH,
    )
    ctx2 = ObservationStructuralContext(workspace_id="W", provenance=other)
    with pytest.raises(ObservationContextError):
        carry_structural_context(env, ctx2)


# ── coherent full existing state + legacy ──────────────────────────

def test_coherent_full_existing_reserved_state_is_accepted() -> None:
    prov = _prov(scope=StructuralPath(("W", "AREA", "UNIT")), time_s=12.5)
    env = replace(
        _envelope(),
        context={
            "vf.workspace_id": "W",
            "vf.run_id": "run-1",
            "vf.scope_path": "W/AREA/UNIT",
            "vf.provenance": prov.to_dict(),
        },
    )
    ctx = ObservationStructuralContext(
        workspace_id="W",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
        run_id="run-1",
        provenance=prov,
    )
    result = carry_structural_context(env, ctx)
    assert result.context[KEY_WORKSPACE_ID] == "W"
    assert result.context[KEY_RUN_ID] == "run-1"
    assert result.context[KEY_SCOPE_PATH] == "W/AREA/UNIT"
    assert result.context[KEY_PROVENANCE] == prov.to_dict()


def test_coherent_existing_provenance_retained_when_incoming_omits() -> None:
    prov = _prov(scope=StructuralPath(("W", "AREA", "UNIT")), time_s=12.5)
    env = replace(
        _envelope(),
        context={
            "vf.workspace_id": "W",
            "vf.run_id": "run-1",
            "vf.scope_path": "W/AREA/UNIT",
            "vf.provenance": prov.to_dict(),
        },
    )
    ctx = ObservationStructuralContext(
        workspace_id="W",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
        run_id="run-1",
    )  # provenance omitted
    result = carry_structural_context(env, ctx)
    assert result.context[KEY_PROVENANCE] == prov.to_dict()


def test_legacy_context_none_returns_same_envelope_even_with_reserved_state() -> None:
    """C03 applies only when the carry/merge seam is explicitly invoked."""
    env = replace(_envelope(), context={"vf.run_id": "run-9"})
    result = carry_structural_context(env, None)
    assert result is env
