"""VF-vNEXT-G15 — SH-WTP federated evaluation trace & diagnostics tests.

Proves (Issue #66 required tests): exactly one trace row per completed window;
deterministic trace + summary; exact run/window/time identity; explicit_lagged;
lag_windows=1; first-window lag visible; second-window previous-output use;
T106/T108 step values captured; committed-next inflow; volume/level/outflow/
overflow exact; zero mass-balance residual; balanced/fill/drain/overflow cases;
exact totals; min/max; attempt isolation; failed window not recorded as success;
provenance truthful; authority unchanged; no runtime mutation by inspection.
"""

from __future__ import annotations

import inspect
import re

import pytest

from virtual_factory.composition import WindowOutcome
from virtual_factory.shwtp import (
    ShwtpEvaluationError,
    ShwtpEvaluationRow,
    ShwtpEvaluationSummary,
    ShwtpEvaluator,
    ShwtpFederationConfig,
    t108_mass_balance_residual,
)
from virtual_factory.shwtp import evaluation as ev_module
from virtual_factory.shwtp.evaluation import SHWTP_EVALUATION_LAG_WINDOWS
from virtual_factory.shwtp.structural import (
    SHWTP_RUNTIME_AUTHORIZATION,
    SHWTP_SITE_AUTHORIZED_EXECUTION,
)


def _config(**overrides) -> ShwtpFederationConfig:
    kwargs = dict(
        communication_step_s=1.0,
        initial_t108_inflow_m3_s=1.0,
        t106_inflow_m3_s=2.0,
        t108_requested_outflow_m3_s=0.5,
        t108_capacity_m3=100.0,
        t108_tank_area_m2=10.0,
        t108_initial_volume_m3=50.0,
    )
    kwargs.update(overrides)
    return ShwtpFederationConfig(**kwargs)


def _run(config, window_count=3) -> ShwtpEvaluator:
    return ShwtpEvaluator(config, window_count=window_count).run()


class TestEvaluationRow:
    def test_one_row_per_completed_window(self):
        ev = _run(_config(), window_count=4)
        assert len(ev.rows) == 4
        assert [r.window_id for r in ev.rows] == [
            "window-1",
            "window-2",
            "window-3",
            "window-4",
        ]
        assert [r.window_index for r in ev.rows] == [1, 2, 3, 4]

    def test_row_identity_exact(self):
        ev = _run(_config(run_id="run-g15"), window_count=2)
        rows = ev.rows
        assert rows[0].window_id == "window-1"
        assert rows[1].window_id == "window-2"
        assert rows[0].start_time_s == 0.0
        assert rows[0].end_time_s == 1.0
        assert rows[1].start_time_s == 1.0
        assert rows[1].end_time_s == 2.0
        assert rows[0].communication_step_s == 1.0
        assert rows[0].run_id == "run-g15"
        assert rows[0].coupling_policy == "explicit_lagged"

    def test_row_status_completed_and_detached(self):
        ev = _run(_config())
        for row in ev.rows:
            assert row.status == "completed"
        assert isinstance(ev.rows[0], ShwtpEvaluationRow)


class TestStepValues:
    def test_t106_input_output_captured(self):
        ev = _run(_config(t106_inflow_m3_s=2.0))
        # Window 1 T106 step input/output == scenario inflow == pass-through.
        r1 = ev.rows[0]
        assert r1.t106_input_flow_m3_s == 2.0
        assert r1.t106_output_staged_m3_s == 2.0

    def test_t108_used_and_committed_next_captured(self):
        cfg = _config(initial_t108_inflow_m3_s=1.0, t106_inflow_m3_s=2.0)
        ev = _run(cfg, window_count=2)
        r1, r2 = ev.rows
        # Window 1 uses the explicit initial inflow; committed next = Q106[1].
        assert r1.t108_inflow_used_m3_s == 1.0
        assert r1.t108_committed_next_m3_s == 2.0
        # Window 2 uses exactly Q106[1]; committed next = Q106[2].
        assert r2.t108_inflow_used_m3_s == 2.0
        assert r2.t108_committed_next_m3_s == 2.0

    def test_t108_volume_level_outflow_overflow_exact(self):
        cfg = _config(
            initial_t108_inflow_m3_s=1.0,
            t106_inflow_m3_s=2.0,
            t108_requested_outflow_m3_s=0.5,
            t108_capacity_m3=100.0,
            t108_tank_area_m2=10.0,
            t108_initial_volume_m3=50.0,
        )
        ev = _run(cfg, window_count=1)
        r = ev.rows[0]
        assert r.t108_start_volume_m3 == 50.0
        assert r.t108_end_volume_m3 == pytest.approx(50.5)
        assert r.t108_end_level_m == pytest.approx(5.05)
        assert r.t108_requested_outflow_m3_s == 0.5
        assert r.t108_applied_outflow_m3_s == 0.5
        assert r.t108_overflow_m3 == 0.0
        assert r.mass_balance_residual_m3 == 0.0


class TestMassBalance:
    def test_residual_helper_exact_zero(self):
        ev = _run(_config(), window_count=3)
        for row in ev.rows:
            assert row.mass_balance_residual_m3 == 0.0
            assert t108_mass_balance_residual(ev.federation.t108.last_step) == 0.0

    def test_overflow_mass_accounted(self):
        cfg = _config(
            t106_inflow_m3_s=5.0,
            t108_requested_outflow_m3_s=0.0,
            t108_capacity_m3=50.0,
            t108_tank_area_m2=5.0,
            t108_initial_volume_m3=50.0,
            initial_t108_inflow_m3_s=5.0,
        )
        ev = _run(cfg, window_count=4)
        for row in ev.rows:
            assert row.t108_overflow_m3 == 5.0
            assert row.t108_end_volume_m3 == 50.0
            assert row.mass_balance_residual_m3 == 0.0


class TestLagDiagnostics:
    def test_lag_windows_constant(self):
        assert SHWTP_EVALUATION_LAG_WINDOWS == 1
        ev = _run(_config())
        assert ev.serialize()["lag_windows"] == 1
        assert ev.summary.lag_windows == 1

    def test_first_window_lag_visible(self):
        cfg = _config(initial_t108_inflow_m3_s=1.0, t106_inflow_m3_s=2.0)
        ev = _run(cfg, window_count=2)
        r1 = ev.rows[0]
        # Window 1 uses the explicit initial inflow, NOT T106's new output.
        assert r1.t108_inflow_used_m3_s == 1.0
        assert r1.t108_inflow_used_m3_s != r1.t106_output_staged_m3_s
        # Boundary 1 commits T106 output for the next window.
        assert r1.t108_committed_next_m3_s == r1.t106_output_staged_m3_s

    def test_second_window_uses_previous_output(self):
        cfg = _config(initial_t108_inflow_m3_s=1.0, t106_inflow_m3_s=2.0)
        ev = _run(cfg, window_count=2)
        r1, r2 = ev.rows
        assert r1.t106_output_staged_m3_s == 2.0
        assert r2.t108_inflow_used_m3_s == 2.0
        assert r2.t108_inflow_used_m3_s == r1.t106_output_staged_m3_s

    def test_lag_is_evaluation_metadata_not_graph_property(self):
        ev = _run(_config())
        graph = ev.federation.coordinator.graph
        assert not hasattr(graph, "lag_windows")
        assert not hasattr(graph, "coupling_policy")


class TestSummary:
    def test_summary_fields_deterministic(self):
        ev = _run(_config(run_id="run-g15"), window_count=3)
        s = ev.summary
        assert isinstance(s, ShwtpEvaluationSummary)
        assert s.run_id == "run-g15"
        assert s.window_count == 3
        assert s.start_time_s == 0.0
        assert s.end_time_s == 3.0
        assert s.communication_step_s == 1.0
        assert s.coupling_policy == "explicit_lagged"
        assert s.lag_windows == 1

    def test_summary_totals_derive_from_trace(self):
        cfg = _config(
            initial_t108_inflow_m3_s=1.0,
            t106_inflow_m3_s=2.0,
            t108_requested_outflow_m3_s=0.5,
        )
        ev = _run(cfg, window_count=3)
        s = ev.summary
        rows = ev.rows
        dt = 1.0
        assert s.total_t106_staged_volume_m3 == pytest.approx(
            sum(r.t106_output_staged_m3_s * dt for r in rows)
        )
        assert s.total_t108_inflow_used_volume_m3 == pytest.approx(
            sum(r.t108_inflow_used_m3_s * dt for r in rows)
        )
        assert s.total_applied_outflow_volume_m3 == pytest.approx(
            sum(r.t108_applied_outflow_m3_s * dt for r in rows)
        )
        assert s.total_overflow_volume_m3 == pytest.approx(
            sum(r.t108_overflow_m3 for r in rows)
        )
        assert s.max_abs_mass_balance_residual_m3 == max(
            abs(r.mass_balance_residual_m3) for r in rows
        )
        # volumes/levels
        assert s.t108_initial_volume_m3 == rows[0].t108_start_volume_m3
        assert s.t108_final_volume_m3 == rows[-1].t108_end_volume_m3
        vols = [r.t108_start_volume_m3 for r in rows]
        vols += [r.t108_end_volume_m3 for r in rows]
        assert s.t108_min_volume_m3 == min(vols)
        assert s.t108_max_volume_m3 == max(vols)
        area = ev.federation.t108.runtime.config.tank_area_m2
        assert s.t108_initial_level_m == pytest.approx(s.t108_initial_volume_m3 / area)
        assert s.t108_final_level_m == pytest.approx(s.t108_final_volume_m3 / area)


class TestDeterminismAndIsolation:
    def test_deterministic_trace_and_summary(self):
        a = _run(_config(run_id="run-d"), window_count=5)
        b = _run(_config(run_id="run-d"), window_count=5)
        assert a.serialize() == b.serialize()
        assert a.summary.to_dict() == b.summary.to_dict()
        assert [r.to_dict() for r in a.rows] == [r.to_dict() for r in b.rows]

    def test_fresh_attempts_isolated(self):
        a = ShwtpEvaluator(_config(run_id="run-i"), window_count=3)
        b = ShwtpEvaluator(_config(run_id="run-i"), window_count=3)
        assert a.rows == ()
        assert b.rows == ()
        a.run()
        assert len(a.rows) == 3
        assert b.rows == ()
        assert b.federation.time_s == 0.0
        b.run()
        assert [r.to_dict() for r in a.rows] == [r.to_dict() for r in b.rows]

    def test_inspection_does_not_mutate(self):
        ev = _run(_config(), window_count=3)
        before = ev.serialize()
        # Repeated inspection is idempotent.
        assert ev.serialize() == before
        assert ev.summary.to_dict() == ev.summary.to_dict()
        assert len(ev.rows) == 3


class TestRunnerFailClosed:
    def test_window_count_must_be_positive(self):
        with pytest.raises(ShwtpEvaluationError):
            ShwtpEvaluator(_config(), window_count=0)
        with pytest.raises(ShwtpEvaluationError):
            ShwtpEvaluator(_config(), window_count=-2)

    def test_window_count_must_be_int(self):
        with pytest.raises(ShwtpEvaluationError):
            ShwtpEvaluator(_config(), window_count=True)
        with pytest.raises(ShwtpEvaluationError):
            ShwtpEvaluator(_config(), window_count=2.5)

    def test_run_twice_fails(self):
        ev = ShwtpEvaluator(_config(), window_count=2)
        ev.run()
        with pytest.raises(ShwtpEvaluationError):
            ev.run()

    def test_failed_window_not_recorded_as_success(self):
        ev = ShwtpEvaluator(_config(), window_count=2)

        class _FailingFed:
            def run_window(self, window_id):
                return WindowOutcome(
                    window_id=window_id,
                    target_time_s=1.0,
                    participants=("shwtp/line1/l1_t106", "shwtp/line1/l1_t108"),
                    committed=(),
                    status="failed",
                    failure="boom",
                )

        ev._federation = _FailingFed()  # noqa: SLF001 — deliberate failure inject
        with pytest.raises(ShwtpEvaluationError):
            ev.run()
        assert ev.rows == ()
        assert ev.summary is None


class TestEvaluationCases:
    def test_balanced(self):
        cfg = _config(
            t106_inflow_m3_s=2.0,
            t108_requested_outflow_m3_s=2.0,
            t108_initial_volume_m3=50.0,
            initial_t108_inflow_m3_s=2.0,
        )
        ev = _run(cfg, window_count=6)
        for row in ev.rows:
            assert row.t108_end_volume_m3 == 50.0
            assert row.mass_balance_residual_m3 == 0.0
        assert ev.summary.t108_min_volume_m3 == 50.0
        assert ev.summary.t108_max_volume_m3 == 50.0
        assert ev.summary.t108_final_volume_m3 == 50.0

    def test_fill(self):
        cfg = _config(
            t106_inflow_m3_s=3.0,
            t108_requested_outflow_m3_s=1.0,
            t108_initial_volume_m3=50.0,
            initial_t108_inflow_m3_s=3.0,
        )
        ev = _run(cfg, window_count=6)
        ends = [r.t108_end_volume_m3 for r in ev.rows]
        assert ends[0] > 50.0
        assert all(b > a for a, b in zip(ends, ends[1:]))
        assert ev.summary.t108_final_volume_m3 > ev.summary.t108_initial_volume_m3
        assert ev.summary.t108_max_volume_m3 == ends[-1]
        for row in ev.rows:
            assert row.mass_balance_residual_m3 == 0.0

    def test_drain(self):
        cfg = _config(
            t106_inflow_m3_s=1.0,
            t108_requested_outflow_m3_s=4.0,
            t108_initial_volume_m3=50.0,
            initial_t108_inflow_m3_s=1.0,
        )
        ev = _run(cfg, window_count=6)
        ends = [r.t108_end_volume_m3 for r in ev.rows]
        assert all(b < a for a, b in zip(ends, ends[1:]))
        assert ev.summary.t108_final_volume_m3 < ev.summary.t108_initial_volume_m3
        # never negative inventory
        for row in ev.rows:
            assert row.t108_end_volume_m3 >= 0.0
            assert row.mass_balance_residual_m3 == 0.0

    def test_overflow(self):
        cfg = _config(
            t106_inflow_m3_s=5.0,
            t108_requested_outflow_m3_s=0.0,
            t108_capacity_m3=50.0,
            t108_tank_area_m2=5.0,
            t108_initial_volume_m3=50.0,
            initial_t108_inflow_m3_s=5.0,
        )
        ev = _run(cfg, window_count=6)
        assert all(r.t108_overflow_m3 == 5.0 for r in ev.rows)
        assert ev.summary.total_overflow_volume_m3 == 30.0
        assert all(r.t108_end_volume_m3 == 50.0 for r in ev.rows)
        for row in ev.rows:
            assert row.mass_balance_residual_m3 == 0.0


class TestProvenanceAndAuthority:
    def test_provenance_truthful(self):
        ev = _run(_config(), window_count=2)
        for row in ev.rows:
            assert row.t106_origin_kind == "simulation"
            assert row.t106_data_status == "synthetic"
            assert row.t106_fidelity == "logical_only"
            assert row.t108_origin_kind == "simulation"
            assert row.t108_data_status == "synthetic"
            assert row.t108_fidelity == "first_order"
            assert row.status == "completed"

    def test_authority_unchanged(self):
        assert SHWTP_RUNTIME_AUTHORIZATION == "NOT_AUTHORIZED"
        assert SHWTP_SITE_AUTHORIZED_EXECUTION == "NOT_AUTHORIZED"

    def test_no_t110_or_f02_f07(self):
        code = re.sub(r'""".*?"""', "", inspect.getsource(ev_module), flags=re.DOTALL)
        assert "T110" not in code
        for rel in ("REL-SHW-F02", "REL-SHW-F03", "REL-SHW-F04", "REL-SHW-F05"):
            assert rel not in code

    def test_no_tolerance_policy_invented(self):
        # Residual is verified exactly (no rel/abs tolerance invented).
        code = re.sub(r'""".*?"""', "", inspect.getsource(ev_module), flags=re.DOTALL)
        assert "isclose" not in code
        assert "rel_tol" not in code
        assert "abs_tol" not in code

    def test_exactly_one_f01_binding_only(self):
        ev = _run(_config())
        graph = ev.federation.coordinator.graph
        assert len(graph.bindings) == 1
        assert graph.bindings[0].edge_id == "BIND-SHW-F01-T106-OUT-T108-IN"
        assert ev.federation.participants == (
            "shwtp/line1/l1_t106",
            "shwtp/line1/l1_t108",
        )
