"""Package loader — reads & validates a PIM-generated VF-2 simulation package.

Usage:
    from simulators.vf2.package_loader import load_package
    pkg = load_package("path/to/package.json")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import VF2Package

SUPPORTED_SCHEMA_VERSIONS = ["1.0"]


def load_package(path: str | Path) -> VF2Package:
    """Load a PIM-generated VF-2 simulation package from JSON.

    Args:
        path: Path to the package JSON file.

    Returns:
        VF2Package: Fully validated Pydantic model.

    Raises:
        FileNotFoundError: If *path* doesn't exist.
        ValueError: If *schema_version* is not supported.
        pydantic.ValidationError: If the package structure is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Package file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    # Check schema version before full validation
    version = data.get("schema_version", "unknown")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"Unsupported schema version: {version}. "
            f"VF-2 supports: {SUPPORTED_SCHEMA_VERSIONS}"
        )

    return VF2Package.model_validate(data)
