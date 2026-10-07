"""DDAY-VF-UAT-02 Run A inspect is historical, not a live Run B HOLD invariant."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / ".ai-harness/sa-review/evidence/DDAY-VF-UAT-02/machine-evidence.json"
SHA = "d7db6d0909da968c2b4a4ea2cdb712e5d7601282"


def test_uat02_is_historical_run_a_snapshot():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["evidence_role"] == "historical_run_a"
    assert data["canonical_current"] is False
    assert data["superseded_by"] == "DDAY-VF-UAT-03"
    assert data["accepted_vf_sha"] == SHA
    assert data["run_a_started"] is True
    assert data["password_stored_in_repo"] is False
    # Snapshot fact at 2026-10-07T02:44:46Z only — not current UAT state.
    assert data["inspected_at_utc"] == "2026-10-07T02:44:46Z"
