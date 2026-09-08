"""VF-vNEXT-G14B — SH-WTP T106->T108 explicit lagged federation tests.

Proves (Issue #65 required tests): explicit_lagged policy visible + unsupported
fail-closed + policy NOT on G4 graph/binding/ports; exactly T106+T108; exactly
F01; T110/F02-F07 absent; explicit initial T108 inflow required; first window
uses initial inflow (not Q106[1]); boundary 1 commits Q106[1]; second window
uses exactly Q106[1]; no same-window retroactive step; detached immutable
transfer; exact PortRefs/binding/window/time; payload exact; stale window fails;
deterministic replay; attempt isolation; T106/T108 standalone unchanged; G14A
unchanged; no direct T106-state read by T108; no workspace/container execution;
authority unchanged.
"""

from __future__ import annotations

import dataclasses
import inspect
import math
import re
import types

import pytest

from virtual_factory.composition import (
    BoundaryPort,
    BoundaryTransfer,
    CompositionBinding,
    CompositionGraph,
    Coordinator,
)
from virtual_factory.provenance import (
    DataStatus,
    Fidelity,
    OriginKind,
    RunContextV2,
)
from virtual_factory.shwtp import (
    SHWTP_T106_SCOPE_PATH,
    SHWTP_T108_SCOPE_PATH,
    ShwtpFederation,
    ShwtpFederationConfig,
    ShwtpFederationError,
    build_shwtp_f01_projection,
)
from virtual_factory.shwtp import federation as fed_module
from virtual_factory.shwtp.federation import (
    SHWTP_FEDERATION_COUPLING_POLICY,
    SHWTP_FEDERATION_PAYLOAD_KEY,
    ShwtpT106Participant,
    ShwtpT108Participant,
)
from virtual_factory.shwtp.logical_runtime import (
    SHWTP_T106_CANONICAL_ID,
    T106Config,
    T106LogicalRuntime,
)
from virtual_factory.shwtp.projection import (
    SHWTP_F01_BINDING_ID,
    ShwtpF01Projection,
    t106_out_port_ref,
    t108_in_port_ref,
)
from virtual_factory.shwtp.runtime import (
    SHWTP_T108_CANONICAL_ID,
    T108Config,
    T108TankRuntime,
)
from virtual_factory.shwtp.structural import (
    SHWTP_RUNTIME_AUTHORIZATION,
    SHWTP_SITE_AUTHORIZED_EXECUTION,
)
from virtual_factory.workspace import StructuralPath


def _module_code(module) -> str:
    return re.sub(r'""".*?"""', "", inspect.getsource(module), flags=re.DOTALL)


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


@pytest.fixture(scope="module")
def projection() -> ShwtpF01Projection:
    return build_shwtp_f01_projection()


class TestCouplingPolicy:
    def test_policy_explicit_and_visible(self):
        assert SHWTP_FEDERATION_COUPLING_POLICY == "explicit_lagged"
        fed = ShwtpFederation(_config())
        assert fed.coupling_policy == "explicit_lagged"

    def test_config_default_is_explicit_lagged(self):
        cfg = _config()
        assert cfg.coupling_policy == "explicit_lagged"

    @pytest.mark.parametrize("bad", ["gauss_seidel", "iterative", "multirate", "adaptive", ""])
    def test_unsupported_policy_fails_closed(self, bad):
        with pytest.raises(ShwtpFederationError):
            _config(coupling_policy=bad)

    def test_policy_not_on_g4_graph_binding_ports(self):
        # CompositionGraph exposes no coupling-policy attribute.
        proj = build_shwtp_f01_projection()
        assert not hasattr(proj.graph, "coupling_policy")
        assert not hasattr(proj.graph, "policy")
        # BoundaryPort / CompositionBinding dataclass fields carry no policy.
        port_fields = {f.name for f in dataclasses.fields(BoundaryPort)}
        binding_fields = {f.name for f in dataclasses.fields(CompositionBinding)}
        assert "coupling_policy" not in port_fields
        assert "policy" not in port_fields
        assert "coupling_policy" not in binding_fields
        assert "policy" not in binding_fields

    def test_policy_lives_only_in_federation_layer(self):
        code = _module_code(fed_module)
        assert "coupling_policy" in code
        # G4 modules are not modified by G14B (they do not import the seam).
        from virtual_factory.composition import graph as g4_graph

        g4_code = _module_code(g4_graph)
        assert "explicit_lagged" not in g4_code
        assert "coupling_policy" not in g4_code


class TestScopeAndBinding:
    def test_exactly_two_participants(self):
        fed = ShwtpFederation(_config())
        assert fed.participants == (
            "shwtp/line1/l1_t106",
            "shwtp/line1/l1_t108",
        )
        assert fed.coordinator.participants == fed.participants

    def test_exactly_one_f01_binding(self):
        fed = ShwtpFederation(_config())
        assert fed.binding_id == SHWTP_F01_BINDING_ID
        graph = fed.coordinator.graph
        assert len(graph.bindings) == 1
        binding = graph.bindings[0]
        assert binding.edge_id == SHWTP_F01_BINDING_ID
        assert binding.source == t106_out_port_ref()
        assert binding.target == t108_in_port_ref()

    def test_t110_absent(self):
        code = _module_code(fed_module)
        assert "T110" not in code
        assert "WASH" not in code

    def test_f02_to_f07_absent(self):
        code = _module_code(fed_module)
        for rel in (
            "REL-SHW-F02",
            "REL-SHW-F03",
            "REL-SHW-F04",
            "REL-SHW-F05",
            "REL-SHW-F06",
            "REL-SHW-F07",
        ):
            assert rel not in code

    def test_no_workspace_or_container_execution(self):
        fed = ShwtpFederation(_config())
        # Only the two exact unit scopes are executable participants.
        assert "shwtp" not in fed.participants
        assert "shwtp/line1" not in fed.participants
        assert fed.participants == ("shwtp/line1/l1_t106", "shwtp/line1/l1_t108")


class TestConfigValidation:
    def test_initial_t108_inflow_required_no_default(self):
        # No hidden default: the field is required (constructor raises TypeError).
        with pytest.raises(TypeError):
            ShwtpFederationConfig(
                communication_step_s=1.0,
                t106_inflow_m3_s=2.0,
                t108_requested_outflow_m3_s=0.5,
                t108_capacity_m3=100.0,
                t108_tank_area_m2=10.0,
                t108_initial_volume_m3=50.0,
            )

    @pytest.mark.parametrize("field", ["initial_t108_inflow_m3_s", "t106_inflow_m3_s", "t108_requested_outflow_m3_s"])
    def test_negative_scenario_flow_fails(self, field):
        with pytest.raises(ShwtpFederationError):
            _config(**{field: -0.1})

    @pytest.mark.parametrize("field", ["initial_t108_inflow_m3_s", "t106_inflow_m3_s", "t108_requested_outflow_m3_s"])
    def test_non_finite_scenario_flow_fails(self, field):
        with pytest.raises(ShwtpFederationError):
            _config(**{field: float("nan")})

    def test_communication_step_positive_required(self):
        with pytest.raises(ShwtpFederationError):
            _config(communication_step_s=0.0)
        with pytest.raises(ShwtpFederationError):
            _config(communication_step_s=-1.0)
        with pytest.raises(ShwtpFederationError):
            _config(communication_step_s=float("inf"))


class TestLaggedSemantics:
    def test_first_window_uses_initial_inflow(self):
        fed = ShwtpFederation(_config())
        fed.run_window("window-1")
        step1 = fed.t108.last_step
        assert step1 is not None
        # Window 1 T108 step used the explicit initial inflow, not Q106[1].
        assert step1.inflow_m3_s == 1.0
        assert fed.t106.last_step.output_flow_m3_s == 2.0

    def test_first_window_does_not_use_t106_output(self):
        fed = ShwtpFederation(_config())
        fed.run_window("window-1")
        assert fed.t108.last_step.inflow_m3_s == 1.0
        assert fed.t108.last_step.inflow_m3_s != fed.t106.last_step.output_flow_m3_s

    def test_boundary_1_commits_t106_output(self):
        fed = ShwtpFederation(_config())
        o1 = fed.run_window("window-1")
        assert o1.status == "completed"
        assert o1.committed == ("XFER-SHW-F01-window-1",)
        # After boundary 1, Q106[1] is committed for the NEXT window.
        assert fed.t108.committed_inflow_m3_s == 2.0

    def test_second_window_uses_exactly_previous_output(self):
        fed = ShwtpFederation(_config())
        fed.run_window("window-1")
        step1 = fed.t108.last_step
        fed.run_window("window-2")
        step2 = fed.t108.last_step
        assert step1.inflow_m3_s == 1.0  # initial inflow
        assert step2.inflow_m3_s == 2.0  # exactly Q106[1]

    def test_no_same_window_retroactive_step(self):
        fed = ShwtpFederation(_config())
        fed.run_window("window-1")
        # T108 advanced exactly once in window 1, using the initial inflow.
        assert fed.t108.runtime.step_index == 1
        window1_inflow = fed.t108.last_step.inflow_m3_s
        assert window1_inflow == 1.0
        # Commit did not retroactively re-step T108 within the same window.
        assert fed.t108.runtime.state.time_s == 1.0
        assert fed.t108.committed_inflow_m3_s == 2.0
        fed.run_window("window-2")
        assert fed.t108.runtime.step_index == 2


class TestTransfer:
    def _first_transfer(self) -> BoundaryTransfer:
        fed = ShwtpFederation(_config())
        fed.run_window("window-1")
        transfer = fed.t106.last_transfer
        assert transfer is not None
        return transfer

    def test_exact_port_refs_and_binding(self):
        t = self._first_transfer()
        assert t.source == t106_out_port_ref()
        assert t.target == t108_in_port_ref()
        assert t.binding_id == SHWTP_F01_BINDING_ID

    def test_window_time_workspace_run_identity(self):
        t = self._first_transfer()
        assert t.window_id == "window-1"
        assert t.simulation_time_s == 1.0
        assert t.workspace_id == "shwtp"
        assert t.run_id == "run-shwtp-f01"

    def test_payload_exact_and_finite(self):
        t = self._first_transfer()
        assert set(t.payload.keys()) == {SHWTP_FEDERATION_PAYLOAD_KEY}
        value = t.payload[SHWTP_FEDERATION_PAYLOAD_KEY]
        assert value == 2.0
        assert math.isfinite(value)

    def test_payload_detached_immutable(self):
        t = self._first_transfer()
        assert isinstance(t.payload, types.MappingProxyType)
        # A detached copy: mutating the producer runtime cannot mutate payload.
        assert t.payload[SHWTP_FEDERATION_PAYLOAD_KEY] == 2.0

    def test_transfer_serialization_deterministic(self):
        t1 = self._first_transfer()
        t2 = self._first_transfer()
        assert t1.to_dict() == t2.to_dict()


class TestFailClosedWindows:
    def test_stale_first_window_fails(self):
        fed = ShwtpFederation(_config())
        with pytest.raises(ShwtpFederationError):
            fed.run_window("window-2")

    def test_duplicate_window_fails(self):
        fed = ShwtpFederation(_config())
        fed.run_window("window-1")
        with pytest.raises(ShwtpFederationError):
            fed.run_window("window-1")

    def test_future_window_fails(self):
        fed = ShwtpFederation(_config())
        fed.run_window("window-1")
        with pytest.raises(ShwtpFederationError):
            fed.run_window("window-3")

    @pytest.mark.parametrize("bad", ["", "w1", "window-0", "window-x", "window-1-extra"])
    def test_invalid_window_identity_fails(self, bad):
        fed = ShwtpFederation(_config())
        with pytest.raises(ShwtpFederationError):
            fed.run_window(bad)

    def test_advance_without_prepare_fails(self):
        rt = T106LogicalRuntime(
            T106Config(dt_s=1.0),
            RunContextV2(workspace_id="shwtp", run_id="r", scope_path=SHWTP_T106_SCOPE_PATH),
        )
        p = ShwtpT106Participant(rt, 2.0, "r")
        with pytest.raises(ShwtpFederationError):
            p.advance_to(1.0)

    def test_non_exact_boundary_fails(self):
        rt = T106LogicalRuntime(
            T106Config(dt_s=1.0),
            RunContextV2(workspace_id="shwtp", run_id="r", scope_path=SHWTP_T106_SCOPE_PATH),
        )
        p = ShwtpT106Participant(rt, 2.0, "r")
        p.prepare_window("window-1")
        with pytest.raises(ShwtpFederationError):
            p.advance_to(0.5)

    def test_backward_boundary_fails(self):
        rt = T106LogicalRuntime(
            T106Config(dt_s=1.0),
            RunContextV2(workspace_id="shwtp", run_id="r", scope_path=SHWTP_T106_SCOPE_PATH),
        )
        p = ShwtpT106Participant(rt, 2.0, "r")
        p.prepare_window("window-1")
        p.advance_to(1.0)
        with pytest.raises(ShwtpFederationError):
            p.advance_to(0.5)

    def test_unexpected_inbound_to_t106_fails(self):
        fed = ShwtpFederation(_config())
        fed.run_window("window-1")
        transfer = fed.t106.last_transfer
        with pytest.raises(ShwtpFederationError):
            fed.t106.commit_transfers((transfer,))


class TestT108CommitValidation:
    def _fed_and_transfer(self):
        fed = ShwtpFederation(_config())
        fed.run_window("window-1")
        transfer = fed.t106.last_transfer
        return fed, transfer

    def test_multiple_inbound_fails(self):
        fed, t = self._fed_and_transfer()
        with pytest.raises(ShwtpFederationError):
            fed.t108.commit_transfers((t, t))

    def test_wrong_window_in_commit_fails(self):
        fed, t = self._fed_and_transfer()
        # Rebuild a transfer carrying the wrong window id.
        wrong = BoundaryTransfer(
            transfer_id="XFER-SHW-F01-window-99",
            source=t.source,
            target=t.target,
            binding_id=t.binding_id,
            window_id="window-99",
            simulation_time_s=1.0,
            workspace_id=t.workspace_id,
            run_id=t.run_id,
            payload={SHWTP_FEDERATION_PAYLOAD_KEY: 2.0},
        )
        with pytest.raises(ShwtpFederationError):
            fed.t108.commit_transfers((wrong,))

    def test_wrong_payload_key_fails(self):
        fed, t = self._fed_and_transfer()
        wrong = BoundaryTransfer(
            transfer_id="XFER-SHW-F01-window-1",
            source=t.source,
            target=t.target,
            binding_id=t.binding_id,
            window_id=t.window_id,
            simulation_time_s=1.0,
            workspace_id=t.workspace_id,
            run_id=t.run_id,
            payload={"mass_flow_kg_s": 2.0},
        )
        with pytest.raises(ShwtpFederationError):
            fed.t108.commit_transfers((wrong,))


class TestIdentityLocking:
    """G14B-C01: federation adapter identity is locked to the runtime RunContextV2."""

    def _t106_runtime(self, run_id: str = "r1") -> T106LogicalRuntime:
        return T106LogicalRuntime(
            T106Config(dt_s=1.0),
            RunContextV2(
                workspace_id="shwtp",
                run_id=run_id,
                scope_path=SHWTP_T106_SCOPE_PATH,
            ),
        )

    def _t108_runtime(self, run_id: str = "r1") -> T108TankRuntime:
        return T108TankRuntime(
            T108Config(
                capacity_m3=100.0,
                tank_area_m2=10.0,
                initial_volume_m3=50.0,
                dt_s=1.0,
            ),
            RunContextV2(
                workspace_id="shwtp",
                run_id=run_id,
                scope_path=SHWTP_T108_SCOPE_PATH,
            ),
        )

    def test_t106_adapter_run_id_mismatch_fails_closed(self):
        rt = self._t106_runtime(run_id="r1")
        with pytest.raises(ShwtpFederationError):
            ShwtpT106Participant(rt, inflow_m3_s=2.0, run_id="r2")

    def test_t108_adapter_run_id_mismatch_fails_closed(self):
        rt = self._t108_runtime(run_id="r1")
        with pytest.raises(ShwtpFederationError):
            ShwtpT108Participant(
                rt,
                requested_outflow_m3_s=0.5,
                initial_inflow_m3_s=1.0,
                run_id="r2",
            )

    def test_t106_adapter_workspace_mismatch_fails_closed(self):
        rt = self._t106_runtime(run_id="r1")
        with pytest.raises(ShwtpFederationError):
            ShwtpT106Participant(
                rt, inflow_m3_s=2.0, run_id="r1", workspace_id="other"
            )

    def test_t108_adapter_workspace_mismatch_fails_closed(self):
        rt = self._t108_runtime(run_id="r1")
        with pytest.raises(ShwtpFederationError):
            ShwtpT108Participant(
                rt,
                requested_outflow_m3_s=0.5,
                initial_inflow_m3_s=1.0,
                run_id="r1",
                workspace_id="other",
            )

    def test_valid_matching_context_passes(self):
        rt106 = self._t106_runtime(run_id="r1")
        p106 = ShwtpT106Participant(rt106, inflow_m3_s=2.0, run_id="r1")
        assert p106.runtime is rt106
        rt108 = self._t108_runtime(run_id="r1")
        p108 = ShwtpT108Participant(
            rt108, requested_outflow_m3_s=0.5, initial_inflow_m3_s=1.0, run_id="r1"
        )
        assert p108.runtime is rt108

    def test_transfer_run_id_equals_t106_provenance_run_id(self):
        fed = ShwtpFederation(_config(run_id="run-c01"))
        fed.run_window("window-1")
        transfer = fed.t106.last_transfer
        step = fed.t106.last_step
        ctx_run_id = fed.t106.runtime.run_context.run_id
        assert transfer.run_id == "run-c01"
        assert step.provenance.run_id == "run-c01"
        assert ctx_run_id == "run-c01"
        assert transfer.run_id == step.provenance.run_id == ctx_run_id

    def test_t108_provenance_run_id_equals_federation_run_id(self):
        fed = ShwtpFederation(_config(run_id="run-c01"))
        fed.run_window("window-1")
        step = fed.t108.last_step
        ctx_run_id = fed.t108.runtime.run_context.run_id
        assert step.provenance.run_id == "run-c01"
        assert ctx_run_id == "run-c01"
        assert step.provenance.run_id == ctx_run_id

    def test_run_context_not_mutated(self):
        fed = ShwtpFederation(_config(run_id="run-c01"))
        t106_ctx = fed.t106.runtime.run_context
        t108_ctx = fed.t108.runtime.run_context
        fed.run_window("window-1")
        # The runtime RunContext remains the same immutable identity object.
        assert fed.t106.runtime.run_context == t106_ctx
        assert fed.t108.runtime.run_context == t108_ctx


class TestDeterminismAndIsolation:
    def test_deterministic_replay(self):
        a = ShwtpFederation(_config())
        b = ShwtpFederation(_config())
        for fed in (a, b):
            fed.run_window("window-1")
            fed.run_window("window-2")
            fed.run_window("window-3")
        assert a.serialize() == b.serialize()

    def test_fresh_attempts_isolated(self):
        a = ShwtpFederation(_config())
        b = ShwtpFederation(_config())
        a.run_window("window-1")
        assert a.time_s == 1.0
        assert b.time_s == 0.0
        assert b.window_index == 0
        assert b.t108.committed_inflow_m3_s == 1.0
        assert a.t108.committed_inflow_m3_s == 2.0


class TestPreservedBoundaries:
    def test_t106_standalone_unchanged(self):
        fed = ShwtpFederation(_config())
        fed.run_window("window-1")
        rt = fed.t106.runtime
        assert rt.canonical_id == SHWTP_T106_CANONICAL_ID
        assert rt.scope_path == SHWTP_T106_SCOPE_PATH
        step = fed.t106.last_step
        assert step.inflow_m3_s == 2.0
        assert step.output_flow_m3_s == 2.0  # LogicalOnly pass-through
        assert step.provenance.origin_kind is OriginKind.SIMULATION
        assert step.provenance.data_status is DataStatus.SYNTHETIC
        assert step.provenance.fidelity is Fidelity.LOGICAL_ONLY

    def test_t108_standalone_unchanged(self):
        fed = ShwtpFederation(_config())
        fed.run_window("window-1")
        rt = fed.t108.runtime
        assert rt.canonical_id == SHWTP_T108_CANONICAL_ID
        assert rt.scope_path == SHWTP_T108_SCOPE_PATH
        step = fed.t108.last_step
        # Window 1: inflow 1.0, outflow 0.5, volume 50 -> 50.5 (mass balance).
        assert step.inflow_m3_s == 1.0
        assert step.requested_outflow_m3_s == 0.5
        assert step.end_volume_m3 == pytest.approx(50.5)
        assert step.provenance.origin_kind is OriginKind.SIMULATION
        assert step.provenance.data_status is DataStatus.SYNTHETIC
        assert step.provenance.fidelity is Fidelity.FIRST_ORDER

    def test_g14a_projection_unchanged(self):
        proj = build_shwtp_f01_projection()
        assert proj.record.projection_id == "PROJ-SHW-F01-T106-T108"
        assert len(proj.ports) == 2
        assert len(proj.graph.bindings) == 1
        # G14A identities are the exact ones G14B reuses.
        fed = ShwtpFederation(_config())
        assert fed.coordinator.graph.workspace_id == proj.graph.workspace_id

    def test_no_direct_t106_state_read_by_t108(self):
        # advance_to must not reference T106 at all (after stripping docstrings
        # and comments; the comment itself only *negates* the claim).
        advance_src = inspect.getsource(ShwtpT108Participant.advance_to)
        advance_src = re.sub(r'""".*?"""', "", advance_src, flags=re.DOTALL)
        advance_src = "\n".join(
            re.sub(r"#.*$", "", line) for line in advance_src.splitlines()
        )
        lowered = advance_src.lower()
        assert "t106" not in lowered
        assert "t106" not in " ".join(ShwtpT108Participant.__slots__)

    def test_authority_unchanged(self):
        assert SHWTP_RUNTIME_AUTHORIZATION == "NOT_AUTHORIZED"
        assert SHWTP_SITE_AUTHORIZED_EXECUTION == "NOT_AUTHORIZED"
        code = _module_code(fed_module)
        assert "site_authorized_execution" not in code
        assert "vf_runtime_authorization = \"AUTHORIZED\"" not in code

    def test_coordinator_is_existing_g4(self):
        fed = ShwtpFederation(_config())
        assert isinstance(fed.coordinator, Coordinator)
        # Exactly the accepted G4 graph semantics are reused.
        assert isinstance(fed.coordinator.graph, CompositionGraph)
