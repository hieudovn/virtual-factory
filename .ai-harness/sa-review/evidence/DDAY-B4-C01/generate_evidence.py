#!/usr/bin/env python3
"""Regenerate DDAY-B4-C01 machine facts (B3 blob ids, C01-scope file list)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
C01_BASE = "0f9606bbc8690e80cfdbf9c4105bcfa998e6e0e8"
B3_BASE = "23b6208266751a8c508b0d96fd7a736dffc5676c"
B3_FILES = (
    ".ai-harness/sa-review/evidence/DDAY-B3/generate_evidence.py",
    ".ai-harness/sa-review/evidence/DDAY-B3/smoke_bottled_water_ui.py",
)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def main() -> None:
    blobs = {path: _git("rev-parse", f"{B3_BASE}:{path}") for path in B3_FILES}
    head_blobs = {path: _git("rev-parse", f"HEAD:{path}") for path in B3_FILES}
    changed = [line for line in _git("diff", "--name-only", C01_BASE, "HEAD").splitlines() if line]
    payload = {
        "c01_baseline": C01_BASE,
        "head": _git("rev-parse", "HEAD"),
        "b3_blobs_at_23b6208": blobs,
        "b3_blobs_at_head": head_blobs,
        "b3_match": blobs == head_blobs,
        "files_vs_c01_baseline": changed,
    }
    (HERE / "generated-head-facts.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
