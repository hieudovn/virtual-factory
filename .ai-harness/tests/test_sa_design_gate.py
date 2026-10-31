"""Offline guard tests for SA design gate; no GitHub credentials required."""
import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "sa_design_gate.py"
spec = importlib.util.spec_from_file_location("sa_design_gate", MODULE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

BASE = "04fb9413bd5af3c4f0457047267a60b3ea4e94fe"
GOV_TASK = ".ai-harness/sa-design/tasks/TIPA-VF-SA-GOV-01.json"
DOC_TASK = ".ai-harness/sa-design/tasks/TIPA-VF-SA-DES-01.json"


def contract(kind="design"):
    task = DOC_TASK if kind == "design" else GOV_TASK
    return {
        "task_id": "TIPA-VF-SA-DES-01" if kind == "design" else "TIPA-VF-SA-GOV-01",
        "class": kind, "repository": gate.REPO,
        "branch": "sa/design/test" if kind == "design" else "sa/governance/test",
        "expected_base_sha": BASE, "approval_issue": 130,
        "authority": "SA_DESIGN_DRAFT" if kind == "design" else "PO_APPROVED_GOVERNANCE",
        "allowed_paths": [task, "docs/plans/tipa-test.md"],
    }


class TestSaDesignGate(unittest.TestCase):
    def check(self, task, paths):
        return gate.validate_contract(task, branch=task["branch"],
             repository=gate.REPO, base=BASE, paths=paths)

    def test_valid_sa_design(self):
        t = contract()
        self.assertEqual(self.check(t, t["allowed_paths"])["class"], "design")

    def test_reject_runtime_source_even_if_allowlisted(self):
        t = contract()
        t["allowed_paths"].append("src/virtual_factory/core.py")
        with self.assertRaises(gate.DesignGateError):
            self.check(t, t["allowed_paths"])

    def test_reject_pm_contract_change(self):
        t = contract()
        t["allowed_paths"].append(".ai-harness/PM-EXECUTION-CONTRACT.md")
        with self.assertRaises(gate.DesignGateError):
            self.check(t, t["allowed_paths"])

    def test_reject_branch_spoofing(self):
        t = contract()
        t["branch"] = "sa/governance/test"
        with self.assertRaises(gate.DesignGateError):
            self.check(t, t["allowed_paths"])

    def test_reject_baseline_drift(self):
        t = contract()
        t["expected_base_sha"] = "b" * 40
        with self.assertRaises(gate.DesignGateError):
            self.check(t, t["allowed_paths"])

    def test_reject_missing_contract(self):
        t = contract()
        with self.assertRaises(gate.DesignGateError):
            self.check(t, ["docs/plans/tipa-test.md"])

    def test_governance_needs_po_authority(self):
        t = contract("governance")
        t["authority"] = "SA_APPROVED_DESIGN"
        with self.assertRaises(gate.DesignGateError):
            self.check(t, t["allowed_paths"])

    def test_governance_explicit_extra_allowed(self):
        t = contract("governance")
        t["allowed_paths"].append("AGENTS.md")
        self.assertEqual(self.check(t, t["allowed_paths"])["class"], "governance")

    def test_reject_governance_unspecified_extra(self):
        t = contract("governance")
        t["allowed_paths"].append(".github/workflows/vf-dm-ci.yml")
        with self.assertRaises(gate.DesignGateError):
            self.check(t, t["allowed_paths"])

    def test_reject_gov_bool_issue(self):
        t = contract("governance")
        t["approval_issue"] = True
        with self.assertRaises(gate.DesignGateError):
            self.check(t, t["allowed_paths"])


if __name__ == "__main__":
    unittest.main()
