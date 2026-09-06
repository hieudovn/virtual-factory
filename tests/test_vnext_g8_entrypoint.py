"""VF-vNEXT-G8-C01 — canonical baseline entrypoint bounded smoke tests.

Issue #53 / SA `5557658309` requirement 5: prove that a FAILING command group
(an explicit repo-native command, a distinct code path from pytest groups)
makes the canonical baseline exit non-zero and NAME the failing group. These are
bounded subprocess smokes against the repo-native entrypoint with throwaway
manifests (no real groups, no nested pytest, no framework added).

Throwaway manifests are written under the repo's gitignored ``.ai-harness/traces``
directory (avoids the pytest tmp_path base on hosts where that base is locked).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / ".ai-harness" / "regression" / "run_vnext_baseline.py"
SMOKE_DIR = ROOT / ".ai-harness" / "traces" / "g8_smoke"


def _run_runner(manifest: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--manifest", str(manifest)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _write_manifest(groups: list[dict], tmp_dir: Path) -> Path:
    manifest = tmp_dir / "manifest.json"
    manifest.write_text(
        json.dumps({"schema": "smoke", "version": "t", "groups": groups}),
        encoding="utf-8",
    )
    return manifest


class _SmokeCase(unittest.TestCase):
    def setUp(self) -> None:
        SMOKE_DIR.mkdir(parents=True, exist_ok=True)
        self._tmp = Path(tempfile.mkdtemp(prefix="case_", dir=str(SMOKE_DIR)))

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)


class TestCommandGroupFailurePath(_SmokeCase):
    def test_failing_command_group_exits_nonzero_and_names_group(self):
        manifest = _write_manifest(
            [
                {
                    "id": "g_bad_command",
                    "gate": "CHECKS",
                    "type": "command",
                    "cmd": [sys.executable, "-c", "import sys; sys.exit(9)"],
                }
            ],
            self._tmp,
        )
        proc = _run_runner(manifest)
        self.assertNotEqual(proc.returncode, 0)  # non-zero overall failure
        combined = proc.stdout + proc.stderr
        self.assertIn("g_bad_command", combined)  # names the failing group
        self.assertIn("BASELINE FAILED groups: g_bad_command", combined)

    def test_passing_command_group_exits_zero(self):
        manifest = _write_manifest(
            [
                {
                    "id": "g_ok_command",
                    "gate": "CHECKS",
                    "type": "command",
                    "cmd": [sys.executable, "-c", "print('ok')"],
                }
            ],
            self._tmp,
        )
        proc = _run_runner(manifest)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("BASELINE PASSED", proc.stdout)

    def test_python_token_substituted_in_command_group(self):
        manifest = _write_manifest(
            [
                {
                    "id": "g_python_token",
                    "gate": "CHECKS",
                    "type": "command",
                    "cmd": ["{python}", "-c", "import sys; print(sys.executable)"],
                }
            ],
            self._tmp,
        )
        proc = _run_runner(manifest)
        self.assertEqual(proc.returncode, 0)
        # {python} must be substituted with the running interpreter.
        self.assertNotIn("{python}", proc.stdout + proc.stderr)
