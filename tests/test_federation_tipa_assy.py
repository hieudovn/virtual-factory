"""VF-vNEXT-G5 — TIPA Workspace / ASSY federation onto G1–G4 tests.

Proves (Issue #50): exact TIPA -> ASSY -> six sub-line hierarchy through G1
authority; ASSY container-only (cannot register); six executable sub-lines;
six adapters wrap six existing AssyLineRuntime instances (no rewrite); adapter
time delegation; representative standalone vs federated semantic parity at
supported shared boundaries; runtime/config/RNG isolation; no direct
cross-scope mutation; identity drift/mismatch fails closed through existing G4
rules; ASSY oracle/regressions remain green (run separately); no G6+.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from virtual_factory.assembly import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
    WipLifecycle,
)
from virtual_factory.composition import (
    CompositionGraph,
    CoordinationError,
    Coordinator,
)
from virtual_factory.composition.participant import ExecutableParticipant
from virtual_factory.federation import (
    PLANT_ID,
    PRODUCTION_LINE_ID,
    SUB_LINE_IDS,
    AssySubLineAdapter,
    FederationStructuralError,
    TipaAssyFederation,
    assy_scope_path,
    build_tipa_workspace,
    sub_line_path,
)

REAL_CONFIG = (
    Path(__file__).resolve().parent.parent
    / "configs" / "plants" / "tipa_assy_demo.yaml"
)


# ═══════════════════════════════════════════════════════════
# Shared helpers
# ═══════════════════════════════════════════════════════════

def make_fast_config() -> AssyLineConfig:
    """Fast config: nominal dwell 10s, index 0s, station durations 5s.

    Every natural dwell lands EXACTLY on a 10s boundary (no overrun), so the
    runtime can legitimately reach any 10s multiple.
    """
    cfg = AssyLineConfig()
    cfg.conveyor.nominal_line_dwell_time_s = 10.0
    cfg.conveyor.index_movement_duration_s = 0.0
    for key in cfg.station_durations:
        cfg.station_durations[key] = 5.0
    return cfg


def seed_one(runtime: AssyLineRuntime) -> None:
    """Canonical ASSY oracle seed: one SSO2 + one RSO2 + one introduction."""
    runtime.produce_sso2_wip()
    runtime.produce_rso2_wip()
    runtime.introduce_to_assy("SSO2-0001", "PAL-001")


def seed_like_demo(runtime: AssyLineRuntime) -> None:
    """Reproduce the AssyDemoComposition per-context upstream seeding."""
    for _ in range(7):
        runtime.produce_sso2_wip()
    for _ in range(7):
        runtime.produce_rso2_wip()
    runtime.introduce_to_assy("SSO2-0001", "PAL-001")


def natural_cycle(runtime: AssyLineRuntime) -> None:
    """One natural ASSY advancement step (the ASSY oracle driver order)."""
    runtime.execute_dwell()
    if runtime.conveyor.state == ConveyorState.READY_TO_INDEX:
        runtime.index_line()


def canonical_state(runtime: AssyLineRuntime) -> tuple:
    """Deterministic normalized domain-state projection for parity."""
    return (
        runtime.simulation_time_s,
        runtime.conveyor.dwell_number,
        tuple(
            (pos, runtime.conveyor.wip_at(pos))
            for pos in runtime.conveyor.positions
        ),
        tuple(
            sorted(
                (wip_id, runtime.get_wip(wip_id).lifecycle.value,
                 runtime.get_wip(wip_id).current_position)
                for wip_id in runtime.wip_ids
            )
        ),
        runtime.motor_count,
        runtime.rso2_buffer_size,
        tuple(
            sorted(
                (g.child_wip_id, tuple(g.parent_wip_ids))
                for g in runtime.genealogy.all_records()
            )
        ),
        tuple(
            sorted(
                (wip_id, runtime.get_current_quality_status(wip_id).value)
                for wip_id in runtime.wip_ids
            )
        ),
        tuple(evt.event_type for evt in runtime.trace),
    )


def released_ids(runtime: AssyLineRuntime) -> tuple[str, ...]:
    return tuple(
        sorted(
            wip_id
            for wip_id in runtime.wip_ids
            if runtime.get_wip(wip_id).lifecycle is WipLifecycle.RELEASED
        )
    )


def _coordinator(workspace) -> Coordinator:
    return Coordinator(workspace, CompositionGraph("TIPA", bindings=(), ports=()))


# ═══════════════════════════════════════════════════════════
# A — TIPA structural workspace mapping (tests 1, 3)
# ═══════════════════════════════════════════════════════════

class TestTipaWorkspace:
    def test_canonical_hierarchy_resolves_through_g1(self):
        ws = build_tipa_workspace()
        assert ws.workspace_id == PLANT_ID == "TIPA"
        assy = ws.resolve_scope(assy_scope_path())
        assert assy.is_container_only
        assert assy.path.as_string() == "TIPA/ASSY"
        # ASSY owns no executable boundary -> no fake runtime for ASSY.
        assert [c.scope_id for c in assy.children] == list(SUB_LINE_IDS)
        for sub_line_id in SUB_LINE_IDS:
            scope = ws.resolve_scope(sub_line_path(sub_line_id))
            assert scope.is_executable_capable
            assert scope.path.as_string() == f"TIPA/ASSY/{sub_line_id}"
            assert scope.path.workspace_id == "TIPA"

    def test_sub_line_scope_ids_are_canonical_and_sorted(self):
        assert SUB_LINE_IDS == (
            "ASSY-SL01", "ASSY-SL02", "ASSY-SL03",
            "ASSY-SL04", "ASSY-SL05", "ASSY-SL06",
        )

    def test_sub_line_path_fails_closed_on_unknown_id(self):
        with pytest.raises(FederationStructuralError):
            sub_line_path("ASSY-SL99")

    def test_workspace_is_deterministic(self):
        ws1 = build_tipa_workspace()
        ws2 = build_tipa_workspace()
        paths1 = {s.path.as_string() for s in ws1.resolve_scope(
            assy_scope_path()).iter_scopes()}
        paths2 = {s.path.as_string() for s in ws2.resolve_scope(
            assy_scope_path()).iter_scopes()}
        assert paths1 == paths2
        assert len(paths1) == 7  # ASSY + 6 sub-lines

    def test_structural_identity_is_distinct_from_pim_identity(self):
        # G1 structural path is never a PIM canonical id / demo label.
        p = sub_line_path("ASSY-SL01")
        assert p.as_string() == "TIPA/ASSY/ASSY-SL01"
        assert p.as_string() != "ASSY-SL01"  # not flattened
        assert "ASSY-SL01" in p.segments  # demo id is only a segment label


# ═══════════════════════════════════════════════════════════
# B — ASSY container-only cannot register (test 2)
# ═══════════════════════════════════════════════════════════

class TestAssyContainerOnly:
    def test_assy_container_scope_cannot_register_as_participant(self):
        ws = build_tipa_workspace()
        runtime = AssyLineRuntime(config=make_fast_config())
        adapter = AssySubLineAdapter(scope_path=assy_scope_path(), runtime=runtime)
        coord = _coordinator(ws)
        with pytest.raises(CoordinationError) as excinfo:
            coord.register(adapter)
        assert "container-only" in str(excinfo.value)

    def test_adapter_rejects_non_structural_path(self):
        runtime = AssyLineRuntime(config=make_fast_config())
        with pytest.raises(TypeError):
            AssySubLineAdapter(scope_path="TIPA/ASSY/ASSY-SL01", runtime=runtime)  # type: ignore[arg-type]


# ═══════════════════════════════════════════════════════════
# C — Federation host: six adapters over six runtimes (tests 3, 4)
# ═══════════════════════════════════════════════════════════

class TestFederationHost:
    def test_six_isolated_runtimes_wrapped_without_rewrite(self):
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        assert sorted(host.sub_lines) == list(SUB_LINE_IDS)
        assert len({id(sl.runtime) for sl in host.sub_lines.values()}) == 6
        assert len({id(sl.config) for sl in host.sub_lines.values()}) == 6
        for sub_line_id in SUB_LINE_IDS:
            sl = host.get(sub_line_id)
            assert type(sl.runtime) is AssyLineRuntime  # exact class, no rewrite
            assert isinstance(sl.adapter, AssySubLineAdapter)
            assert sl.adapter.runtime is sl.runtime
            assert sl.adapter.scope_path is sl.path
            assert sl.path.as_string() == f"TIPA/ASSY/{sub_line_id}"
            assert sl.identity.sub_line_id == sub_line_id

    def test_adapter_conforms_to_g4_participant_protocol(self):
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        adapter = host.adapter("ASSY-SL01")
        assert isinstance(adapter, ExecutableParticipant)

    def test_registration_order_is_deterministic_scope_order(self):
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        coord = host.make_coordinator()
        order = host.register(coord)
        assert order == tuple(
            f"TIPA/ASSY/{sub_line_id}" for sub_line_id in SUB_LINE_IDS
        )
        assert coord.participants == order

    def test_identity_matches_registered_structural_scope(self):
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        coord = host.make_coordinator()
        host.register(coord, sub_line_ids=["ASSY-SL01"])
        assert coord.participants == ("TIPA/ASSY/ASSY-SL01",)
        # The runtime's adapter identity equals its registered structural scope.
        assert host.adapter("ASSY-SL01").scope_path.as_string() == (
            "TIPA/ASSY/ASSY-SL01"
        )

    def test_production_host_initializes_without_demo_composition(self):
        """G5-C01: six isolated runtimes are built DIRECTLY (no
        AssyDemoComposition constructed/owned, no demo policy names imported)."""
        import virtual_factory.federation.assy_host as host_module

        for name in ("AssyDemoComposition", "DemoScenario", "ContinuousFeedPolicy"):
            assert name not in host_module.__dict__, name
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        assert len(host.sub_lines) == 6
        for name in ("_composition", "composition", "scenario", "feed_policy",
                     "continuous_feed_enabled", "selected_sub_line_id",
                     "demo_step_number"):
            assert not hasattr(host, name), name
        for sl in host.sub_lines.values():
            assert type(sl.runtime) is AssyLineRuntime

    def test_federation_api_exposes_no_demo_policy_authority(self):
        """G5-C01: host construction takes only config_path; no implicit
        seeded-inventory/demo policy in the production host."""
        import inspect

        params = list(inspect.signature(TipaAssyFederation.__init__).parameters)
        assert params == ["self", "config_path"]
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        for sub_line_id in SUB_LINE_IDS:
            # No WIP is pre-seeded by the production host (time 0, empty).
            assert host.runtime(sub_line_id).simulation_time_s == 0.0
            assert host.runtime(sub_line_id).wip_count == 0


# ═══════════════════════════════════════════════════════════
# D — Adapter time delegation + supported shared boundary (tests 5, 6)
# ═══════════════════════════════════════════════════════════

class TestAdapterTimeAndBoundary:
    def test_adapter_current_time_delegates_to_runtime(self):
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        for sub_line_id in SUB_LINE_IDS:
            sl = host.get(sub_line_id)
            assert sl.adapter.current_time_s == sl.runtime.simulation_time_s == 0.0

    def test_all_six_reach_supported_shared_boundary_after_explicit_prep(self):
        """All six reach a supported shared natural boundary after EXPLICIT
        equivalent preparation (seeding is not implicit production policy)."""
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        for sub_line_id in SUB_LINE_IDS:
            seed_like_demo(host.runtime(sub_line_id))  # explicit prep helper
        coord = host.make_coordinator()
        outcome = host.run_window(coord, 120.0)
        assert outcome.status == "completed"
        assert outcome.failure is None
        for sub_line_id in SUB_LINE_IDS:
            sl = host.get(sub_line_id)
            # Natural single-dwell boundary, not a forced/arbitrary clock.
            assert sl.runtime.simulation_time_s == 120.0
            assert sl.adapter.current_time_s == 120.0
            assert sl.runtime.conveyor.state is ConveyorState.STOPPED

    def test_unreachable_fractional_boundary_fails_closed(self):
        """target 60 is not a natural ASSY boundary (nominal dwell 120) -> the
        coordinator window must fail; no fractional dwell/time rewrite."""
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        coord = host.make_coordinator()
        outcome = host.run_window(coord, 60.0, sub_line_ids=["ASSY-SL01"])
        assert outcome.status == "failed"
        assert outcome.committed == ()
        assert "overshoots" in (outcome.failure or "")

    def test_adapter_rejects_backward_target(self):
        runtime = AssyLineRuntime(config=make_fast_config())
        seed_one(runtime)
        adapter = AssySubLineAdapter(scope_path=sub_line_path("ASSY-SL01"), runtime=runtime)
        coord = _coordinator(build_tipa_workspace())
        coord.register(adapter)
        # First reach 20, then request a backward target -> fail closed
        # (the coordinator rejects a participant already ahead of the boundary).
        assert coord.run_window("w1", 20.0).status == "completed"
        outcome = coord.run_window("w2", 10.0)
        assert outcome.status == "failed"
        assert "ahead of boundary" in (outcome.failure or "")


# ═══════════════════════════════════════════════════════════
# E — Standalone vs federated semantic parity (test 6)
# ═══════════════════════════════════════════════════════════

class TestStandaloneFederatedParity:
    def _make_seeded_runtime(self):
        runtime = AssyLineRuntime(config=copy.deepcopy(make_fast_config()))
        seed_one(runtime)
        return runtime

    def _run_standalone(self, steps: int) -> AssyLineRuntime:
        runtime = self._make_seeded_runtime()
        for _ in range(steps):
            natural_cycle(runtime)
        return runtime

    def _run_federated(self, target_time_s: float) -> AssyLineRuntime:
        runtime = self._make_seeded_runtime()
        adapter = AssySubLineAdapter(
            scope_path=sub_line_path("ASSY-SL01"), runtime=runtime
        )
        coord = _coordinator(build_tipa_workspace())
        coord.register(adapter)
        outcome = coord.run_window("w1", target_time_s)
        assert outcome.status == "completed", outcome.failure
        return runtime

    def test_representative_release_scenario_parity(self):
        """Same runtime semantics: standalone vs federated to a RELEASED motor."""
        steps = 16  # fast config: reaches AP11 + final QC + release
        standalone = self._run_standalone(steps)
        federated = self._run_federated(standalone.simulation_time_s)
        assert standalone.simulation_time_s == 160.0
        assert federated.simulation_time_s == standalone.simulation_time_s
        assert released_ids(standalone) == ("MTR-0001",)
        assert released_ids(federated) == released_ids(standalone)
        assert canonical_state(standalone) == canonical_state(federated)

    def test_mid_line_join_parity(self):
        """Parity through AP04 JOIN genealogy on a shorter supported boundary."""
        steps = 7
        standalone = self._run_standalone(steps)
        federated = self._run_federated(standalone.simulation_time_s)
        assert standalone.motor_count == 1
        assert len(standalone.genealogy.all_records()) >= 1
        assert canonical_state(standalone) == canonical_state(federated)

    def test_real_config_six_subline_replica_parity(self):
        """Hosting six REAL config runtimes federated (one shared natural dwell
        boundary) equals each sub-line's standalone replica, given EXPLICIT
        equivalent initial conditions on both arms."""
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        for sub_line_id in SUB_LINE_IDS:
            seed_like_demo(host.runtime(sub_line_id))  # explicit prep
        coord = host.make_coordinator()
        outcome = host.run_window(coord, 120.0)
        assert outcome.status == "completed"
        for sub_line_id in SUB_LINE_IDS:
            replica = host.standalone_replica(sub_line_id)
            seed_like_demo(replica)
            natural_cycle(replica)
            assert canonical_state(replica) == canonical_state(host.runtime(sub_line_id))


# ═══════════════════════════════════════════════════════════
# F — Isolation + no cross-scope mutation (tests 7, 8)
# ═══════════════════════════════════════════════════════════

class TestIsolation:
    def test_per_subline_config_and_rng_seed_isolated(self):
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        seeds = {sl.config.random_seed for sl in host.sub_lines.values()}
        assert len(seeds) == 6  # distinct ordinal seeds
        ap06_ids = {id(sl.config.quality.ap06) for sl in host.sub_lines.values()}
        assert len(ap06_ids) == 6  # nested quality configs are isolated

    def test_wip_feed_state_isolated_per_runtime(self):
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        base_buffers = {
            sid: host.runtime(sid).rso2_buffer_size for sid in SUB_LINE_IDS
        }
        # Produce an RSO2 WIP in SL01 only -> only SL01's buffer changes.
        host.runtime("ASSY-SL01").produce_rso2_wip()
        assert host.runtime("ASSY-SL01").rso2_buffer_size == base_buffers["ASSY-SL01"] + 1
        for sid in SUB_LINE_IDS[1:]:
            assert host.runtime(sid).rso2_buffer_size == base_buffers[sid]

    def test_no_cross_scope_mutation_when_single_subline_advanced(self):
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        seed_like_demo(host.runtime("ASSY-SL01"))  # prepare only SL01
        others = {sid: canonical_state(host.runtime(sid)) for sid in SUB_LINE_IDS[1:]}
        coord = host.make_coordinator()
        outcome = host.run_window(coord, 120.0, sub_line_ids=["ASSY-SL01"])
        assert outcome.status == "completed"
        # Only SL01 advanced; every other context is untouched.
        assert host.runtime("ASSY-SL01").simulation_time_s == 120.0
        for sid, state in others.items():
            assert canonical_state(host.runtime(sid)) == state
            assert host.runtime(sid).simulation_time_s == 0.0


# ═══════════════════════════════════════════════════════════
# G — Identity drift / mismatch fails closed via G4 rules (test 9)
# ═══════════════════════════════════════════════════════════

class _FlipScopeDuringAdvance:
    """Delegating adapter: reports the real scope BEFORE advance, then flips
    ``scope_path`` to ``flip_to`` DURING ``advance_to()`` (after the wrapped
    runtime has advanced). The G4 C03 post-advance identity re-read must fail
    the window."""

    def __init__(self, inner: AssySubLineAdapter, flip_to) -> None:
        self._inner = inner
        self._flip_to = flip_to
        self._flipped = False

    @property
    def scope_path(self):
        return self._flip_to if self._flipped else self._inner.scope_path

    @property
    def current_time_s(self):
        return self._inner.current_time_s

    def advance_to(self, target_time_s):
        result = self._inner.advance_to(target_time_s)
        self._flipped = True
        return result

    def commit_transfers(self, inbound):
        return self._inner.commit_transfers(inbound)


class TestIdentityFailClosed:
    def test_drift_during_advance_fails_closed(self):
        """Registered SL01; coherent pre-advance; drifts to SL02 DURING
        advance_to() -> existing G4 C03 rule fails the window."""
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        coord = host.make_coordinator()
        drifter = _FlipScopeDuringAdvance(
            host.adapter("ASSY-SL01"), sub_line_path("ASSY-SL02")
        )
        coord.register(drifter)
        outcome = coord.run_window("w1", 120.0)
        assert outcome.status == "failed"
        assert "changed during advance_to" in (outcome.failure or "")
        assert "drifted" in (outcome.failure or "")
        assert outcome.committed == ()

    def test_invalid_scope_type_during_advance_fails_closed(self):
        """Drifts to a non-StructuralPath DURING advance_to() -> fail closed."""
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        coord = host.make_coordinator()
        drifter = _FlipScopeDuringAdvance(
            host.adapter("ASSY-SL01"), "TIPA/ASSY/ASSY-SL01"
        )
        coord.register(drifter)
        outcome = coord.run_window("w1", 120.0)
        assert outcome.status == "failed"
        assert "changed during advance_to" in (outcome.failure or "")
        assert "not a StructuralPath" in (outcome.failure or "")
        assert outcome.committed == ()

    def test_coherent_identity_across_advance_remains_accepted(self):
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        coord = host.make_coordinator()
        outcome = host.run_window(coord, 120.0, sub_line_ids=["ASSY-SL01"])
        assert outcome.status == "completed"
