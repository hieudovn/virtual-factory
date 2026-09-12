"""VF-vNEXT-G2 — telemetry provenance threading tests.

Proves the additive G2 seam: policy-filtered signals are identical to the legacy
seam, provenance is deterministic and carried beside (never inside) SignalValue,
output-policy behavior is unchanged, legacy callers keep working, and no
canonical signal id is ever fabricated.
"""

from __future__ import annotations

from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine
from virtual_factory.provenance import (
    DataStatus,
    Fidelity,
    ProvenanceV2,
)
from virtual_factory.telemetry.telemetry_frame import (
    ProvenancedFrame,
    build_provenanced_frame,
    build_publishable_frame,
)
from virtual_factory.workspace import StructuralPath


def _engine():
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)
    engine.step()
    return config, engine


def test_provenanced_frame_is_additive_and_matches_legacy_signals() -> None:
    config, engine = _engine()
    provenance = ProvenanceV2(
        workspace_id="W",
        run_id="run-1",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
        scenario_id="scn-1",
        data_status=DataStatus.SYNTHETIC,
        fidelity=Fidelity.LOGICAL_ONLY,
    )

    legacy = build_publishable_frame(
        config, engine.state, engine.assembly.output_policy, timestamp_s=1.5
    )
    provenanced = build_provenanced_frame(
        config, engine.state, engine.assembly.output_policy, timestamp_s=1.5,
        provenance=provenance,
    )

    assert isinstance(provenanced, ProvenancedFrame)
    assert provenanced.provenance is provenance
    # Same policy-filtered signals, same order, same fields.
    assert provenanced.signal_values() == legacy


def test_provenance_is_deterministic() -> None:
    config, engine = _engine()
    provenance = ProvenanceV2(
        workspace_id="W", run_id="run-1", data_status=DataStatus.SYNTHETIC
    )
    f1 = build_provenanced_frame(
        config, engine.state, engine.assembly.output_policy, timestamp_s=2.0,
        provenance=provenance,
    )
    f2 = build_provenanced_frame(
        config, engine.state, engine.assembly.output_policy, timestamp_s=2.0,
        provenance=provenance,
    )
    assert f1.to_dict() == f2.to_dict()


def test_output_policy_behavior_unchanged() -> None:
    config, engine = _engine()
    provenance = ProvenanceV2(workspace_id="W", run_id="run-1")
    provenanced = build_provenanced_frame(
        config, engine.state, engine.assembly.output_policy, timestamp_s=0.0,
        provenance=provenance,
    )
    categories = {s.category for s in provenanced.signals}
    # internal_truth never leaks through the policy in the G2 seam either.
    assert "internal_truth" not in categories


def test_no_fabricated_canonical_signal_id_and_per_signal_runtime_id() -> None:
    config, engine = _engine()
    provenance = ProvenanceV2(
        workspace_id="W",
        run_id="run-1",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
    )
    provenanced = build_provenanced_frame(
        config, engine.state, engine.assembly.output_policy, timestamp_s=0.0,
        provenance=provenance,
    )
    records = provenanced.to_records()
    assert len(records) >= 2
    seen: set[str] = set()
    for record in records:
        prov = record["provenance"]
        assert "canonical_signal_id" not in prov
        runtime_id = prov["runtime_signal_id"]
        # Per-signal identity derives from the signal's own name — never one
        # frame-level value duplicated across all signals.
        assert runtime_id == f"W/AREA/UNIT/{record['name']}"
        assert runtime_id not in seen
        seen.add(runtime_id)


def test_distinct_signals_do_not_share_fabricated_runtime_identity() -> None:
    """Multi-signal proof: a frame with many signals must not stamp one
    fabricated frame-level runtime identity onto all of them."""
    config, engine = _engine()
    provenance = ProvenanceV2(workspace_id="W", run_id="run-1")
    provenanced = build_provenanced_frame(
        config, engine.state, engine.assembly.output_policy, timestamp_s=0.0,
        provenance=provenance,
    )
    records = provenanced.to_records()
    runtime_ids = [r["provenance"]["runtime_signal_id"] for r in records]
    assert len(runtime_ids) >= 2
    assert len(set(runtime_ids)) == len(runtime_ids)
    # The common run/frame provenance is still shared by every record.
    for record in records:
        prov = record["provenance"]
        assert prov["workspace_id"] == "W"
        assert prov["run_id"] == "run-1"


def test_legacy_seam_remains_plain_signal_list() -> None:
    """Legacy callers get a plain list[SignalValue] — no provenance fabricated."""
    config, engine = _engine()
    frame = build_publishable_frame(
        config, engine.state, engine.assembly.output_policy, timestamp_s=0.0
    )
    assert isinstance(frame, list)
    for item in frame:
        assert not hasattr(item, "provenance")
