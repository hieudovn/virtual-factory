#!/usr/bin/env python3
"""Collect DDAY-VF-UAT-01 read-only pre-deployment recon evidence."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
C03 = "320d82fb2fb3339461553e258b09ebee6689615a"
FR1 = "dd6cfe466832b4c167f49861d27f718291f78699"
FR1_EVIDENCE = "96a43b92dbbf99f178407048b44117124a022eae"
PROFILE = "configs/workspaces/bottled-water-dday/runtime.profile.yaml"
DICTIONARY = "configs/workspaces/bottled-water-dday/plantos_export.dictionary.yaml"
SA_T_LOWER_BOUND_S = 610.0
SA_EPOCH = "2026-10-03T00:00:00.000Z"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def _blob_exists(sha: str, path: str) -> bool:
    r = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}:{path}"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def _sha256_blob(sha: str, path: str) -> str | None:
    r = subprocess.run(["git", "show", f"{sha}:{path}"], cwd=REPO, capture_output=True)
    if r.returncode != 0:
        return None
    return hashlib.sha256(r.stdout).hexdigest()


def _reachable(host: str, port: int, timeout_s: float = 2.0) -> dict:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return {"reachable": True, "error": None}
    except OSError as exc:
        return {"reachable": False, "error": str(exc)}


def _which(name: str) -> bool:
    return shutil.which(name) is not None


def main() -> None:
    profile_at_c03 = _blob_exists(C03, PROFILE)
    scheduler_grep = subprocess.run(
        ["git", "grep", "RuntimeProfileScheduler", C03, "--", "*.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    docker_available = _which("docker")
    docker_ps_code = None
    if docker_available:
        docker_ps = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        docker_ps_code = docker_ps.returncode
    uat = {
        "result": "UNKNOWN",
        "plantos_net": "UNKNOWN",
        "plantos_emqx_1883": "UNKNOWN",
        "edge_dday_01": "UNKNOWN",
        "auth_policy": "UNKNOWN",
        "invented_credentials": False,
        "reason": [],
    }
    if not docker_available:
        uat["reason"].append("docker CLI not present in recon environment")
    elif docker_ps_code != 0:
        uat["reason"].append("docker ps failed; no UAT daemon access")
    emqx = _reachable("plantos-emqx", 1883)
    uat["plantos_emqx_1883"] = "REACHABLE" if emqx["reachable"] else "UNREACHABLE"
    if not emqx["reachable"]:
        uat["reason"].append(f"plantos-emqx:1883 not reachable ({emqx['error']})")
    if os.environ.get("MQTT_USERNAME") or os.environ.get("MQTT_PASSWORD"):
        uat["reason"].append("MQTT credential env present; not used and not logged")
    uat["sa_stated_topology"] = {
        "network": "plantos-net",
        "broker": "plantos-emqx:1883",
        "edge": "plantos-edge-dday / EDGE-DDAY-01",
        "source": "VF SA deployment review on Issue #118 (2026-10-06T22:55:18Z)",
        "independently_verified": False,
        "prior_publisher_credential_flags": "none (SA: internal path without credential flags)",
    }
    td = {
        "result": "UNKNOWN",
        "measured_max": None,
        "measured_max_simulation_time_s": None,
        "historian_modified": False,
        "sa_stated_lower_bound_simulation_time_s": SA_T_LOWER_BOUND_S,
        "sa_stated_lower_bound_timestamp": "2026-10-03T00:10:10.000Z",
        "epoch": SA_EPOCH,
        "reason": "no TDengine endpoint/credentials in this recon environment; did not query or patch historian",
        "next_publish_must_be_strictly_after": "independently measured max (unknown here); not less than SA lower bound t>=610s",
    }
    evidence = {
        "task_id": "DDAY-VF-UAT-01",
        "slice": "pre_deployment_recon_only",
        "head": _git("rev-parse", "HEAD"),
        "origin_main": _git("rev-parse", "origin/main"),
        "c03_accepted_sha": C03,
        "fr1_implementation_sha": FR1,
        "fr1_evidence_sha": FR1_EVIDENCE,
        "c03_sha_has_runtime_profile": profile_at_c03,
        "c03_sha_has_runtime_profile_scheduler": scheduler_grep.returncode == 0,
        "fr1_profile_id": "dday-bw-runtime-fr1",
        "contract_version": "dday-bw-b1-v2",
        "dictionary_sha256_c03": _sha256_blob(C03, DICTIONARY),
        "dictionary_sha256_fr1": _sha256_blob(FR1, DICTIONARY),
        "persistent_bw_mqtt_entrypoint": False,
        "entrypoint_findings": {
            "dockerfile_cmd": "virtual-factory run --steps 60 --quiet",
            "serve_mqtt": "RuntimeService publish_frame on generic MVP, not plantos_export",
            "http_autorun": "BottledWaterFactory.step only; no publish_live_mqtt",
            "systemd": "deploy/virtual-factory.service is Compressor Train OPC UA",
            "vf2_dockerfile": "unrelated PIM runtime",
            "cli_parsers": ["run", "serve", "validate", "generate", "parse"],
        },
        "mqtt_gateway_username_password_api": False,
        "timestamp_epoch": SA_EPOCH,
        "timestamp_formula": "UTC_EPOCH + simulation_time_s",
        "uat_live_inspect": uat,
        "tdengine_max_source_timestamp": td,
        "hero_scenario_windows_s": {
            "capper_recovery_completes_s": 210,
            "compressor_normal_before_degrade_s": 240,
            "compressor_recovery_completes_s": 328,
        },
        "deploy_authorized": False,
        "plantos_handoff": False,
        "merge_authorized": False,
        "launcher_implemented": False,
        "warmup_implemented": False,
    }
    (HERE / "machine-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
