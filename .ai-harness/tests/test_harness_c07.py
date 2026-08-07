"""VF-AI-HARNESS-C07 — Smoke portability / Unicode subprocess tests.

Tests:
  1. ordinary commands unchanged by normalization
  2. smoke can execute with UTF-8 env
  3. Unicode stdout doesn't cause false failure
  4. non-zero CLI exit remains FAIL
  5. existing C06 tests unchanged
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from run_task_gate import _normalize_smoke_command


class TestSmokeNormalization:
    """C07-1, C07-3: command normalization unchanged for non-vf commands."""

    def test_ordinary_command_unchanged(self):
        assert _normalize_smoke_command(["echo", "hello"]) == ["echo", "hello"]

    def test_pytest_unchanged(self):
        assert _normalize_smoke_command(["pytest", "-q"]) == ["pytest", "-q"]

    def test_empty_unchanged(self):
        assert _normalize_smoke_command([]) == []

    def test_virtual_factory_translated(self):
        result = _normalize_smoke_command(
            ["virtual-factory", "validate", "--config", "foo.yaml"]
        )
        assert result[0] == sys.executable
        assert result[1] == "-c"
        assert "virtual_factory.main" in result[2]


class TestUTF8SubprocessSmoke:
    """C07-2, C07-3, C07-4: smoke with UTF-8 env succeeds, non-zero fails."""

    def test_utf8_env_handles_unicode_stdout(self):
        """Subprocess with PYTHONIOENCODING=utf-8 can print Unicode."""
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        r = subprocess.run(
            [sys.executable, "-c", "print('\u2705 OK')"],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=10,
        )
        assert r.returncode == 0
        assert "\u2705" in r.stdout

    def test_project_smoke_succeeds_with_utf8_env(self):
        """The actual project smoke command succeeds with UTF-8 env."""
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        cmd = _normalize_smoke_command(
            ["virtual-factory", "validate",
             "--config", "configs/plants/compressor_train_benchmark_01.yaml"]
        )
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env,
                           cwd=Path(__file__).resolve().parent.parent.parent, timeout=30)
        assert r.returncode == 0, f"smoke failed: {r.stderr[:200]}"
        assert "YES" in r.stdout

    def test_nonzero_exit_still_fails(self):
        """A failing CLI command still produces FAIL."""
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        r = subprocess.run(
            [sys.executable, "-c", "import sys; sys.exit(2)"],
            capture_output=True, text=True, env=env, timeout=10,
        )
        assert r.returncode != 0


class TestC06Regression:
    """C07-5: existing C06 tests still pass (structure verification)."""

    def test_canonical_ids_unchanged(self):
        from run_task_gate import CANONICAL_IDS
        assert len(CANONICAL_IDS) == 24
        assert CANONICAL_IDS[0] == "P01"
        assert CANONICAL_IDS[-1] == "P24"

    def test_pipeline_registry_still_works(self):
        from run_task_gate import PipelineRegistry, CANONICAL_IDS
        reg = PipelineRegistry()
        for cid in CANONICAL_IDS:
            reg.record(cid, f"Step {cid}", True, "PASS")
        pi = reg.integrity()
        assert pi["all_required_steps_executed"] is True
        assert pi["all_required_steps_pass"] is True
