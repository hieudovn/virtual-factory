"""VF-vNEXT-G14A — SH-WTP T106->T108 runtime projection contract tests.

Proves (Issue #64 required tests): exactly one projection, only REL-SHW-F01, exact
PIM endpoints, exact T106/T108 paths, exactly two BoundaryPorts (OUT/IN, MATERIAL,
m3/s, volumetric_flow), compatibility PASS, exactly one CompositionBinding,
deterministic graph + serialization, VF-local PortRefs, no generic FLOWS_TO
auto-projection, F02-F07 absent, T110 absent, T106/T108 state unchanged on
construct/inspect, no coordinator/run-control execution.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import pytest

from virtual_factory.composition import (
    CompositionGraph,
    PortCategory,
    PortDirection,
    check_port_compatibility,
)
from virtual_factory.provenance import RunContextV2
from virtual_factory.shwtp import (
    SHWTP_T106_SCOPE_PATH,
    SHWTP_T108_SCOPE_PATH,
    ShwtpF01Projection,
    build_shwtp_f01_projection,
    f01_binding,
    t106_out_port,
    t108_in_port,
)
from virtual_factory.shwtp import projection as proj_module
from virtual_factory.shwtp.logical_runtime import (
    SHWTP_T106_CANONICAL_ID,
    T106Config,
    T106LogicalRuntime,
)
from virtual_factory.shwtp.runtime import (
    SHWTP_T108_CANONICAL_ID,
    T108Config,
    T108TankRuntime,
)
from virtual_factory.workspace import StructuralPath


def _module_code(module) -> str:
    return re.sub(r'""".*?"""', "", inspect.getsource(module), flags=re.DOTALL)


def _t106_ctx():
    return RunContextV2(
        workspace_id="shwtp", run_id="r1", scope_path=SHWTP_T106_SCOPE_PATH
    )


def _t108_ctx():
    return RunContextV2(
        workspace_id="shwtp", run_id="r2", scope_path=SHWTP_T108_SCOPE_PATH
    )


@pytest.fixture(scope="module")
def projection() -> ShwtpF01Projection:
    return build_shwtp_f01_projection()


class TestProjectionRecord:
    def test_exactly_one_projection(self, projection):
        assert projection.record.projection_id
        assert projection.record.projection_id == "PROJ-SHW-F01-T106-T108"

    def test_references_only_f01(self, projection):
        assert projection.record.relation_id == "REL-SHW-F01"
        assert projection.record.relation_type == "FLOWS_TO"
        assert projection.record.evidence_status == "DocumentConfirmed"

    def test_exact_pim_endpoints(self, projection):
        assert projection.record.pim_source_endpoint == "PROC-SHW-L1-T106-OUT-FLOW"
        assert projection.record.pim_target_endpoint == "PROC-SHW-L1-T108-IN-FLOW"

    def test_exact_vf_paths(self, projection):
        assert projection.record.vf_source_path == "shwtp/line1/l1_t106"
        assert projection.record.vf_target_path == "shwtp/line1/l1_t108"

    def test_authorization_scope_and_disclaimer(self, projection):
        assert "CANDIDATE_SCOPED" in projection.record.authorization_scope
        assert "NOT_AUTHORIZED" in projection.record.disclaimer
        assert "site" in projection.record.disclaimer.lower()
        assert projection.record.pim_authority == "hieudovn/plant-intelligence-model"
        assert projection.record.pim_main_sha == "ec7f1266d4a19e5201b689874a2a7a75a022fc5c"


class TestPorts:
    def test_exactly_two_ports(self, projection):
        assert len(projection.ports) == 2

    def test_source_out_target_in(self, projection):
        src, tgt = projection.ports
        assert src.direction is PortDirection.OUT
        assert tgt.direction is PortDirection.IN

    def test_material_category_unit_descriptor(self, projection):
        for port in projection.ports:
            assert port.category is PortCategory.MATERIAL
            assert port.unit == "m3/s"
            assert port.descriptor == "volumetric_flow"

    def test_compatibility_passes(self, projection):
        src, tgt = projection.ports
        check_port_compatibility(src, tgt)  # no exception == PASS

    def test_port_refs_are_vf_local_not_pim_canonical(self, projection):
        for port in projection.ports:
            ref = port.ref
            assert "PROC-SHW" not in ref.as_string()
            assert "out_flow" in ref.as_string() or "in_flow" in ref.as_string()
            assert ref.owner_scope.workspace_id == "shwtp"

    def test_port_owner_scopes_exact(self, projection):
        src, tgt = projection.ports
        assert src.ref.owner_scope == SHWTP_T106_SCOPE_PATH
        assert tgt.ref.owner_scope == SHWTP_T108_SCOPE_PATH


class TestBindingAndGraph:
    def test_exactly_one_binding(self, projection):
        assert projection.binding.edge_id == "BIND-SHW-F01-T106-OUT-T108-IN"
        assert projection.binding.source == t106_out_port().ref
        assert projection.binding.target == t108_in_port().ref

    def test_graph_valid_and_deterministic(self, projection):
        assert isinstance(projection.graph, CompositionGraph)
        assert projection.graph.workspace_id == "shwtp"
        assert len(projection.graph.bindings) == 1
        again = build_shwtp_f01_projection()
        assert projection.serialize() == again.serialize()

    def test_serialization_deterministic_and_complete(self, projection):
        data = projection.serialize()
        assert data["schema"].startswith("vf.vnext.g14a")
        assert len(data["ports"]) == 2
        assert len(data["bindings"]) == 1
        assert data["bindings"][0]["source"] == "shwtp/line1/l1_t106#out_flow"
        assert data["bindings"][0]["target"] == "shwtp/line1/l1_t108#in_flow"


class TestNoAutoProjection:
    def test_no_generic_flows_to_auto_projection(self):
        code = _module_code(proj_module)
        assert "def project_relation" not in code
        assert "def auto_project" not in code
        # only the fixed F01 builder exists
        assert "def build_shwtp_f01_projection" in code

    def test_f02_to_f07_not_projected(self):
        code = _module_code(proj_module)
        for rel in ("REL-SHW-F02", "REL-SHW-F03", "REL-SHW-F04", "REL-SHW-F05", "REL-SHW-F06", "REL-SHW-F07"):
            assert rel not in code

    def test_t110_absent(self):
        code = _module_code(proj_module)
        assert "T110" not in code
        assert "UNIT-SHW-WASH-T110" not in code


class TestInertness:
    def test_no_execution_api(self):
        code = _module_code(proj_module)
        for token in ("def advance", "def step", "Coordinator", "RunLifecycleService", "transfer"):
            assert token not in code
        for token in ("from virtual_factory.runcontrol",):
            assert token not in code

    def test_construct_does_not_mutate_t106_or_t108_state(self):
        t106 = T106LogicalRuntime(T106Config(dt_s=1.0), _t106_ctx())
        t108 = T108TankRuntime(
            T108Config(capacity_m3=100.0, tank_area_m2=10.0, initial_volume_m3=50.0, dt_s=1.0),
            _t108_ctx(),
        )
        t106_before = t106.state
        t108_before = t108.state
        build_shwtp_f01_projection().serialize()
        assert t106.state == t106_before
        assert t108.state == t108_before
        # canonical ids unchanged and locked
        assert t106.canonical_id == SHWTP_T106_CANONICAL_ID
        assert t108.canonical_id == SHWTP_T108_CANONICAL_ID

    def test_t106_t108_runtimes_unchanged(self):
        t106 = T106LogicalRuntime(T106Config(dt_s=1.0), _t106_ctx())
        rec = t106.step(3.0)
        assert rec.output_flow_m3_s == pytest.approx(3.0)
        t108 = T108TankRuntime(
            T108Config(capacity_m3=100.0, tank_area_m2=10.0, initial_volume_m3=50.0, dt_s=1.0),
            _t108_ctx(),
        )
        rec108 = t108.step(2.0, 0.0)
        assert rec108.end_volume_m3 == pytest.approx(52.0)
