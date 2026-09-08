"""VF-vNEXT-G13 — SH-WTP T108 standalone synthetic first-order runtime tests.

Proves (Issue #61 required tests): exact T108 target, only-T108 implementation,
explicit config inputs, deterministic initial state + repeated scenario, mass
balance, fill/drain/empty-saturation/overflow, level=volume/area, reset, attempt
isolation, invalid-config fail closed, synthetic first-order provenance, no
site-truth labels, no G12B relation projection, no G4/BoundaryPort/coordinator,
T106 unimplemented, T110 blocked, workspace/container target not enabled.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import pytest

from virtual_factory.provenance import (
    DataStatus,
    Fidelity,
    OriginKind,
    RunContextV2,
)
from virtual_factory.shwtp import (
    SHWTP_T108_CANONICAL_ID,
    SHWTP_T108_SCOPE_PATH,
    T108Config,
    T108RuntimeError,
    T108TankRuntime,
)
from virtual_factory.shwtp import runtime as rt_module
from virtual_factory.workspace import StructuralPath

ADMISSION_PATH = (
    Path(__file__).resolve().parent.parent
    / "configs"
    / "vnext"
    / "shwtp"
    / "shwtp_synthetic_runtime_admission.json"
)


def _config(**overrides) -> T108Config:
    kwargs = dict(
        capacity_m3=100.0,
        tank_area_m2=10.0,
        initial_volume_m3=50.0,
        dt_s=1.0,
    )
    kwargs.update(overrides)
    return T108Config(**kwargs)


def _ctx(scope_path=SHWTP_T108_SCOPE_PATH, *, workspace_id="shwtp", run_id="run-1"):
    return RunContextV2(
        workspace_id=workspace_id,
        run_id=run_id,
        scope_path=scope_path,
        scenario_id="scn-1",
    )


def _runtime(**overrides) -> T108TankRuntime:
    return T108TankRuntime(_config(**overrides), _ctx())


def _module_code(module) -> str:
    return re.sub(r'""".*?"""', "", inspect.getsource(module), flags=re.DOTALL)


class TestTarget:
    def test_exact_t108_target_preserved(self):
        assert SHWTP_T108_CANONICAL_ID == "UNIT-SHW-L1-T108"
        assert SHWTP_T108_SCOPE_PATH == StructuralPath(("shwtp", "line1", "l1_t108"))
        rt = _runtime()
        assert rt.canonical_id == "UNIT-SHW-L1-T108"
        assert rt.scope_path == SHWTP_T108_SCOPE_PATH

    def test_only_t108_implemented(self):
        code = _module_code(rt_module)
        for token in (
            "T106Runtime",
            "T110Runtime",
            "SHWTP_T106_CANONICAL_ID",
            "SHWTP_T110_CANONICAL_ID",
        ):
            assert token not in code

    def test_workspace_and_container_targets_not_enabled(self):
        with pytest.raises(T108RuntimeError):
            T108TankRuntime(_config(), _ctx(scope_path=StructuralPath(("shwtp",))))
        with pytest.raises(T108RuntimeError):
            T108TankRuntime(
                _config(), _ctx(scope_path=StructuralPath(("shwtp", "line1")))
            )
        with pytest.raises(T108RuntimeError):
            T108TankRuntime(_config(), _ctx(scope_path=None))
        with pytest.raises(T108RuntimeError):
            T108TankRuntime(
                _config(),
                RunContextV2(workspace_id="other", run_id="r", scope_path=None),
            )


class TestConfig:
    def test_all_inputs_are_explicit_no_defaults(self):
        sig = inspect.signature(T108Config)
        for name in ("capacity_m3", "tank_area_m2", "initial_volume_m3", "dt_s"):
            assert sig.parameters[name].default is inspect.Parameter.empty

    def test_invalid_config_fails_closed(self):
        for bad in (
            dict(capacity_m3=0.0),
            dict(capacity_m3=-1.0),
            dict(tank_area_m2=0.0),
            dict(tank_area_m2=-5.0),
            dict(dt_s=0.0),
            dict(dt_s=-1.0),
            dict(initial_volume_m3=-0.1),
            dict(initial_volume_m3=101.0),  # > capacity
        ):
            with pytest.raises(T108RuntimeError):
                _config(**bad)

    def test_negative_step_inputs_fail_closed(self):
        rt = _runtime()
        with pytest.raises(T108RuntimeError):
            rt.step(-0.1, 0.0)
        with pytest.raises(T108RuntimeError):
            rt.step(0.0, -0.1)


class TestDeterminism:
    def test_initial_state_deterministic(self):
        a = _runtime()
        b = _runtime()
        assert a.state == b.state
        assert a.state.time_s == 0.0
        assert a.state.volume_m3 == 50.0
        assert a.state.level_m == pytest.approx(5.0)

    def test_repeated_scenario_identical(self):
        def run():
            rt = _runtime()
            records = []
            for qin, qout in ((1.0, 0.5), (2.0, 0.0), (0.0, 3.0)):
                rec = rt.step(qin, qout)
                records.append(
                    (
                        rec.end_time_s,
                        rec.end_volume_m3,
                        rec.end_level_m,
                        rec.applied_outflow_m3_s,
                        rec.overflow_m3,
                    )
                )
            return records

        assert run() == run()


class TestStepSemantics:
    def test_mass_balance_closes(self):
        rt = _runtime()
        start = rt.state
        rec = rt.step(2.0, 0.5)
        expected = (
            start.volume_m3
            + 2.0 * rt.config.dt_s
            - rec.applied_outflow_m3_s * rt.config.dt_s
            - rec.overflow_m3
        )
        assert rec.end_volume_m3 == pytest.approx(expected, rel=1e-9)

    def test_fill_increases_level(self):
        rt = _runtime()
        before = rt.state.level_m
        rt.step(5.0, 0.0)
        assert rt.state.level_m > before

    def test_drain_decreases_level(self):
        rt = _runtime()
        before = rt.state.level_m
        rt.step(0.0, 2.0)
        assert rt.state.level_m < before

    def test_empty_tank_saturation_never_negative(self):
        rt = _runtime(initial_volume_m3=0.0)
        rec = rt.step(0.0, 5.0)
        assert rec.applied_outflow_m3_s == pytest.approx(0.0)
        assert rec.end_volume_m3 == pytest.approx(0.0)
        assert rec.end_volume_m3 >= 0.0
        assert rt.state.volume_m3 == pytest.approx(0.0)

    def test_overflow_explicit_not_silent(self):
        rt = _runtime(initial_volume_m3=99.0)
        rec = rt.step(5.0, 0.0)
        assert rec.overflow_m3 == pytest.approx(4.0)
        assert rec.end_volume_m3 == pytest.approx(100.0)
        assert rt.state.volume_m3 == pytest.approx(100.0)

    def test_level_equals_volume_over_area(self):
        rt = _runtime()
        rt.step(1.0, 0.0)
        assert rt.state.level_m == pytest.approx(rt.state.volume_m3 / 10.0)

    def test_outflow_limited_by_available_inventory(self):
        rt = _runtime(initial_volume_m3=1.0, dt_s=1.0)
        rec = rt.step(0.0, 10.0)  # demand > available
        assert rec.applied_outflow_m3_s == pytest.approx(1.0)
        assert rec.end_volume_m3 == pytest.approx(0.0)


class TestLifecycle:
    def test_reset_restores_initial_within_same_attempt(self):
        rt = _runtime()
        rt.step(5.0, 0.0)
        rt.step(0.0, 2.0)
        assert rt.state.time_s > 0.0
        rt.reset()
        assert rt.state.time_s == 0.0
        assert rt.state.volume_m3 == pytest.approx(50.0)
        assert rt.state.level_m == pytest.approx(5.0)
        assert rt.step_index == 0

    def test_fresh_attempts_isolated(self):
        a = _runtime()
        b = _runtime()
        a.step(5.0, 0.0)
        assert b.state.volume_m3 == pytest.approx(50.0)
        assert a.state.volume_m3 != b.state.volume_m3


class TestProvenance:
    def test_provenance_simulation_synthetic_first_order(self):
        rt = _runtime()
        rec = rt.step(1.0, 0.0)
        prov = rec.provenance
        assert prov.origin_kind is OriginKind.SIMULATION
        assert prov.data_status is DataStatus.SYNTHETIC
        assert prov.fidelity is Fidelity.FIRST_ORDER
        assert prov.workspace_id == "shwtp"
        assert prov.scope_path == SHWTP_T108_SCOPE_PATH

    def test_no_site_or_measurement_labels(self):
        rt = _runtime()
        rec = rt.step(1.0, 0.0)
        blob = json.dumps(rec.provenance.to_dict()).lower()
        for token in ("measured", "site", "siteverified", "sourcemapped", "calibrated"):
            assert token not in blob
        assert rec.provenance.fidelity.value == "first_order"
        assert rec.provenance.data_status.value == "synthetic"

    def test_snapshot_is_detached(self):
        rt = _runtime()
        snap = rt.snapshot()
        rt.step(5.0, 0.0)
        # snapshot captured before the step is unchanged
        assert snap.volume_m3 == pytest.approx(50.0)
        assert rt.state.volume_m3 != snap.volume_m3


class TestNoProjection:
    def test_no_g12b_relation_runtime_projected(self):
        code = _module_code(rt_module)
        for token in (
            "FLOWS_TO",
            "DISCHARGES_TO",
            "CONNECTED_TO",
            "CompositionBinding",
            "BoundaryPort",
        ):
            assert token not in code

    def test_no_g4_or_runtime_module_imports(self):
        code = _module_code(rt_module)
        for token in (
            "from virtual_factory.composition",
            "from virtual_factory.runcontrol",
            "from virtual_factory.equipment",
        ):
            assert token not in code
        for name in (
            "BoundaryPort",
            "PortDirection",
            "PortCategory",
            "CompositionBinding",
            "Coordinator",
            "RunLifecycleService",
        ):
            assert name not in vars(rt_module)


class TestAdmissionAlignment:
    def test_admission_authority_preserved(self):
        admission = json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))
        authority = admission["authority"]
        assert authority["review_status"] == "COMPLETE"
        assert authority["authorization_mode"] == "CANDIDATE_SCOPED"
        assert authority["first_authorized_slice"] == ["UNIT-SHW-L1-T108"]
        assert "UNIT-SHW-WASH-T110" in authority["blocked_candidates"]
        assert authority["vf_runtime_authorization"] == "NOT_AUTHORIZED"
        assert authority["site_authorized_execution"] == "NOT_AUTHORIZED"

    def test_t106_later_optional_t110_blocked(self):
        admission = json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))
        authority = admission["authority"]
        assert authority["authorized_candidates"] == [
            "UNIT-SHW-L1-T106",
            "UNIT-SHW-L1-T108",
        ]
        # G13 implements only T108; T106 is later/optional, T110 blocked
        plan = admission["g13_authorization_plan"]
        assert plan["first_authorized_slice"] == ["UNIT-SHW-L1-T108"]
        assert plan["blocked_candidates"] == ["UNIT-SHW-WASH-T110"]


class TestC01Corrections:
    """G13-C01: locked T108 canonical reference + snapshot provenance."""

    def test_canonical_reference_locked_to_t108(self):
        # no caller override remains
        params = inspect.signature(T108TankRuntime.__init__).parameters
        assert "canonical_id" not in params
        rt = _runtime()
        assert rt.canonical_id == "UNIT-SHW-L1-T108"
        rec = rt.step(1.0, 0.0)
        assert rec.canonical_id == "UNIT-SHW-L1-T108"
        # every emitted record keeps the locked canonical reference
        rec2 = rt.step(0.0, 2.0)
        assert rec2.canonical_id == "UNIT-SHW-L1-T108"

    def test_snapshot_carries_truthful_provenance(self):
        rt = _runtime()
        snap = rt.snapshot()
        prov = snap.provenance
        assert prov.origin_kind is OriginKind.SIMULATION
        assert prov.data_status is DataStatus.SYNTHETIC
        assert prov.fidelity is Fidelity.FIRST_ORDER
        assert prov.workspace_id == "shwtp"
        assert prov.scope_path == SHWTP_T108_SCOPE_PATH
        # no site/measurement labels in the serialized snapshot provenance
        blob = json.dumps(prov.to_dict()).lower()
        for token in ("measured", "site", "siteverified", "sourcemapped", "calibrated"):
            assert token not in blob

    def test_snapshot_provenance_tracks_time_and_step(self):
        rt = _runtime()
        assert rt.state.provenance.simulation_time_s == pytest.approx(0.0)
        assert rt.state.provenance.step == 0
        rt.step(1.0, 0.0)
        assert rt.state.provenance.simulation_time_s == pytest.approx(1.0)
        assert rt.state.provenance.step == 1

    def test_snapshot_provenance_immutable_and_detached(self):
        rt = _runtime()
        snap = rt.snapshot()
        rt.step(5.0, 0.0)
        # the pre-step snapshot provenance is unchanged (detached)
        assert snap.provenance.simulation_time_s == pytest.approx(0.0)
        assert snap.provenance.step == 0
        assert rt.state.provenance.simulation_time_s == pytest.approx(1.0)

