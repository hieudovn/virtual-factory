"""DDAY-VF-UAT-03 — current closeout evidence and SHA distinction."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / ".ai-harness/sa-review/evidence/DDAY-VF-UAT-03/machine-evidence.json"
CURRENT = REPO / ".ai-harness/sa-review/CURRENT.md"
OLD_HOLD_TEST = REPO / "tests/test_dday_vf_uat_02_host_hold.py"
VF_SHA = "d7db6d0909da968c2b4a4ea2cdb712e5d7601282"
PLANTOS_SHA = "a1695c5457515e2b565a5f9fe107c1e18b3e0879"


def test_uat03_records_run_b_completed_and_three_shas():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["canonical_current"] is True
    assert data["deployed_vf_runtime_sha"] == VF_SHA
    assert data["plantos_accepted_uat_merge_sha"] == PLANTOS_SHA
    assert data["uat02_historical_head"] == "a8d5ecba1b0794251fd9c618c338de449263a0b0"
    assert data["run_b_completed"] is True
    assert data["run_b_hold_current"] is False
    assert data["run_b"]["reused_vf_source_timestamps"] is True
    assert data["reset_dday_receive_epoch"]["succeeded"] is True
    assert data["vf_product_changed"] is False


def test_no_live_run_b_hold_invariant():
    assert not OLD_HOLD_TEST.is_file()
    current = CURRENT.read_text(encoding="utf-8")
    assert "Run B HOLD" not in current
    assert "Run B completed" in current
    assert VF_SHA in current
    assert PLANTOS_SHA in current
