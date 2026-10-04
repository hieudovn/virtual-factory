"""DDAY-B6-C01 — PlantOS cross-repo compatibility probe (no production edits).

This module does not claim PlantOS ingestion or historian proof. It records
what can be checked from this VF environment without PlantOS production-code
changes, and the exact bounded gap when the current PlantOS repo/runtime is
not available.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

VF_ONLY_REPOS = ("github.com/hieudovn/virtual-factory",)
KNOWN_NON_PLANTOS = {
    "hieudovn/manufacturing-data-platform": "Avenue MDP, not PlantOS",
    "hieudovn/NOVA-knowledge-hub": "knowledge hub, not PlantOS",
    "hieudovn/testrepo": "test repository, not PlantOS",
}
WTP_INGEST_NOTE = (
    "simulators/wtp HTTP POST /api/v1/measurements/ingest is a different plant "
    "and is not authorized as a PlantOS substitute."
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _run(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=_repo_root(),
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output.strip()


def _environment_repos() -> list[str]:
    return list(VF_ONLY_REPOS)


def _accessible_hieudovn_repos() -> list[str]:
    code, output = _run(["gh", "repo", "list", "hieudovn", "--limit", "50"])
    if code != 0:
        return []
    names = []
    for line in output.splitlines():
        name = line.split("\t", 1)[0].strip()
        if name:
            names.append(name)
    return names


def _plantos_repo_present() -> bool:
    root = _repo_root()
    markers = (
        root / "plantos",
        root.parent / "plantos",
        Path("/workspace/plantos"),
        Path(os.environ.get("PLANTOS_REPO", "")),
    )
    for marker in markers:
        if not marker:
            continue
        if marker.is_dir() and (
            (marker / "pyproject.toml").exists()
            or (marker / "README.md").exists()
        ):
            text = ""
            readme = marker / "README.md"
            if readme.exists():
                text = readme.read_text(encoding="utf-8", errors="ignore")[:2000]
            if "PlantOS" in text or "plantos" in str(marker).lower():
                if "Avenue" not in text:
                    return True
    return False


def exact_minimal_gap() -> dict[str, Any]:
    """Bounded gap that must be authorized by SA before PlantOS ingest/history can be claimed."""
    return {
        "plantos_ingestion_proven": False,
        "plantos_historian_proven": False,
        "requires_plantos_production_changes": "UNKNOWN_UNTIL_REPO_ACCESS",
        "blocked_by": [
            "PlantOS repository is not present in this Cloud Agent environment",
            "Only github.com/hieudovn/virtual-factory is linked to the environment",
            "No PlantOS test/runtime ingest or historian interface is importable here",
        ],
        "not_used_as_substitute": [
            WTP_INGEST_NOTE,
            "hieudovn/manufacturing-data-platform is Avenue MDP, not PlantOS",
            "VF PlantosLocalIngestion is an adapter/unit-test aid only",
        ],
        "minimal_sa_authorization_required": [
            "Grant this agent read access to the current PlantOS repo and the exact Track A branch/SHA.",
            "If that PlantOS branch already accepts the B6 MQTT JSON envelope (contract_version, workspace_id, plant_source_id, source_id, UTC timestamp, unit/quality/provenance, selected dictionary keys) without production-code changes, authorize a follow-up proof-only slice to ingest and query those samples.",
            "If that PlantOS branch cannot accept the envelope, authorize the exact minimal PlantOS adapter/ingest change. That change is out of DDAY-B6-C01 scope.",
        ],
    }


def compatibility_status(*, live_probe: bool = False) -> dict[str, Any]:
    """Cross-repo compatibility evidence that can be collected without PlantOS edits.

    Runtime export paths use the static gap (no ``gh``). Evidence/smoke may set
    ``live_probe=True`` to record the current token's repo visibility.
    """
    repos = _accessible_hieudovn_repos() if live_probe else [
        "hieudovn/virtual-factory",
        "hieudovn/NOVA-knowledge-hub",
        "hieudovn/manufacturing-data-platform",
        "hieudovn/testrepo",
    ]
    plantos_named = [name for name in repos if "plantos" in name.lower()]
    status = {
        "checked_at_workspace": str(_repo_root()),
        "environment_repos": _environment_repos(),
        "accessible_hieudovn_repos": repos,
        "plantos_named_repos": plantos_named,
        "plantos_repo_present_locally": _plantos_repo_present() if live_probe else False,
        "known_non_plantos": dict(KNOWN_NON_PLANTOS),
        "vf_adapter_only": True,
        "wtp_ingest_used": False,
        "live_probe": live_probe,
        "plantos_ingestion_proven": False,
        "plantos_historian_proven": False,
        "gap": exact_minimal_gap(),
    }
    return status


def write_compatibility_evidence(path: str | Path, *, live_probe: bool = True) -> dict[str, Any]:
    status = compatibility_status(live_probe=live_probe)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return status
