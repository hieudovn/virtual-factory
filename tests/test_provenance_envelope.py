"""VF-vNEXT-G2 — Provenance v2 envelope tests.

Proves: immutability, deterministic serialization, fail-closed simulation truth
labels (origin_kind / data_status / fidelity), semantic pins are opaque +
immutable (no PIM validation), and runtime_signal_id is distinct from any
canonical id (which G2 does not fabricate).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from virtual_factory.provenance import (
    DataStatus,
    Fidelity,
    OriginKind,
    ProvenanceError,
    ProvenanceV2,
)
from virtual_factory.workspace import StructuralPath


def test_envelope_immutable() -> None:
    env = ProvenanceV2(workspace_id="W", run_id="run-1")
    with pytest.raises(FrozenInstanceError):
        env.run_id = "run-2"  # type: ignore[misc]


def test_origin_kind_is_simulation_fail_closed() -> None:
    env = ProvenanceV2(workspace_id="W", run_id="run-1")
    assert env.origin_kind is OriginKind.SIMULATION
    # origin_kind cannot become plant measurement truth.
    with pytest.raises(ProvenanceError):
        ProvenanceV2(workspace_id="W", run_id="run-1", origin_kind="measured")  # type: ignore[arg-type]


def test_only_allowed_data_status_and_fidelity_accepted() -> None:
    env = ProvenanceV2(
        workspace_id="W",
        run_id="run-1",
        data_status=DataStatus.SYNTHETIC,
        fidelity=Fidelity.LOGICAL_ONLY,
    )
    assert env.data_status is DataStatus.SYNTHETIC
    assert env.fidelity is Fidelity.LOGICAL_ONLY
    # Plain "measured"/"ground_truth" is not an allowed data_status.
    with pytest.raises((ValueError, ProvenanceError)):
        DataStatus("measured")  # type: ignore[misc]
    with pytest.raises((ValueError, ProvenanceError)):
        ProvenanceV2(workspace_id="W", run_id="run-1", data_status="measured")  # type: ignore[arg-type]


def test_semantic_pins_are_opaque_immutable_and_serialized() -> None:
    env = ProvenanceV2(
        workspace_id="W",
        run_id="run-1",
        semantic_contract_version="v0.1",
        semantic_contract_sha="abc123",
        evidence_note="synthetic demo run",
    )
    d = env.to_dict()
    assert d["semantic_contract_version"] == "v0.1"
    assert d["semantic_contract_sha"] == "abc123"
    assert d["evidence_note"] == "synthetic demo run"
    # G2 does not validate PIM ownership of these pins (G9 owns that).
    # Pins are frozen fields; a second serialization is byte-identical.
    assert env.to_dict() == d


def test_runtime_signal_id_distinct_from_canonical_and_not_fabricated() -> None:
    env = ProvenanceV2(
        workspace_id="W",
        run_id="run-1",
        runtime_signal_id="W.UNIT-1.FT-101",
    )
    assert env.runtime_signal_id == "W.UNIT-1.FT-101"
    # There is NO canonical_signal_id field; VF never fabricates one.
    assert not hasattr(env, "canonical_signal_id")
    assert "canonical_signal_id" not in env.to_dict()


def test_missing_required_identity_fails_closed() -> None:
    with pytest.raises(ProvenanceError):
        ProvenanceV2(workspace_id="", run_id="run-1")
    with pytest.raises(ProvenanceError):
        ProvenanceV2(workspace_id="W", run_id="  ")


def test_scope_path_serialization() -> None:
    env = ProvenanceV2(
        workspace_id="W",
        run_id="run-1",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
    )
    assert env.to_dict()["scope_path"] == "W/AREA/UNIT"


def test_invalid_time_and_step_fail_closed() -> None:
    with pytest.raises(ProvenanceError):
        ProvenanceV2(workspace_id="W", run_id="run-1", simulation_time_s=-1.0)
    with pytest.raises(ProvenanceError):
        ProvenanceV2(workspace_id="W", run_id="run-1", step=-1)
