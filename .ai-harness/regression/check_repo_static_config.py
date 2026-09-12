#!/usr/bin/env python3
"""check_repo_static_config.py — truthful static/lint/type baseline check.

Reports whether the repository configures any static/lint/type tool
(ruff / mypy / black / pyright / flake8). It does NOT invent a tool: when none
is configured it prints that finding and passes (exit 0). If a configured
static tool is detected that the baseline does not execute, it fails (exit 1)
so the baseline cannot silently ignore newly-configured tooling.

Run from the repo root:
    python .ai-harness/regression/check_repo_static_config.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# (pyproject [tool.X] key, classic config filename)
TOOL_KEYS = ["ruff", "mypy", "black", "pyright", "flake8"]
TOOL_FILES = [".ruff.toml", "ruff.toml", "mypy.ini", "pyproject.toml",
              "setup.cfg", "tox.ini", "pyrightconfig.json", ".flake8"]

# Tool section names we care about inside pyproject.toml / setup.cfg / tox.ini.
def _config_file_has_tool(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    lowered = text.lower()
    return any(f"[{key}" in lowered or f"[tool.{key}" in lowered
               for key in TOOL_KEYS)


def main() -> int:
    detected: list[str] = []
    for key in TOOL_KEYS:
        # pyproject.toml section [tool.<key>] at repo root
        pyproject = ROOT / "pyproject.toml"
        if pyproject.exists() and f"[tool.{key}]" in pyproject.read_text(
            encoding="utf-8", errors="replace"
        ).lower():
            detected.append(f"pyproject.toml [tool.{key}]")
    for fname in (".ruff.toml", "ruff.toml", "mypy.ini",
                  "pyrightconfig.json", ".flake8"):
        if (ROOT / fname).exists():
            detected.append(fname)
    for fname in ("setup.cfg", "tox.ini"):
        path = ROOT / fname
        if path.exists() and _config_file_has_tool(path):
            detected.append(fname)

    if detected:
        print("STATIC CONFIG: configured but baseline does not execute it: "
              + ", ".join(detected))
        print("STATIC CONFIG: add the configured tool to the baseline or "
              "remove the config; nothing is silently invented here.")
        return 1

    print("STATIC CONFIG: no ruff/mypy/black/pyright/flake8 configured in this "
          "repo (truthful); no static tool invented by the G8 baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
