"""VF-SHW-X1 evidence generator (whole-plant process graph + scope/fidelity/control contracts).

Produces repo-native, machine-derived evidence for the contract-only gate:

  01-graph-signature.json      deterministic, schema-valid process graph + file digests
  02-validation-matrix.json    the ten X1 validations, each evaluated and evidenced
  03-no-construction-proof.json zero new runtime/session/controller/engine construction
  04-x2-admission-summary.json X2 executable scope, fidelity and control admission

Run:  python .ai-harness/sa-review/evidence/VF-SHW-X1/generate_evidence.py
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE
while not (ROOT / "pyproject.toml").exists():
    ROOT = ROOT.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from virtual_factory.shwtp import contracts as shwtp_contracts  # noqa: E402
from virtual_factory.shwtp.contracts import (  # noqa: E402
    ASSUMED_SOURCE_KIND,
    ASSUMED_STATUS,
    EDGE_CATEGORIES,
    GRAPH_SCHEMA,
    VF_LOCAL_PREFIX,
    accepted_canonical_ids,
    iter_vf_local_ids,
    load_whole_plant_contracts,
    pim_ids_referenced_by_contracts,
    referenced_pim_ids,
)

CONFIG_DIR = ROOT / "configs" / "vnext" / "shwtp"
ARTIFACTS = {
    "graph": CONFIG_DIR / "shwtp_whole_plant_graph_v1.json",
    "process": CONFIG_DIR / "shwtp_process_contracts_v1.json",
    "control": CONFIG_DIR / "shwtp_control_contracts_v1.json",
    "admission": CONFIG_DIR / "shwtp_x2_admission_manifest_v1.json",
}
CODE_ARTIFACT = SRC / "virtual_factory" / "shwtp" / "contracts.py"
TEST_ARTIFACT = ROOT / "tests" / "test_vnext_x1_whole_plant_contracts.py"

PROBED_RUNTIME_TYPES = (
    ("virtual_factory.runcontrol.lifecycle", "RunLifecycleService"),
    ("virtual_factory.runcontrol.session", "RuntimeSession"),
    ("virtual_factory.shwtp.bridge", "ShwtpExecutionBridge"),
    ("virtual_factory.shwtp.runtime", "T108TankRuntime"),
    ("virtual_factory.shwtp.logical_runtime", "T106LogicalRuntime"),
    ("virtual_factory.core.simulation_engine", "SimulationEngine"),
    ("virtual_factory.discrete.engine", "DiscreteSimulationEngine"),
)

RUNTIME_TOKENS = (
    "RunLifecycleService",
    "ExecutionBridge",
    "RuntimeService",
    "SimulationEngine",
    "RunRecord",
    "def advance",
    "def step",
)

FORBIDDEN_IMPORTS = (
    "from virtual_factory.runcontrol",
    "from virtual_factory.composition",
    "from virtual_factory.discrete",
    "from virtual_factory.ui",
)

REQUIRED_INVARIANTS = (
    "ONE canonical SH-WTP RuntimeSession",
    "C2 loop active",
    "site_truth=false",
    "no new PIM canonical id",
)

NOT_AUTHORIZED_EXPECTATIONS = (
    "PI/PID",
    "rich SH-WTP UI",
    "gateway",
    "second workspace/session/run authority",
)

#: the frozen X1 whole-plant shape (regression-pinned)
FROZEN_COUNTS = {
    "nodes": 19,
    "edges": 25,
    "assumptions": 18,
    "scope_contracts": 17,
    "controls": 19,
    "pim_known_edges": 3,
    "reference_only_edges": 4,
    "assumed_edges": 18,
}
FROZEN_ADMISSION = {
    "executable_scopes": 16,
    "reference_only_scopes": 3,
    "x2_active_c1": 9,
    "boundary_entries": 2,
    "c2_loops_deferred": 5,
    "admission_deferred_entries": 6,
    "invariants": 14,
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def graph_signature_evidence() -> dict:
    first = load_whole_plant_contracts()
    second = load_whole_plant_contracts()
    graph_raw = json.loads(ARTIFACTS["graph"].read_text(encoding="utf-8"))
    categories: dict[str, int] = {}
    for edge in first.edges:
        categories[edge.category] = categories.get(edge.category, 0) + 1
    fidelity: dict[str, int] = {}
    for scope in first.scopes:
        fidelity[scope.fidelity_class] = fidelity.get(scope.fidelity_class, 0) + 1
    payload = {
        "gate": "VF-SHW-X1",
        "artifacts": {name: str(path.relative_to(ROOT)).replace("\\", "/") for name, path in ARTIFACTS.items()},
        "artifact_digests": {
            name: digest(path) for name, path in ARTIFACTS.items()
        },
        "code_artifact": {
            "path": str(CODE_ARTIFACT.relative_to(ROOT)).replace("\\", "/"),
            "sha256": digest(CODE_ARTIFACT),
        },
        "test_artifact": {
            "path": str(TEST_ARTIFACT.relative_to(ROOT)).replace("\\", "/"),
            "sha256": digest(TEST_ARTIFACT),
        },
        "graph_schema": graph_raw["schema"],
        "node_count": len(first.nodes),
        "edge_count": len(first.edges),
        "edges_per_category": dict(sorted(categories.items())),
        "assumption_count": len(first.assumption_ids),
        "scope_contract_count": len(first.scopes),
        "scope_fidelity_classes": dict(sorted(fidelity.items())),
        "control_contract_count": len(first.controls),
        "signature": first.signature,
        "frozen_counts": FROZEN_COUNTS,
        "observed_counts": {
            "nodes": len(first.nodes),
            "edges": len(first.edges),
            "assumptions": len(first.assumption_ids),
            "scope_contracts": len(first.scopes),
            "controls": len(first.controls),
            "pim_known_edges": categories.get("pim_known", 0),
            "reference_only_edges": categories.get("reference_only", 0),
            "assumed_edges": categories.get("vf_scenario_assumption", 0),
        },
        "counts_match_frozen": {
            "nodes": len(first.nodes) == FROZEN_COUNTS["nodes"],
            "edges": len(first.edges) == FROZEN_COUNTS["edges"],
            "assumptions": len(first.assumption_ids) == FROZEN_COUNTS["assumptions"],
            "scope_contracts": len(first.scopes) == FROZEN_COUNTS["scope_contracts"],
            "controls": len(first.controls) == FROZEN_COUNTS["controls"],
            "pim_known_edges": categories.get("pim_known", 0) == FROZEN_COUNTS["pim_known_edges"],
            "reference_only_edges": categories.get("reference_only", 0) == FROZEN_COUNTS["reference_only_edges"],
            "assumed_edges": categories.get("vf_scenario_assumption", 0) == FROZEN_COUNTS["assumed_edges"],
        },
        "deterministic_across_reloads": first.signature == second.signature,
        "edge_order_stable": [e.edge_id for e in first.edges] == [e.edge_id for e in second.edges],
        "verdict": (
            "WHOLE_PLANT_GRAPH_DETERMINISTIC"
            if first.signature == second.signature
            and [e.edge_id for e in first.edges] == [e.edge_id for e in second.edges]
            and len(first.nodes) == FROZEN_COUNTS["nodes"]
            and len(first.edges) == FROZEN_COUNTS["edges"]
            and len(first.assumption_ids) == FROZEN_COUNTS["assumptions"]
            else "GRAPH_NOT_DETERMINISTIC"
        ),
    }
    return payload


def validation_matrix() -> dict:
    graph_raw = json.loads(ARTIFACTS["graph"].read_text(encoding="utf-8"))
    process_raw = json.loads(ARTIFACTS["process"].read_text(encoding="utf-8"))
    control_raw = json.loads(ARTIFACTS["control"].read_text(encoding="utf-8"))
    admission_raw = json.loads(ARTIFACTS["admission"].read_text(encoding="utf-8"))
    contracts = load_whole_plant_contracts()

    checks: dict[str, dict] = {}

    def record(key: str, ok: bool, detail: object) -> None:
        checks[key] = {"pass": bool(ok), "detail": detail}

    # 1 - deterministic + schema valid
    record(
        "V1_graph_deterministic_and_schema_valid",
        graph_raw["schema"] == GRAPH_SCHEMA
        and load_whole_plant_contracts().signature == contracts.signature,
        {"schema": graph_raw["schema"], "signature": contracts.signature[:24]},
    )

    # 2 - no invented PIM id
    allowed = accepted_canonical_ids()
    per_file_unknown = {
        name: sorted(referenced_pim_ids(payload) - allowed)
        for name, payload in (
            ("graph", graph_raw), ("process", process_raw),
            ("control", control_raw), ("admission", admission_raw),
        )
    }
    record(
        "V2_no_new_canonical_pim_id",
        not any(per_file_unknown.values()) and not (set(pim_ids_referenced_by_contracts(contracts)) - allowed),
        {
            "accepted_canonical_ids": len(allowed),
            "referenced_by_contracts": len(set(pim_ids_referenced_by_contracts(contracts))),
            "unknown_ids": {k: v for k, v in per_file_unknown.items() if v},
        },
    )

    # 3 - VF-local namespace
    local_ids = sorted(set(iter_vf_local_ids(contracts)))
    record(
        "V3_vf_local_namespace_only",
        bool(local_ids)
        and all(local_id.startswith(VF_LOCAL_PREFIX) for local_id in local_ids)
        and not any(re.fullmatch(r"(PLANT|AREA|UNIT|REL|PROC|GAP)-SHW.*", i) for i in local_ids),
        {"vf_local_id_count": len(local_ids), "prefix": VF_LOCAL_PREFIX, "sample": local_ids[:6]},
    )

    # 4 - assumption provenance
    assumed = [e for e in graph_raw["edges"] if e["category"] == "vf_scenario_assumption"]
    provenance_ok = all(
        e["assumption"]["source_kind"] == ASSUMED_SOURCE_KIND
        and e["assumption"]["status"] == ASSUMED_STATUS
        and e["assumption"]["reversible"] is True
        and e["assumption"]["rationale"]
        for e in assumed
    )
    record(
        "V4_assumption_provenance_complete",
        provenance_ok
        and list(contracts.assumption_ids) == sorted(e["assumption"]["assumption_id"] for e in assumed),
        {
            "assumed_edges": len(assumed),
            "assumption_registry_entries": len(contracts.assumption_ids),
            "source_kind": ASSUMED_SOURCE_KIND,
            "status": ASSUMED_STATUS,
            "reversible": True,
        },
    )

    # 5 - no dual-category identity
    identities: dict[tuple[str, str, str], list[str]] = {}
    for edge in contracts.edges:
        identities.setdefault((edge.source, edge.target, edge.flow), []).append(edge.edge_id)
    duplicates = {f"{k[0]}->{k[1]}:{k[2]}": v for k, v in identities.items() if len(v) > 1}
    record(
        "V5_no_dual_category_edge_identity",
        not duplicates,
        {"duplicate_identities": duplicates, "distinct_identities": len(identities)},
    )

    # 6 - process contract completeness for every X2 scope
    admitted = [s for s in contracts.scopes if s.x2_admitted]
    required = (
        "inputs", "outputs", "state", "parameters", "constraints",
        "conservation", "update_rule_family", "init_reset", "invalid_state",
    )
    missing = {
        s.scope_id: [f for f in required if f not in s.raw] for s in admitted if any(f not in s.raw for f in required)
    }
    record(
        "V6_process_contract_complete_per_x2_scope",
        not missing and all(s.raw["invalid_state"]["fail_closed"] is True for s in admitted),
        {
            "x2_admitted_scopes": [s.scope_id for s in admitted],
            "missing_fields": missing,
            "fail_closed": all(s.raw["invalid_state"]["fail_closed"] is True for s in admitted),
        },
    )

    # 7 - C1 control completeness and C2 deferral
    active_c1 = [c for c in contracts.controls if c.active_in_x2 and c.control_class == "C1"]
    c2 = [c for c in contracts.controls if c.control_class == "C2"]
    control_required = ("permissives", "interlocks", "alarms", "reset_init", "auto_manual")
    control_missing = {
        c.controller_id: [f for f in control_required if f not in c.raw]
        for c in active_c1
        if any(f not in c.raw for f in control_required)
    }
    record(
        "V7_c1_complete_and_c2_deferred",
        not control_missing
        and all(c.implementation_gate == "X2" for c in active_c1)
        and all((not c.active_in_x2) and c.anti_windup != "n/a" for c in c2)
        and not [c for c in contracts.controls if c.control_class == "C2" and c.active_in_x2],
        {
            "x2_active_c1": sorted(c.controller_id for c in active_c1),
            "c2_deferred": {c.controller_id: c.implementation_gate for c in c2},
            "admission_deferred_entries": {
                control_id: gate for control_id, gate in contracts.admission.c2_deferred
            },
            "missing_fields": control_missing,
            "c2_active_in_x2": [c.controller_id for c in contracts.controls if c.control_class == "C2" and c.active_in_x2],
        },
    )

    # 8 - admission internal consistency
    admission = contracts.admission
    executable = set(admission.executable_scope_ids)
    reference_only = set(admission.reference_only_scope_ids)
    contracted = {s.scope_id for s in admitted}
    eligible_assumed = {
        e.edge_id for e in contracts.edges if e.category == "vf_scenario_assumption" and e.x2_eligible
    }
    excluded_assumed = {
        e.edge_id for e in contracts.edges if e.category == "vf_scenario_assumption" and not e.x2_eligible
    }
    record(
        "V8_admission_internally_consistent",
        not (executable & reference_only)
        and contracted == executable
        and set(admission.c1_active_ids) == {c.controller_id for c in active_c1}
        and eligible_assumed == set(admission.assumed_edges_used)
        and excluded_assumed == set(admission.assumed_edges_excluded),
        {
            "executable_scopes": sorted(executable),
            "reference_only_scopes": sorted(reference_only),
            "scope_overlap": sorted(executable & reference_only),
            "contracts_without_admission": sorted(contracted - executable),
            "admitted_without_contract": sorted(executable - contracted),
            "assumed_edges_used": len(admission.assumed_edges_used),
            "assumed_edges_excluded": len(admission.assumed_edges_excluded),
            "pim_known_edges_used": len(admission.pim_known_edges_used),
        },
    )

    # 9 - frozen invariants + authority
    invariants = " ".join(admission.invariants)
    not_authorized = " ".join(admission.not_authorized)
    missing_invariants = [t for t in REQUIRED_INVARIANTS if t not in invariants]
    missing_not_authorized = [t for t in NOT_AUTHORIZED_EXPECTATIONS if t not in not_authorized]
    authority_ok = all(
        payload["authority"]["vf_runtime_authorization"] == "NOT_AUTHORIZED"
        and payload["authority"]["site_authorized_execution"] == "NOT_AUTHORIZED"
        and payload["authority"]["site_truth"] is False
        for payload in (graph_raw, process_raw, control_raw, admission_raw)
    )
    record(
        "V9_invariants_and_authority_frozen",
        not missing_invariants and not missing_not_authorized and authority_ok,
        {
            "invariant_count": len(admission.invariants),
            "missing_invariants": missing_invariants,
            "missing_not_authorized": missing_not_authorized,
            "authority_frozen": authority_ok,
            "site_truth": False,
        },
    )

    # 10 - no runtime/session/controller construction
    counters: dict[str, int] = {}
    originals: list[tuple[object, str, object]] = []
    try:
        for module_name, class_name in PROBED_RUNTIME_TYPES:
            cls = getattr(importlib.import_module(module_name), class_name)
            original = cls.__init__
            originals.append((cls, "__init__", original))

            def wrapper(self_, *args, _orig=original, _name=class_name, **kwargs):  # noqa: ANN001
                counters[_name] = counters.get(_name, 0) + 1
                return _orig(self_, *args, **kwargs)

            cls.__init__ = wrapper
        load_whole_plant_contracts()
    finally:
        for cls, name, original in originals:
            setattr(cls, name, original)

    code = re.sub(r'""".*?"""', "", inspect.getsource(shwtp_contracts), flags=re.DOTALL)
    token_hits = [token for token in RUNTIME_TOKENS if token in code]
    import_hits = [imp for imp in FORBIDDEN_IMPORTS if imp in code]
    surface_hits = [a for a in ("advance", "step", "start", "run", "reset_session") if hasattr(shwtp_contracts, a)]
    record(
        "V10_no_runtime_construction_or_execution_surface",
        not counters and not token_hits and not import_hits and not surface_hits,
        {
            "probed_types": [f"{m}.{c}" for m, c in PROBED_RUNTIME_TYPES],
            "constructor_calls_during_load": counters,
            "runtime_tokens_in_contract_module": token_hits,
            "forbidden_imports_in_contract_module": import_hits,
            "execution_surface_attributes": surface_hits,
        },
    )

    failed = sorted(key for key, value in checks.items() if not value["pass"])
    return {
        "gate": "VF-SHW-X1",
        "validation_count": len(checks),
        "checks": checks,
        "failed_checks": failed,
        "verdict": "ALL_X1_VALIDATIONS_PASS" if not failed else "X1_VALIDATION_FAILURES",
    }


def no_construction_proof() -> dict:
    counters: dict[str, int] = {}
    originals: list[tuple[object, object]] = []
    try:
        for module_name, class_name in PROBED_RUNTIME_TYPES:
            cls = getattr(importlib.import_module(module_name), class_name)
            original = cls.__init__
            originals.append((cls, original))

            def wrapper(self_, *args, _orig=original, _name=class_name, **kwargs):  # noqa: ANN001
                counters[_name] = counters.get(_name, 0) + 1
                return _orig(self_, *args, **kwargs)

            cls.__init__ = wrapper
        load_whole_plant_contracts()
    finally:
        for cls, original in originals:
            cls.__init__ = original

    from virtual_factory.shwtp import structural

    containment_ids = set(structural._CONTAINMENT_BY_CANONICAL) | {  # noqa: SLF001
        child
        for children in structural._CONTAINMENT_BY_CANONICAL.values()  # noqa: SLF001
        for child in children
    }
    allowed = accepted_canonical_ids()
    code = re.sub(r'""".*?"""', "", inspect.getsource(shwtp_contracts), flags=re.DOTALL)
    return {
        "gate": "VF-SHW-X1",
        "probed_types": [f"{m}.{c}" for m, c in PROBED_RUNTIME_TYPES],
        "constructor_calls_during_contract_load": counters,
        "runtime_tokens_in_contract_module": [t for t in RUNTIME_TOKENS if t in code],
        "forbidden_imports_in_contract_module": [i for i in FORBIDDEN_IMPORTS if i in code],
        "contract_module_public_surface": sorted(
            name for name in dir(shwtp_contracts) if not name.startswith("_")
        ),
        "structural_module_unchanged": {
            "runtime_authorization": structural.SHWTP_RUNTIME_AUTHORIZATION,
            "site_authorized_execution": structural.SHWTP_SITE_AUTHORIZED_EXECUTION,
            "canonical_ids_in_containment": len(containment_ids),
            "containment_ids_all_accepted": containment_ids <= allowed,
        },
        "verdict": (
            "NO_RUNTIME_CONSTRUCTION_ADDED"
            if not counters
            and not [t for t in RUNTIME_TOKENS if t in code]
            and not [i for i in FORBIDDEN_IMPORTS if i in code]
            and containment_ids <= allowed
            and structural.SHWTP_RUNTIME_AUTHORIZATION == "NOT_AUTHORIZED"
            else "RUNTIME_SURFACE_DETECTED"
        ),
    }


def x2_admission_summary() -> dict:
    contracts = load_whole_plant_contracts()
    admission = contracts.admission
    active_c1 = sorted(c.controller_id for c in contracts.controls if c.active_in_x2 and c.control_class == "C1")
    boundaries = sorted(c.controller_id for c in contracts.controls if c.active_in_x2 and c.control_class == "C0")
    c2 = {c.controller_id: c.implementation_gate for c in contracts.controls if c.control_class == "C2"}
    node_roles: dict[str, str] = {}
    for node in contracts.nodes:
        node_roles[node.process_role] = node_roles.get(node.process_role, "")
    scopes = [
        {
            "scope_id": scope.scope_id,
            "canonical_id": scope.canonical_id,
            "canonical_refs": list(scope.raw.get("canonical_refs", [])),
            "fidelity_class": scope.fidelity_class,
            "update_rule_family": scope.update_rule_family,
            "conservation_kind": scope.conservation_kind,
            "x2_admitted": scope.x2_admitted,
            "controls": list(scope.control_ids),
            "site_truth": scope.site_truth,
        }
        for scope in contracts.scopes
    ]
    t107 = next(scope for scope in contracts.scopes if scope.scope_id == "vf-shw-node-t107")
    return {
        "gate": "VF-SHW-X1",
        "executable_scope_ids": list(admission.executable_scope_ids),
        "reference_only_scope_ids": list(admission.reference_only_scope_ids),
        "t107_excluded_from_x2": not t107.x2_admitted,
        "x2_active_control_ids": active_c1,
        "x2_active_control_count": len(active_c1),
        "x2_active_boundary_entries": boundaries,
        "deferred_c2_controls": c2,
        "deferred_control_gates": sorted(set(c2.values())),
        "admission_deferred_entries": {
            control_id: gate for control_id, gate in admission.c2_deferred
        },
        "assumed_edges_used": list(admission.assumed_edges_used),
        "assumed_edges_excluded": list(admission.assumed_edges_excluded),
        "pim_known_edges_used": list(admission.pim_known_edges_used),
        "node_roles": sorted(node_roles),
        "scope_contracts": scopes,
        "invariants": list(admission.invariants),
        "not_authorized": list(admission.not_authorized),
        "frozen_admission": FROZEN_ADMISSION,
        "authority": {
            "vf_runtime_authorization": "NOT_AUTHORIZED",
            "site_authorized_execution": "NOT_AUTHORIZED",
            "whole_plant_runtime": "NOT_AUTHORIZED / NOT_IMPLEMENTED",
            "site_truth": False,
            "simulation_truth": "synthetic_reference",
        },
        "verdict": (
            "X2_ADMISSION_FROZEN"
            if len(active_c1) == FROZEN_ADMISSION["x2_active_c1"]
            and len(admission.executable_scope_ids) == FROZEN_ADMISSION["executable_scopes"]
            and len(admission.reference_only_scope_ids) == FROZEN_ADMISSION["reference_only_scopes"]
            and len(boundaries) == FROZEN_ADMISSION["boundary_entries"]
            and len(c2) == FROZEN_ADMISSION["c2_loops_deferred"]
            and len(admission.c2_deferred) == FROZEN_ADMISSION["admission_deferred_entries"]
            and len(admission.invariants) == FROZEN_ADMISSION["invariants"]
            and set(c2.values()) <= {"X3", "X4"}
            else "X2_ADMISSION_INCOMPLETE"
        ),
    }


def main() -> int:
    results = {
        "01-graph-signature.json": graph_signature_evidence(),
        "02-validation-matrix.json": validation_matrix(),
        "03-no-construction-proof.json": no_construction_proof(),
        "04-x2-admission-summary.json": x2_admission_summary(),
    }
    for name, payload in results.items():
        (HERE / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: payload["verdict"] for name, payload in results.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
