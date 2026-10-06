#!/usr/bin/env python3
"""DDAY-VF-UAT-01 — read-only pre-deployment recon smoke."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
C03 = "320d82fb2fb3339461553e258b09ebee6689615a"
FR1 = "dd6cfe466832b4c167f49861d27f718291f78699"
PROFILE = "configs/workspaces/bottled-water-dday/runtime.profile.yaml"
_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def _blob_exists(sha: str, path: str) -> bool:
    r = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}:{path}"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def _reachable(host: str, port: int, timeout_s: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def main() -> int:
    claim(not _blob_exists(C03, PROFILE), "320d82f has no runtime.profile.yaml")
    claim(_blob_exists(FR1, PROFILE), "dd6cfe4 has runtime.profile.yaml")
    profile = subprocess.check_output(
        ["git", "show", f"{FR1}:{PROFILE}"], cwd=REPO, text=True
    )
    claim("profile_id: dday-bw-runtime-fr1" in profile, "FR1 profile id present at dd6cfe4")
    dockerfile = (REPO / "Dockerfile").read_text(encoding="utf-8")
    claim("bottled-water-dday" not in dockerfile, "root Dockerfile is not a BW D-Day launcher")
    main_py = (REPO / "src/virtual_factory/main.py").read_text(encoding="utf-8")
    claim("publish_live_mqtt" not in main_py, "CLI does not call publish_live_mqtt")
    api = (REPO / "src/virtual_factory/ui/api.py").read_text(encoding="utf-8")
    claim("publish_live_mqtt" not in api, "HTTP autorun does not publish FR1 MQTT")
    evidence_path = HERE / "machine-evidence.json"
    claim(evidence_path.is_file(), "machine-evidence.json exists")
    data = json.loads(evidence_path.read_text(encoding="utf-8"))
    claim(data.get("persistent_bw_mqtt_entrypoint") is False, "evidence records no persistent entrypoint")
    claim(data.get("deploy_authorized") is False, "deployment remains unauthorized")
    claim(data.get("uat_live_inspect", {}).get("invented_credentials") is False, "no invented MQTT credentials")
    emqx = _reachable("plantos-emqx", 1883)
    claim(not emqx or data["uat_live_inspect"]["result"] != "UNKNOWN", "live EMQX reachability matches evidence")
    print("SMOKE-DDAY-VF-UAT-01", "PASS" if not _failures else "FAIL")
    for item in _failures:
        print("  -", item)
    return 0 if not _failures else 1


if __name__ == "__main__":
    sys.exit(main())
