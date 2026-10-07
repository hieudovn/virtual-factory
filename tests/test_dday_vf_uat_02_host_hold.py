"""DDAY-VF-UAT-02 — UAT host evidence must not contain secrets or start Run B."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / ".ai-harness/sa-review/evidence/DDAY-VF-UAT-02/machine-evidence.json"
SHA = "d7db6d0909da968c2b4a4ea2cdb712e5d7601282"


def test_uat02_evidence_frozen_sha_and_run_b_hold():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["accepted_vf_sha"] == SHA
    assert data["deployed_vf_source_sha"] == SHA
    assert data["run_a_started"] is True
    assert data["run_b_started"] is False
    assert data["password_stored_in_repo"] is False
    assert data["container"]["public_ports"] == {}
    text = EVIDENCE.read_text(encoding="utf-8")
    assert "BiPsiKKz" not in text
    assert "#2026" not in text
