"""DDAY-VF-UAT-01 — read-only pre-deployment reconciliation."""

from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path

from virtual_factory.protocols.mqtt_gateway import MqttGateway
from virtual_factory.workspaces.plantos_export import CONTRACT_VERSION, UTC_EPOCH, utc_timestamp

REPO = Path(__file__).resolve().parent.parent
C03 = "320d82fb2fb3339461553e258b09ebee6689615a"
FR1 = "dd6cfe466832b4c167f49861d27f718291f78699"
FR1_EVIDENCE = "96a43b92dbbf99f178407048b44117124a022eae"
PROFILE = "configs/workspaces/bottled-water-dday/runtime.profile.yaml"
DICTIONARY = "configs/workspaces/bottled-water-dday/plantos_export.dictionary.yaml"
DICT_SHA = "cbe389ec7d3c022a78b7853044f08ba148a7b8a41e374931973683c8886b07ca"


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


def _show(sha: str, path: str) -> str:
    return _git("show", f"{sha}:{path}")


def test_uat01_r1_c03_sha_has_no_fr1_profile_or_scheduler():
    assert not _blob_exists(C03, PROFILE)
    grep = subprocess.run(
        ["git", "grep", "-n", "RuntimeProfileScheduler", C03, "--", "*.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert grep.returncode != 0
    assert "publish_live_mqtt" not in _show(C03, "src/virtual_factory/workspaces/bottled_water.py")
    assert "dday-bw-runtime-fr1" not in _show(C03, "configs/workspaces/bottled-water-dday/workspace.contract.yaml")


def test_uat01_r2_fr1_lineage_and_evidence_only_child():
    profile = _show(FR1, PROFILE)
    assert "profile_id: dday-bw-runtime-fr1" in profile
    assert "contract_version: dday-bw-b1-v2" in profile
    mapped = [
        line
        for line in profile.splitlines()
        if "signal_id:" in line and "class:" in line and "operating_state" not in line
    ]
    assert len(mapped) == 22
    assert "class RuntimeProfileScheduler" in _show(FR1, "src/virtual_factory/workspaces/plantos_export.py")
    assert "def publish_live_mqtt" in _show(FR1, "src/virtual_factory/workspaces/bottled_water.py")
    dict_bytes = subprocess.check_output(["git", "show", f"{FR1}:{DICTIONARY}"], cwd=REPO)
    import hashlib

    assert hashlib.sha256(dict_bytes).hexdigest() == DICT_SHA
    c03_dict = subprocess.check_output(["git", "show", f"{C03}:{DICTIONARY}"], cwd=REPO)
    assert hashlib.sha256(c03_dict).hexdigest() == DICT_SHA
    diff = _git("diff", "--name-only", FR1, FR1_EVIDENCE)
    names = {line for line in diff.splitlines() if line}
    assert names == {
        ".ai-harness/sa-review/CURRENT.md",
        ".ai-harness/sa-review/evidence/DDAY-FR1/01-scope.md",
        ".ai-harness/sa-review/evidence/DDAY-FR1/machine-evidence.json",
        ".ai-harness/sa-review/reports/DDAY-FR1.md",
    }
    evidence = json.loads(
        (REPO / ".ai-harness/sa-review/evidence/DDAY-FR1/machine-evidence.json").read_text()
    )
    assert evidence["head"] == FR1
    assert evidence["contract_version"] == "dday-bw-b1-v2"


def test_uat01_r3_no_persistent_bw_mqtt_service_entrypoint():
    dockerfile = (REPO / "Dockerfile").read_text(encoding="utf-8")
    assert "run" in dockerfile and "--steps" in dockerfile
    assert "bottled-water-dday" not in dockerfile
    compose = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    assert "bottled-water-dday" not in compose
    assert "publish_live_mqtt" not in compose
    unit = (REPO / "deploy/virtual-factory.service").read_text(encoding="utf-8")
    assert "compressor_train_benchmark_01.yaml" in unit
    assert "bottled-water" not in unit
    main_text = (REPO / "src/virtual_factory/main.py").read_text(encoding="utf-8")
    assert 'add_parser("run"' in main_text
    assert 'add_parser("serve"' in main_text
    assert "publish_live_mqtt" not in main_text
    assert "dday-bw" not in main_text
    vf2 = (REPO / "deploy/vf2.Dockerfile").read_text(encoding="utf-8")
    assert "bottled-water-dday" not in vf2


def test_uat01_r4_http_autorun_does_not_publish_plantos_export():
    api_text = (REPO / "src/virtual_factory/ui/api.py").read_text(encoding="utf-8")
    assert "async def _bw_autorun_loop" in api_text
    assert "factory.step()" in api_text
    assert "publish_live_mqtt" not in api_text
    runtime = (REPO / "src/virtual_factory/ui/runtime_service.py").read_text(encoding="utf-8")
    assert "publish_frame" in runtime
    assert "plantos_export" not in runtime
    assert "publish_live_mqtt" not in runtime


def test_uat01_r5_timestamp_and_mqtt_auth_surface_unchanged():
    assert CONTRACT_VERSION == "dday-bw-b1-v2"
    assert UTC_EPOCH.isoformat().replace("+00:00", "Z") == "2026-10-03T00:00:00Z"
    assert utc_timestamp(0) == "2026-10-03T00:00:00.000Z"
    assert utc_timestamp(610) == "2026-10-03T00:10:10.000Z"
    create = inspect.getsource(MqttGateway._create_client)
    assert "username" not in create
    assert "password" not in create
    assert "username" not in MqttGateway.__dataclass_fields__
    assert "password" not in MqttGateway.__dataclass_fields__


def test_uat01_r6_recon_evidence_does_not_invent_uat_facts():
    path = REPO / ".ai-harness/sa-review/evidence/DDAY-VF-UAT-01/machine-evidence.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["c03_sha_has_runtime_profile"] is False
    assert data["fr1_implementation_sha"] == FR1
    assert data["persistent_bw_mqtt_entrypoint"] is False
    assert data["deploy_authorized"] is False
    assert data["uat_live_inspect"]["result"] in {"PASS", "UNKNOWN"}
    assert data["tdengine_max_source_timestamp"]["result"] in {"PASS", "UNKNOWN"}
    if data["uat_live_inspect"]["result"] == "UNKNOWN":
        assert data["uat_live_inspect"]["invented_credentials"] is False
    if data["tdengine_max_source_timestamp"]["result"] == "UNKNOWN":
        assert data["tdengine_max_source_timestamp"]["measured_max"] is None
        assert data["tdengine_max_source_timestamp"]["historian_modified"] is False
