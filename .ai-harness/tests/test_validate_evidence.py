"""Test validate_evidence.py — contradiction detection."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validate_evidence import validate_evidence


def _load(name: str) -> dict:
    p = Path(__file__).resolve().parent.parent / "examples" / name
    with open(p) as f:
        return json.load(f)


class TestValidateEvidence:
    def test_valid_ready_is_consistent(self):
        e = _load("valid-ready-evidence.json")
        ok, contradictions = validate_evidence(e)
        assert ok
        assert len(contradictions) == 0

    def test_valid_merged_is_consistent(self):
        e = _load("valid-merged-awaiting-review.json")
        ok, _ = validate_evidence(e)
        assert ok

    def test_stale_ci_detected(self):
        e = _load("invalid-stale-ci-evidence.json")
        ok, contradictions = validate_evidence(e)
        assert not ok
        assert any("CI head" in c or "stale" in c.lower() for c in contradictions)

    def test_missing_commit_detected(self):
        e = _load("invalid-missing-commit-evidence.json")
        ok, contradictions = validate_evidence(e)
        assert not ok

    def test_local_only_detected(self):
        e = _load("invalid-local-only-evidence.json")
        ok, contradictions = validate_evidence(e)
        assert not ok

    def test_false_platform_state_detected(self):
        e = _load("invalid-false-platform-state.json")
        ok, contradictions = validate_evidence(e)
        assert not ok
        assert any("platform" in c.lower() for c in contradictions)

    def test_local_only_ready_flag(self):
        e = _load("invalid-local-only-evidence.json")
        e["derived_status"] = "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW"
        ok, c = validate_evidence(e)
        assert not ok
        assert any("local" in x.lower() or "remote" in x.lower() for x in c)

    def test_m2_s04_closed_is_consistent(self):
        e = _load("m2-s04-closed-evidence.json")
        ok, _ = validate_evidence(e)
        assert ok
