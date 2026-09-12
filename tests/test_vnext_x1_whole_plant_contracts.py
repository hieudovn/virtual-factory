"""VF-SHW-X1 — whole-plant contract layer validation (contract-only gate).

Validates the ten required X1 validations:
  1 deterministic + schema-valid graph;
  2 every PIM canonical id referenced already exists in the accepted inventory;
  3 every assumed edge carries explicit VF assumption provenance;
  4 no edge is simultaneously PIM-known and VF-assumed under the same identity;
  5 every X2-admitted executable scope has a complete process contract;
  6 every X2 C1 control has a complete control contract;
  7 every X3/X4 loop is explicitly deferred and inactive in X2;
  8 no runtime/session/controller/engine construction is added;
  9 existing baseline groups remain green (proved by the baseline run, not here);
 10 the full suite remains green (same).

It also proves the frozen path coverage from X0 (RAW-WATER/T100, LINE1
T101..T108, DIST-P108, CHEMICAL, SLUDGE, WASH-T110, LINE2 aggregate,
ELECTRICAL/AUTOMATION reference-only).
"""

from __future__ import annotations

import importlib
import inspect
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from virtual_factory.shwtp import contracts as shwtp_contracts  # noqa: E402
from virtual_factory.shwtp.contracts import (  # noqa: E402
    CONTROL_SCHEMA,
    EDGE_CATEGORIES,
    FIDELITY_CLASSES,
    GRAPH_SCHEMA,
    ADMISSION_SCHEMA,
    PROCESS_SCHEMA,
    ShwtpContractError,
    accepted_canonical_ids,
    iter_vf_local_ids,
    load_whole_plant_contracts,
    pim_ids_referenced_by_contracts,
    referenced_vf_local_ids,
)

CONFIG_DIR = ROOT / "configs" / "vnext" / "shwtp"
GRAPH_PATH = CONFIG_DIR / "shwtp_whole_plant_graph_v1.json"
PROCESS_PATH = CONFIG_DIR / "shwtp_process_contracts_v1.json"
CONTROL_PATH = CONFIG_DIR / "shwtp_control_contracts_v1.json"
ADMISSION_PATH = CONFIG_DIR / "shwtp_x2_admission_manifest_v1.json"

REQUIRED_FLOW_PATH = {
    "AREA-SHW-RAW-WATER": {"UNIT-SHW-RAW-INTAKE", "UNIT-SHW-T100"},
    "AREA-SHW-LINE1": {
        "UNIT-SHW-L1-T101", "UNIT-SHW-L1-T102", "UNIT-SHW-L1-T103",
        "UNIT-SHW-L1-T104", "UNIT-SHW-L1-T105", "UNIT-SHW-L1-T106",
        "UNIT-SHW-L1-T107", "UNIT-SHW-L1-T108", "UNIT-SHW-WASH-T110",
    },
    "AREA-SHW-CHEMICAL": {"UNIT-SHW-CHEM-DOSING"},
    "AREA-SHW-SLUDGE": {"UNIT-SHW-SLUDGE-T201"},
    "AREA-SHW-ELECTRICAL": {"UNIT-SHW-ELEC-MCC"},
    "AREA-SHW-AUTOMATION": {"UNIT-SHW-AUTO-PLC"},
}

RUNTIME_TOKENS = (
    "RunLifecycleService",
    "ExecutionBridge",
    "RuntimeService",
    "SimulationEngine",
    "RunRecord",
    "def advance",
    "def step",
)

PROBED_RUNTIME_TYPES = (
    ("virtual_factory.runcontrol.lifecycle", "RunLifecycleService"),
    ("virtual_factory.runcontrol.session", "RuntimeSession"),
    ("virtual_factory.shwtp.bridge", "ShwtpExecutionBridge"),
    ("virtual_factory.shwtp.runtime", "T108TankRuntime"),
    ("virtual_factory.shwtp.logical_runtime", "T106LogicalRuntime"),
    ("virtual_factory.core.simulation_engine", "SimulationEngine"),
    ("virtual_factory.discrete.engine", "DiscreteSimulationEngine"),
)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def contracts():
    return load_whole_plant_contracts()


@pytest.fixture()
def workdir():
    """A writable scratch directory (the OS temp dir is not writable here)."""
    base = ROOT / ".ai-harness" / "traces"
    base.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="shwx1-", dir=str(base)))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="module")
def graph() -> dict:
    return _read(GRAPH_PATH)


@pytest.fixture(scope="module")
def process_payload() -> dict:
    return _read(PROCESS_PATH)


@pytest.fixture(scope="module")
def control_payload() -> dict:
    return _read(CONTROL_PATH)


@pytest.fixture(scope="module")
def admission_payload() -> dict:
    return _read(ADMISSION_PATH)


# ── 1. schema + coverage + categories ─────────────────────────────────────

class TestGraphContract:
    def test_contract_files_carry_the_frozen_schema_and_gate(self, graph, process_payload, control_payload, admission_payload):
        assert graph["schema"] == GRAPH_SCHEMA
        assert process_payload["schema"] == PROCESS_SCHEMA
        assert control_payload["schema"] == CONTROL_SCHEMA
        assert admission_payload["schema"] == ADMISSION_SCHEMA
        for payload in (graph, process_payload, control_payload, admission_payload):
            assert payload["version"]
            assert payload["gate"] == "VF-SHW-X1"
            assert payload["authority"]["vf_runtime_authorization"] == "NOT_AUTHORIZED"
            assert payload["authority"]["site_authorized_execution"] == "NOT_AUTHORIZED"
            assert payload["authority"]["site_truth"] is False

    def test_frozen_whole_plant_shape_is_pinned(self, contracts):
        categories: dict[str, int] = {}
        for edge in contracts.edges:
            categories[edge.category] = categories.get(edge.category, 0) + 1
        assert len(contracts.nodes) == 19
        assert len(contracts.edges) == 25
        assert categories == {"pim_known": 3, "vf_scenario_assumption": 18, "reference_only": 4}
        assert len(contracts.assumption_ids) == 18
        assert len(contracts.scopes) == 17
        assert len(contracts.controls) == 19
        assert len(contracts.admission.executable_scope_ids) == 16
        assert len(contracts.admission.reference_only_scope_ids) == 3
        assert len(contracts.admission.c1_active_ids) == 9
        # 5 deferred PI/PID loops + the deferred C1 chlorine controller
        assert len(contracts.admission.c2_deferred) == 6
        assert len(contracts.admission.invariants) == 14

    def test_every_edge_has_exactly_one_frozen_category(self, contracts):
        assert contracts.edges
        for edge in contracts.edges:
            assert edge.category in EDGE_CATEGORIES
            if edge.category == "pim_known":
                assert edge.pim_relation_id
                assert edge.assumption_id is None
            elif edge.category == "vf_scenario_assumption":
                assert edge.assumption_id
                assert edge.reversible is True
            else:
                assert edge.pim_relation_id is None
                assert edge.x2_eligible is False

    def test_frozen_operational_path_and_side_streams_are_covered(self, contracts):
        canonical = {node.canonical_id for node in contracts.nodes if node.canonical_id}
        for area, units in REQUIRED_FLOW_PATH.items():
            assert any(node.area_canonical_id == area for node in contracts.nodes), area
            assert units <= canonical, sorted(units - canonical)
        roles = {node.process_role for node in contracts.nodes}
        for role in ("boundary_source", "boundary_sink", "parallel_line_aggregate", "distribution"):
            assert role in roles, role
        assert "UNIT-SHW-DIST-P108" in canonical
        # LINE2 is represented as an aggregate with reference-only internals (no new canonical id)
        line2 = next(node for node in contracts.nodes if node.process_role == "parallel_line_aggregate")
        assert line2.canonical_id is None
        assert set(line2.canonical_refs) == {
            "UNIT-SHW-L2-T101", "UNIT-SHW-L2-T105", "UNIT-SHW-L2-T106", "UNIT-SHW-L2-T108",
        }

    def test_pim_known_edges_are_the_document_confirmed_relations(self, contracts):
        known = {edge.edge_id: edge for edge in contracts.edges if edge.category == "pim_known"}
        assert known, "the frozen path must keep at least the DocumentConfirmed relations"
        assert {edge.pim_relation_id for edge in known.values()} == {
            "REL-SHW-F01", "REL-SHW-F04",
        }
        f01 = next(edge for edge in known.values() if edge.pim_relation_id == "REL-SHW-F01")
        assert f01.evidence_status == "DocumentConfirmed"
        assert f01.x2_eligible is True

    def test_t107_and_reference_areas_stay_out_of_x2(self, contracts):
        by_id = {edge.edge_id: edge for edge in contracts.edges}
        for edge_id in ("vf-shw-edge-t106-t107", "vf-shw-edge-t107-t108", "vf-shw-edge-chem-t107"):
            assert by_id[edge_id].category == "vf_scenario_assumption"
            assert by_id[edge_id].x2_eligible is False, edge_id
        reference = [edge for edge in contracts.edges if edge.category == "reference_only"]
        assert reference, "electrical/automation support links must exist as reference_only"
        assert all(edge.flow == "reference" for edge in reference)
        t107 = next(node for node in contracts.nodes if node.canonical_id == "UNIT-SHW-L1-T107")
        assert t107.x2_eligible is False


# ── 3 + 4. assumption provenance ──────────────────────────────────────────

class TestAssumptionProvenance:
    def test_every_assumed_edge_has_explicit_reversible_provenance(self, graph):
        assumed = [edge for edge in graph["edges"] if edge["category"] == "vf_scenario_assumption"]
        assert assumed
        for edge in assumed:
            assumption = edge["assumption"]
            assert assumption["source_kind"] == "vf_scenario_assumption"
            assert assumption["status"] == "assumed/synthetic"
            assert assumption["reversible"] is True
            assert assumption["rationale"]
            assert assumption["assumption_id"].startswith("ASSUME-SHW-")

    def test_assumption_registry_is_exactly_the_used_assumptions(self, contracts, graph):
        used = sorted(edge.assumption_id for edge in contracts.edges if edge.assumption_id)
        assert list(contracts.assumption_ids) == used
        assert len(set(contracts.assumption_ids)) == len(contracts.assumption_ids)
        assert graph["assumption_registry"]

    def test_no_edge_identity_is_both_pim_known_and_assumed(self, contracts):
        seen: dict[tuple[str, str, str], str] = {}
        for edge in contracts.edges:
            key = (edge.source, edge.target, edge.flow)
            assert key not in seen, (edge.edge_id, seen.get(key))
            seen[key] = edge.edge_id
        # the F01 direct edge and the alternative in-line T107 path are distinct identities
        assert ("vf-shw-node-t106", "vf-shw-node-t108", "water") in seen
        assert ("vf-shw-node-t106", "vf-shw-node-t107", "water") in seen

    def test_loader_rejects_an_edge_with_two_categories(self, workdir, graph):
        mutated = json.loads(json.dumps(graph))
        duplicate = json.loads(json.dumps(next(e for e in mutated["edges"] if e["edge_id"] == "vf-shw-edge-t106-t108")))
        duplicate["edge_id"] = "vf-shw-edge-t106-t108-assumed"
        duplicate["category"] = "vf_scenario_assumption"
        duplicate["assumption"] = {
            "assumption_id": "ASSUME-SHW-DUPLICATE-F01",
            "version": "1",
            "source_kind": "vf_scenario_assumption",
            "status": "assumed/synthetic",
            "reversible": True,
            "rationale": "conflict probe",
        }
        mutated["edges"].append(duplicate)
        mutated["assumption_registry"].append(
            {"assumption_id": "ASSUME-SHW-DUPLICATE-F01", "edge": duplicate["edge_id"], "reversible": True}
        )
        path = workdir / "graph_conflict.json"
        path.write_text(json.dumps(mutated), encoding="utf-8")
        with pytest.raises(ShwtpContractError, match="simultaneously PIM-known and VF-assumed"):
            load_whole_plant_contracts(graph_path=path)

    def test_loader_rejects_an_assumed_edge_without_provenance(self, workdir, graph):
        mutated = json.loads(json.dumps(graph))
        target = next(e for e in mutated["edges"] if e["category"] == "vf_scenario_assumption")
        target["assumption"] = None
        path = workdir / "graph_no_provenance.json"
        path.write_text(json.dumps(mutated), encoding="utf-8")
        with pytest.raises(ShwtpContractError, match="assumption provenance"):
            load_whole_plant_contracts(graph_path=path)


# ── 2. identity / namespace ───────────────────────────────────────────────

class TestIdentityAndNamespace:
    def test_every_referenced_pim_id_already_exists(self, contracts):
        allowed = accepted_canonical_ids()
        referenced = set(pim_ids_referenced_by_contracts(contracts))
        assert referenced, "the contracts must reference the accepted PIM ids"
        assert referenced <= allowed, sorted(referenced - allowed)

    def test_all_contract_files_reference_only_existing_pim_ids(self, graph, process_payload, control_payload, admission_payload):
        allowed = accepted_canonical_ids()
        for payload in (graph, process_payload, control_payload, admission_payload):
            unknown = shwtp_contracts.referenced_pim_ids(payload) - allowed
            assert not unknown, sorted(unknown)

    def test_vf_local_ids_use_the_reserved_namespace(self, contracts):
        local_ids = set(iter_vf_local_ids(contracts))
        assert local_ids
        assert all(local_id.startswith("vf-shw-") for local_id in local_ids)
        assert not any(re.fullmatch(r"(PLANT|AREA|UNIT|REL)-SHW.*", local_id) for local_id in local_ids)

    def test_loader_rejects_an_invented_canonical_id(self, workdir, graph):
        mutated = json.loads(json.dumps(graph))
        mutated["nodes"][0]["canonical_id"] = "UNIT-SHW-X1-INVENTED"
        path = workdir / "graph_invented.json"
        path.write_text(json.dumps(mutated), encoding="utf-8")
        with pytest.raises(ShwtpContractError, match="do not exist in the accepted inventory"):
            load_whole_plant_contracts(graph_path=path)


# ── 5. process contracts ──────────────────────────────────────────────────

class TestProcessContracts:
    def test_every_x2_admitted_scope_has_a_complete_contract(self, contracts):
        admitted = [scope for scope in contracts.scopes if scope.x2_admitted]
        assert admitted
        required = (
            "inputs", "outputs", "state", "parameters", "constraints",
            "conservation", "update_rule_family", "init_reset", "invalid_state",
        )
        for scope in admitted:
            for field in required:
                assert field in scope.raw, (scope.scope_id, field)
            assert scope.fidelity_class in FIDELITY_CLASSES
            assert scope.update_rule_family
            assert scope.conservation_kind
            assert scope.raw["invalid_state"]["fail_closed"] is True
            assert scope.site_truth is False

    def test_parameters_carry_units_and_synthetic_provenance(self, contracts):
        for scope in contracts.scopes:
            if not scope.x2_admitted:
                continue
            for parameter in scope.raw["parameters"]:
                assert parameter.get("unit") is not None, (scope.scope_id, parameter)
                assert parameter.get("provenance", "").startswith("synthetic_reference"), (
                    scope.scope_id, parameter
                )

    def test_storage_scopes_declare_a_volume_balance(self, contracts):
        storage = {
            "vf-shw-node-t100", "vf-shw-node-t108", "vf-shw-node-wash-t110",
            "vf-shw-node-t105", "vf-shw-node-sludge-t201", "vf-shw-node-t106",
        }
        for scope in contracts.scopes:
            if scope.scope_id in storage:
                assert scope.conservation_kind == "volume_balance", scope.scope_id

    def test_reference_only_and_excluded_scopes_are_not_admitted(self, contracts, process_payload):
        reference = {entry["scope_id"] for entry in process_payload["reference_only_scopes"]}
        t107 = next(scope for scope in contracts.scopes if scope.scope_id == "vf-shw-node-t107")
        assert t107.x2_admitted is False
        for scope in contracts.scopes:
            if scope.scope_id in reference:
                assert scope.x2_admitted is False


# ── 6 + 7. control contracts ──────────────────────────────────────────────

class TestControlContracts:
    def test_every_x2_active_c1_control_is_a_complete_contract(self, contracts):
        active = [
            control for control in contracts.controls
            if control.active_in_x2 and control.control_class == "C1"
        ]
        assert len(active) == 9, [control.controller_id for control in active]
        for control in active:
            assert control.control_class == "C1", control.controller_id
            assert control.implementation_gate == "X2"
            assert control.controller_type in ("rule", "sequence", "ratio", "proportional_rule", "on_off")
            assert control.synthetic_tuning_status
            for field in ("permissives", "interlocks", "alarms", "reset_init", "auto_manual"):
                assert field in control.raw

    def test_x2_active_c0_boundary_entries_are_conditions_not_controllers(self, contracts):
        boundaries = [
            control for control in contracts.controls
            if control.active_in_x2 and control.control_class == "C0"
        ]
        assert {control.controller_id for control in boundaries} == {
            "vf-shw-ctrl-raw-source-boundary",
            "vf-shw-ctrl-network-demand-boundary",
        }
        for control in boundaries:
            assert control.controller_type == "none"
            assert control.implementation_gate == "X2"
            assert control.raw["interlocks"] == []
            assert control.raw["permissives"] == []
            assert control.raw["alarms"] == []
            assert control.synthetic_tuning_status == "n/a (no controller)"
            assert control.raw["provenance"] == "VF synthetic boundary condition"

    def test_pi_pid_loops_are_deferred_with_anti_windup_and_inactive(self, contracts):
        pi_pid = [control for control in contracts.controls if control.controller_type in ("PI", "PID")]
        assert len(pi_pid) == 5, [c.controller_id for c in pi_pid]
        for control in pi_pid:
            assert control.control_class == "C2"
            assert control.active_in_x2 is False
            assert control.implementation_gate in ("X3", "X4")
            assert control.anti_windup != "n/a"
            assert control.raw["pv"] and control.raw["mv"]
            assert control.raw["auto_manual"]
            assert "synthetic" in control.synthetic_tuning_status

    def test_no_c2_control_is_active_in_x2(self, contracts):
        assert not [c for c in contracts.controls if c.control_class == "C2" and c.active_in_x2]

    def test_scope_contracts_reference_existing_controls(self, contracts):
        known = {control.controller_id for control in contracts.controls}
        for scope in contracts.scopes:
            for control_id in scope.control_ids:
                assert control_id in known, (scope.scope_id, control_id)

    def test_every_control_declares_a_gate_and_no_vendor_equivalence(self, contracts):
        for control in contracts.controls:
            assert control.implementation_gate in ("X2", "X3", "X4", "n/a")
            assert "synthetic_reference" in control.synthetic_tuning_status or control.synthetic_tuning_status in (
                "n/a", "n/a (no controller)"
            )


# ── admission manifest ────────────────────────────────────────────────────

class TestX2Admission:
    def test_admission_is_complete_and_internally_consistent(self, contracts):
        admission = contracts.admission
        assert admission.executable_scope_ids
        assert admission.reference_only_scope_ids
        assert not set(admission.executable_scope_ids) & set(admission.reference_only_scope_ids)
        assert admission.c1_active_ids
        assert admission.c2_deferred
        assert admission.assumed_edges_used
        assert admission.pim_known_edges_used
        assert len(admission.invariants) >= 10
        assert admission.not_authorized
        # every executable scope owns a contract
        contracted = {scope.scope_id for scope in contracts.scopes if scope.x2_admitted}
        assert contracted == set(admission.executable_scope_ids)

    def test_every_x2_eligible_assumed_edge_is_listed_as_used(self, contracts):
        eligible = {
            edge.edge_id for edge in contracts.edges
            if edge.category == "vf_scenario_assumption" and edge.x2_eligible
        }
        assert eligible == set(contracts.admission.assumed_edges_used)
        excluded = {
            edge.edge_id for edge in contracts.edges
            if edge.category == "vf_scenario_assumption" and not edge.x2_eligible
        }
        assert excluded == set(contracts.admission.assumed_edges_excluded)

    def test_admission_defers_c2_and_freezes_the_invariants(self, contracts):
        gates = {gate for _, gate in contracts.admission.c2_deferred}
        assert gates <= {"X3", "X4"}
        deferred_ids = {control_id for control_id, _ in contracts.admission.c2_deferred}
        assert not (deferred_ids & set(contracts.admission.c1_active_ids))
        assert "vf-shw-ctrl-chlorine-residual" in deferred_ids
        joined = " ".join(contracts.admission.invariants)
        for expected in ("ONE canonical SH-WTP RuntimeSession", "C2 loop active", "site_truth=false",
                         "no new PIM canonical id"):
            assert expected in joined, expected

    def test_not_authorized_list_covers_the_forbidden_scope(self, contracts):
        joined = " ".join(contracts.admission.not_authorized)
        for expected in ("PI/PID", "rich SH-WTP UI", "gateway", "second workspace/session/run authority"):
            assert expected in joined, expected


# ── determinism ───────────────────────────────────────────────────────────

class TestDeterminism:
    def test_signature_is_stable_across_reloads(self, contracts):
        again = load_whole_plant_contracts()
        assert again.signature == contracts.signature
        assert [edge.edge_id for edge in again.edges] == [edge.edge_id for edge in contracts.edges]

    def test_signature_is_independent_of_declaration_order(self, workdir, contracts, graph):
        mutated = json.loads(json.dumps(graph))
        mutated["nodes"] = list(reversed(mutated["nodes"]))
        mutated["edges"] = list(reversed(mutated["edges"]))
        mutated["assumption_registry"] = list(reversed(mutated["assumption_registry"]))
        path = workdir / "graph_reversed.json"
        path.write_text(json.dumps(mutated), encoding="utf-8")
        reloaded = load_whole_plant_contracts(graph_path=path)
        assert reloaded.signature == contracts.signature


# ── 8. no construction / no authority ─────────────────────────────────────

class TestNoRuntimeConstruction:
    def test_loading_contracts_constructs_nothing(self, monkeypatch):
        counters: dict[str, int] = {}

        for module_name, class_name in PROBED_RUNTIME_TYPES:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
            original = cls.__init__

            def wrapper(self_, *args, _orig=original, _name=class_name, **kwargs):  # noqa: ANN001
                counters[_name] = counters.get(_name, 0) + 1
                return _orig(self_, *args, **kwargs)

            monkeypatch.setattr(cls, "__init__", wrapper)

        load_whole_plant_contracts()
        assert counters == {}, counters

    def test_contract_module_contains_no_runtime_tokens(self):
        code = re.sub(r'""".*?"""', "", inspect.getsource(shwtp_contracts), flags=re.DOTALL)
        for token in RUNTIME_TOKENS:
            assert token not in code, token
        for forbidden_import in ("from virtual_factory.runcontrol", "from virtual_factory.composition",
                                 "from virtual_factory.discrete", "from virtual_factory.ui"):
            assert forbidden_import not in code, forbidden_import

    def test_contract_module_exposes_no_execution_surface(self):
        for attribute in ("advance", "step", "start", "run", "reset_session"):
            assert not hasattr(shwtp_contracts, attribute), attribute

    def test_structural_module_unchanged_by_this_gate(self):
        from virtual_factory.shwtp import structural

        assert structural.SHWTP_RUNTIME_AUTHORIZATION == "NOT_AUTHORIZED"
        assert structural.SHWTP_SITE_AUTHORIZED_EXECUTION == "NOT_AUTHORIZED"
        # the accepted structural containment is fully covered by the frozen canonical id set
        allowed = accepted_canonical_ids()
        structural_ids = {
            parent for parent in structural._CONTAINMENT_BY_CANONICAL  # noqa: SLF001
        } | {
            child
            for children in structural._CONTAINMENT_BY_CANONICAL.values()  # noqa: SLF001
            for child in children
        }
        assert structural_ids <= allowed
        assert len(allowed) >= 28
