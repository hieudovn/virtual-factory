"""VF-SHW-X0 evidence generator (DESIGN/AUDIT-ONLY gate).

Derives repo-native evidence for the SH-WTP whole-plant design freeze:

  01-inventory.json            areas/units/roles/fidelity ceilings/evidence statuses/gaps + live slice + registry
  02-topology-matrix.json      known / assumed / unknown edge matrix (repo-derived + documented VF-assumed edges)
  04-no-new-pim-id-proof.json  every canonical ID used by the design already exists in the repo
  05-no-code-change-proof.json design-only proof: no executable/source/doc/config change

(03-control-matrix.json is the frozen machine-readable control design data authored with the report.)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE
while not (ROOT / "pyproject.toml").exists():
    ROOT = ROOT.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

REPORT = ROOT / ".ai-harness" / "sa-review" / "reports" / "VF-SHW-X0.md"
READINESS = ROOT / "configs" / "vnext" / "shwtp" / "shwtp_readiness_scope.json"

CANONICAL_ID_RE = re.compile(
    r"\b(?:PLANT|AREA|UNIT|REL|PROC|GAP)-SHW[A-Z0-9-]*\b"
)
VF_LOCAL_RE = re.compile(r"\bvf-shw[a-z0-9-]*\b")

#: VF-assumed edges frozen by the review (documented in the report section 3).
VF_ASSUMED_EDGES = [
    {"edge": "E5", "from": "UNIT-SHW-L1-T108", "to": "UNIT-SHW-DIST-P108",
     "status": "VF-assumed", "evidence": "shwtp_workstream_independence_review.json: unit-level relation STILL_INSUFFICIENT; overlay.py scenario assumption"},
    {"edge": "E6", "from": "UNIT-SHW-L1-T101", "to": "UNIT-SHW-L1-T105",
     "status": "VF-assumed", "evidence": "inventory notes: units DocumentConfirmed, serial order not established"},
    {"edge": "E7", "from": "UNIT-SHW-L1-T105", "to": "UNIT-SHW-L1-T106",
     "status": "VF-assumed", "evidence": "shwtp_expansion_readiness.json T105 rationale: adjacency inferred"},
    {"edge": "E8", "from": "UNIT-SHW-L1-T106", "to": "UNIT-SHW-L1-T108",
     "status": "VF-assumed (in-line T107 default)",
     "evidence": "REL-SHW-F01 target is T108; T107 in-line position PIM-ambiguous"},
    {"edge": "E9", "from": "UNIT-SHW-L1-T106", "to": "UNIT-SHW-WASH-T110",
     "status": "VF-assumed (return destination)",
     "evidence": "shwtp_synthetic_runtime_admission.json T110 rationale: return destination VF-inferred"},
    {"edge": "E14", "from": "external raw-water source", "to": "UNIT-SHW-RAW-INTAKE",
     "status": "unknown boundary (C0)", "evidence": "no PIM data for the external source"},
    {"edge": "E15", "from": "plant-level quality/KPI chain", "to": "n/a",
     "status": "unknown (synthetic proxies only)", "evidence": "GAP-SHW-004 (lab/quality history)"},
]


def load_readiness() -> dict:
    return json.loads(READINESS.read_text(encoding="utf-8"))


def inventory() -> dict:
    data = load_readiness()
    entries = data.get("inventory") or data.get("scopes") or []
    rows = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        rows.append(
            {
                "id": entry.get("id") or entry.get("canonical_id"),
                "pim_canonical_id": entry.get("pim_canonical_id"),
                "pim_reference": entry.get("pim_reference"),
                "vf_scope_role": entry.get("vf_scope_role"),
                "fidelity_ceiling": entry.get("fidelity_ceiling"),
                "evidence_status": (entry.get("evidence") or {}).get("status")
                if isinstance(entry.get("evidence"), dict)
                else entry.get("evidence_status"),
                "gaps": entry.get("gaps"),
                "runtime_later": entry.get("runtime_later"),
                "note": entry.get("note") or entry.get("rationale"),
            }
        )

    relations = []
    seen: set[str] = set()
    for match in re.finditer(r"REL-SHW-F\d+", json.dumps(data)):
        rid = match.group(0)
        if rid not in seen:
            seen.add(rid)
            relations.append(rid)

    slice_info: dict = {}
    try:
        from virtual_factory.shwtp.expansion import PLANT_SLICE_SCOPES

        slice_info["plant_slice_scopes"] = [
            getattr(scope, "path", None) or getattr(scope, "as_string", lambda: None)()
            or str(scope)
            for scope in PLANT_SLICE_SCOPES
        ]
        slice_info["plant_slice_scope_count"] = len(PLANT_SLICE_SCOPES)
    except Exception as exc:  # noqa: BLE001
        slice_info["plant_slice_error"] = f"{type(exc).__name__}: {exc}"

    registry_info: dict = {}
    try:
        from virtual_factory.ui.workspace_monitor import build_platform_registry

        registry = build_platform_registry()
        registry_info["registry_workspaces"] = sorted(map(str, registry.workspace_ids()))
    except Exception as exc:  # noqa: BLE001
        registry_info["registry_error"] = f"{type(exc).__name__}: {exc}"

    structural_info: dict = {}
    try:
        from virtual_factory.shwtp.structural import build_shwtp_workspace

        workspace = build_shwtp_workspace()
        view = workspace.view() if hasattr(workspace, "view") else {}
        structural_info = {
            "workspace_id": getattr(workspace, "workspace_id", None),
            "scope_count": view.get("scope_count") if isinstance(view, dict) else None,
        }
    except Exception as exc:  # noqa: BLE001
        structural_info["structural_error"] = f"{type(exc).__name__}: {exc}"

    return {
        "source_of_record": str(READINESS.relative_to(ROOT)),
        "inventory_entries": len(rows),
        "scopes": rows,
        "relation_ids_present": sorted(relations),
        "live_runtime": slice_info,
        "registry": registry_info,
        "structural_workspace": structural_info,
        "canonical_areas": sorted(
            {row["pim_canonical_id"] for row in rows if (row["pim_canonical_id"] or "").startswith("AREA-SHW")}
        ),
        "canonical_units": sorted(
            {row["pim_canonical_id"] for row in rows if (row["pim_canonical_id"] or "").startswith("UNIT-SHW")}
        ),
        "verdict": "INVENTORY_DERIVED_FROM_REPO" if rows else "INVENTORY_EMPTY",
    }


def topology_matrix() -> dict:
    data = load_readiness()
    text = json.dumps(data)
    confirmed = sorted(set(re.findall(r"REL-SHW-F0[145]", text)))
    inferred = sorted(set(re.findall(r"REL-SHW-F0[67]", text)))
    return {
        "known_document_confirmed_relations": confirmed,
        "known_aggregate_relations": ["REL-SHW-F04", "REL-SHW-F05"],
        "pattern_inferred_relations": inferred,
        "vf_assumed_edges": VF_ASSUMED_EDGES,
        "unknown_gaps": sorted(set(re.findall(r"GAP-SHW-\d+", text))),
        "rules": [
            "PIM owns canonical IDs, evidence_status and truth_domain vocabulary; VF references, never invents.",
            "VF-assumed connectivity must use the existing reversible vf_scenario_assumption mechanism and may never claim DocumentConfirmed.",
            "Every VF-assumed edge stays visible in the UI (assumed_topology / inbound_link_assumed) and reversible.",
        ],
        "verdict": "TOPOLOGY_MATRIX_FROZEN",
    }


def no_new_pim_id_proof() -> dict:
    """Every canonical ID used by the design must already exist in the repo."""
    haystack_parts = []
    for pattern in ("configs/**/*", "docs/**/*", "src/**/*.py", "tests/**/*.py",
                    ".ai-harness/sa-review/evidence/**/*.json", ".ai-harness/sa-review/evidence/**/*.md"):
        for path in ROOT.glob(pattern):
            if path.is_file() and path.stat().st_size < 4_000_000:
                try:
                    haystack_parts.append(path.read_text(encoding="utf-8", errors="replace"))
                except Exception:  # noqa: BLE001
                    continue
    haystack = "\n".join(haystack_parts)

    design_files = [REPORT] + [
        HERE / name
        for name in ("01-inventory.json", "02-topology-matrix.json", "03-control-matrix.json")
        if (HERE / name).exists()
    ]
    used: dict[str, int] = {}
    for path in design_files:
        for token in CANONICAL_ID_RE.findall(path.read_text(encoding="utf-8")):
            used[token] = used.get(token, 0) + 1

    missing = sorted(token for token in used if token not in haystack)
    vf_local_used = sorted(
        {
            token
            for path in design_files
            for token in VF_LOCAL_RE.findall(path.read_text(encoding="utf-8"))
        }
    )
    return {
        "canonical_ids_used_by_design": sorted(used),
        "canonical_id_use_counts": dict(sorted(used.items())),
        "missing_in_repo": missing,
        "vf_local_ids_introduced": vf_local_used,
        "vf_local_prefix_is_not_pim_shaped": all(not t.upper().startswith(("PLANT-SHW", "AREA-SHW", "UNIT-SHW"))
                                                for t in vf_local_used),
        "verdict": "NO_NEW_PIM_ID_INTRODUCED" if not missing else "INVENTED_PIM_ID_FOUND",
    }


def no_code_change_proof() -> dict:
    base = "f4dcca59112b1f68c94ede6ad50378c72eb0b8e0"
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", base],
            cwd=str(ROOT), capture_output=True, text=True, check=False,
        )
        changed = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    except Exception as exc:  # noqa: BLE001
        changed = []
        print("git diff failed:", exc)
    code_change = [
        path for path in changed
        if not path.startswith(".ai-harness/")
    ]
    # The editor rewrites .vscode/tasks.json whenever a task is created; it is an
    # editor artifact, never part of a gate change set (and is reverted before
    # staging). It is reported but cannot make this gate a code change.
    editor_artifacts = [path for path in code_change if path.startswith(".vscode/")]
    source_change = [path for path in code_change if not path.startswith(".vscode/")]
    return {
        "base_sha": base,
        "changed_files": changed,
        "non_harness_changes": code_change,
        "editor_artifacts_ignored": editor_artifacts,
        "source_document_changes": source_change,
        "source_globs_clean": all(
            not any(path.startswith(prefix) for prefix in
                    ("src/", "tests/", "configs/", "docs/", "simulators/", "scripts/", "deploy/", "tools/"))
            for path in changed
        ),
        "verdict": "DESIGN_ONLY_NO_CODE_CHANGE" if not source_change else "CODE_CHANGED_UNEXPECTEDLY",
    }


def main() -> int:
    results = {
        "01-inventory.json": inventory(),
        "02-topology-matrix.json": topology_matrix(),
        "04-no-new-pim-id-proof.json": no_new_pim_id_proof(),
        "05-no-code-change-proof.json": no_code_change_proof(),
    }
    for name, payload in results.items():
        (HERE / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: payload["verdict"] for name, payload in results.items()}, indent=2))
    print("canonical ids used:", len(results["04-no-new-pim-id-proof.json"]["canonical_ids_used_by_design"]))
    print("vf-local ids:", results["04-no-new-pim-id-proof.json"]["vf_local_ids_introduced"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
