"""Test PipelineRegistry and canonical pipeline integrity."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from run_task_gate import PipelineRegistry, CANONICAL_IDS


class TestPipelineRegistry:
    def test_records_all_canonical_ids(self):
        reg = PipelineRegistry()
        for cid in CANONICAL_IDS:
            reg.record(cid, f"Step {cid}", True, "PASS")
        pi = reg.integrity()
        assert pi["actual_ids"] == CANONICAL_IDS
        assert pi["missing_ids"] == []
        assert pi["duplicate_ids"] == []
        assert pi["unexpected_ids"] == []
        assert pi["required_count"] == len(CANONICAL_IDS)
        assert pi["all_required_steps_executed"]
        assert pi["all_required_steps_pass"]

    def test_empty_pipeline_fails(self):
        reg = PipelineRegistry()
        pi = reg.integrity()
        assert not pi["all_required_steps_executed"]
        assert not pi["all_required_steps_pass"]
        assert pi["required_count"] == 0

    def test_missing_id_fails(self):
        reg = PipelineRegistry()
        for cid in CANONICAL_IDS[:20]:
            reg.record(cid, f"Step {cid}", True, "PASS")
        pi = reg.integrity()
        assert pi["missing_ids"]
        assert not pi["all_required_steps_executed"]

    def test_duplicate_id_fails(self):
        reg = PipelineRegistry()
        reg.record("P01", "Step 1", True, "PASS")
        try:
            reg.record("P01", "Step 1 dup", True, "PASS")
            assert False, "Should have raised"
        except RuntimeError:
            pass

    def test_unexpected_id_fails(self):
        reg = PipelineRegistry()
        for cid in CANONICAL_IDS:
            reg.record(cid, f"Step {cid}", True, "PASS")
        reg.steps.append({"id": "P99", "name": "Extra", "required": True, "executed": True, "result": "PASS"})
        reg.index["P99"] = reg.steps[-1]
        pi = reg.integrity()
        assert "P99" in pi["unexpected_ids"]

    def test_update_by_id_preserves_others(self):
        reg = PipelineRegistry()
        for cid in CANONICAL_IDS:
            reg.record(cid, f"Step {cid}", True, "PASS")
        reg.update_result("P07", "FAIL")
        assert reg.index["P07"]["result"] == "FAIL"
        assert reg.index["P10"]["result"] == "PASS"

    def test_failed_step_prevents_all_pass(self):
        reg = PipelineRegistry()
        for cid in CANONICAL_IDS:
            reg.record(cid, f"Step {cid}", True, "PASS")
        reg.update_result("P07", "FAIL")
        pi = reg.integrity()
        assert not pi["all_required_steps_pass"]

    def test_canonical_ids_contains_23_steps(self):
        assert len(CANONICAL_IDS) == 23
        assert CANONICAL_IDS[0] == "P01"
        assert CANONICAL_IDS[-1] == "P23"
