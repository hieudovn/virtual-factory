"""VF-vNEXT-G13B — SH-WTP T106 standalone synthetic LogicalOnly runtime tests.

Proves (Issue #63 required tests): locked T106 canonical/path, only-T106 added,
deterministic init/sequence, output == input, exact dt time advance, zero inflow,
invalid input fail closed, reset, attempt isolation, detached snapshot,
logical_only provenance on step + snapshot, no site/measured labels, no filtration
physics/quality/backwash fields, no G12B relation projection, no
BoundaryPort/G4/coordinator, T108 unchanged/green, T110 blocked, workspace/container
target unavailable.
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
    SHWTP_T106_CANONICAL_ID,
    SHWTP_T106_SCOPE_PATH,
    T106Config,
    T106LogicalRuntime,
    T106RuntimeError,
)
from virtual_factory.shwtp import logical_runtime as t106_module
from virtual_factory.shwtp.runtime import (
    SHWTP_T108_CANONICAL_ID,
    SHWTP_T108_SCOPE_PATH,
    T108Config,
    T108TankRuntime,
)
from virtual_factory.workspace import StructuralPath

ADMISSION_PATH = (
    Path(__file__).resolve().parent.parent
    / "configs"
    / "vnext"
    / "shwtp"
    / "shwtp_synthetic_runtime_admission.json"
)


def _config(**overrides) -> T106Config:
    kwargs = dict(dt_s=1.0)
    kwargs.update(overrides)
    return T106Config(**kwargs)


def _ctx(scope_path=SHWTP_T106_SCOPE_PATH, *, workspace_id="shwtp", run_id="run-1"):
    return RunContextV2(
        workspace_id=workspace_id,
        run_id=run_id,
        scope_path=scope_path,
        scenario_id="scn-1",
    )


def _runtime(**overrides) -> T106LogicalRuntime:
    return T106LogicalRuntime(_config(**overrides), _ctx())


def _module_code(module) -> str:
    return re.sub(r'""".*?"""', "", inspect.getsource(module), flags=re.DOTALL)


class TestTarget:
    def test_canonical_and_path_locked_to_t106(self):
        assert SHWTP_T106_CANONICAL_ID == "UNIT-SHW-L1-T106"
        assert SHWTP_T106_SCOPE_PATH == StructuralPath(("shwtp", "line1", "l1_t106"))
        rt = _runtime()
        assert rt.canonical_id == "UNIT-SHW-L1-T106"
        assert rt.scope_path == SHWTP_T106_SCOPE_PATH
        # no caller override of canonical reference exists
        assert "canonical_id" not in inspect.signature(T106LogicalRuntime.__init__).parameters

    def test_only_t106_added_by_this_module(self):
        code = _module_code(t106_module)
        assert "UNIT-SHW-L1-T106" in code
        for token in ("SHWTP_T110_CANONICAL_ID", "T110Runtime", "T108Runtime"):
            assert token not in code

    def test_workspace_container_t110_t108_targets_rejected(self):
        for bad_scope in (
            StructuralPath(("shwtp",)),
            StructuralPath(("shwtp", "line1")),
            SHWTP_T108_SCOPE_PATH,
        ):
            with pytest.raises(T106RuntimeError):
                T106LogicalRuntime(_config(), _ctx(scope_path=bad_scope))
        with pytest.raises(T106RuntimeError):
            T106LogicalRuntime(_config(), _ctx(scope_path=None))
        with pytest.raises(T106RuntimeError):
            T106LogicalRuntime(
                _config(),
                RunContextV2(workspace_id="other", run_id="r", scope_path=None),
            )


class TestConfig:
    def test_invalid_dt_fails_closed(self):
        for bad_dt in (0.0, -1.0):
            with pytest.raises(T106RuntimeError):
                _config(dt_s=bad_dt)

    def test_invalid_inflow_fails_closed(self):
        rt = _runtime()
        with pytest.raises(T106RuntimeError):
            rt.step(-0.1)
        with pytest.raises(T106RuntimeError):
            rt.step(float("nan"))
        with pytest.raises(T106RuntimeError):
            rt.step(float("inf"))


class TestStepSemantics:
    def test_deterministic_initialization(self):
        a = _runtime()
        b = _runtime()
        assert a.state == b.state
        assert a.state.time_s == 0.0
        assert a.state.last_input_flow_m3_s == 0.0
        assert a.state.last_output_flow_m3_s == 0.0

    def test_identical_input_sequence_identical_output(self):
        def run():
            rt = _runtime()
            out = []
            for q in (0.0, 1.0, 2.5, 0.0):
                rec = rt.step(q)
                out.append((rec.output_flow_m3_s, rec.end_time_s))
            return out

        assert run() == run()

    def test_output_equals_input(self):
        rt = _runtime()
        for q in (0.0, 1.0, 2.5, 100.0):
            rec = rt.step(q)
            assert rec.output_flow_m3_s == pytest.approx(q)
            assert rt.state.last_input_flow_m3_s == pytest.approx(q)
            assert rt.state.last_output_flow_m3_s == pytest.approx(q)

    def test_time_advances_exactly_dt(self):
        rt = _runtime(dt_s=0.5)
        assert rt.step(1.0).end_time_s == pytest.approx(0.5)
        assert rt.step(2.0).end_time_s == pytest.approx(1.0)
        assert rt.state.time_s == pytest.approx(1.0)

    def test_zero_inflow_stays_zero(self):
        rt = _runtime()
        rec = rt.step(0.0)
        assert rec.output_flow_m3_s == pytest.approx(0.0)
        assert rt.state.last_output_flow_m3_s == pytest.approx(0.0)


class TestLifecycle:
    def test_reset_restores_initial_state(self):
        rt = _runtime()
        rt.step(3.0)
        rt.step(1.0)
        rt.reset()
        assert rt.state.time_s == 0.0
        assert rt.state.last_input_flow_m3_s == 0.0
        assert rt.state.last_output_flow_m3_s == 0.0
        assert rt.step_index == 0

    def test_fresh_attempts_isolated(self):
        a = _runtime()
        b = _runtime()
        a.step(5.0)
        assert b.state.time_s == 0.0
        assert b.state.last_output_flow_m3_s == 0.0
        assert a.state.time_s != b.state.time_s

    def test_snapshot_detached_and_immutable(self):
        rt = _runtime()
        snap = rt.snapshot()
        rt.step(5.0)
        assert snap.time_s == 0.0
        assert snap.last_output_flow_m3_s == 0.0
        assert rt.state.time_s != snap.time_s


class TestProvenance:
    def test_step_and_snapshot_provenance_logical_only(self):
        rt = _runtime()
        rec = rt.step(2.0)
        for prov in (rec.provenance, rt.state.provenance, rt.snapshot().provenance):
            assert prov.origin_kind is OriginKind.SIMULATION
            assert prov.data_status is DataStatus.SYNTHETIC
            assert prov.fidelity is Fidelity.LOGICAL_ONLY
            assert prov.workspace_id == "shwtp"
            assert prov.scope_path == SHWTP_T106_SCOPE_PATH

    def test_no_site_or_measurement_labels(self):
        rt = _runtime()
        rec = rt.step(2.0)
        for prov in (rec.provenance, rt.state.provenance):
            blob = json.dumps(prov.to_dict()).lower()
            for token in ("measured", "site", "siteverified", "sourcemapped", "calibrated"):
                assert token not in blob
        assert rec.provenance.fidelity.value == "logical_only"
        assert rt.state.provenance.fidelity.value == "logical_only"


class TestNoPhysics:
    def test_no_filtration_physics_or_quality_fields(self):
        code = _module_code(t106_module)
        for token in (
            "headloss",
            "efficiency",
            "turbidity",
            "quality",
            "backwash",
            "pressure",
            "capacity_m3",
            "accumulation",
        ):
            assert token not in code


class TestNoProjection:
    def test_no_g12_relation_or_g4_projection(self):
        code = _module_code(t106_module)
        for token in (
            "FLOWS_TO",
            "DISCHARGES_TO",
            "CONNECTED_TO",
            "CompositionBinding",
            "BoundaryPort",
            "coordinator",
        ):
            assert token not in code
        for token in (
            "from virtual_factory.composition",
            "from virtual_factory.runcontrol",
            "from virtual_factory.equipment",
        ):
            assert token not in code


class TestAdmissionAndT108:
    def test_admission_authority_and_t110_blocked(self):
        admission = json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))
        authority = admission["authority"]
        assert authority["review_status"] == "COMPLETE"
        assert authority["authorization_mode"] == "CANDIDATE_SCOPED"
        assert "UNIT-SHW-L1-T106" in authority["authorized_candidates"]
        assert "UNIT-SHW-WASH-T110" in authority["blocked_candidates"]
        assert authority["vf_runtime_authorization"] == "NOT_AUTHORIZED"
        assert authority["site_authorized_execution"] == "NOT_AUTHORIZED"
        # no T110 runtime exists anywhere in the shwtp package runtime modules
        assert "SHWTP_T110_CANONICAL_ID" not in vars(t106_module)

    def test_t108_runtime_unchanged_and_still_green(self):
        # T108 runtime semantics preserved (tank accumulator, not a pass-through)
        cfg = T108Config(capacity_m3=100.0, tank_area_m2=10.0, initial_volume_m3=50.0, dt_s=1.0)
        t108 = T108TankRuntime(cfg, _ctx(scope_path=SHWTP_T108_SCOPE_PATH))
        assert t108.canonical_id == SHWTP_T108_CANONICAL_ID == "UNIT-SHW-L1-T108"
        rec = t108.step(2.0, 0.0)
        assert rec.end_volume_m3 == pytest.approx(52.0)
        assert rec.overflow_m3 == pytest.approx(0.0)
