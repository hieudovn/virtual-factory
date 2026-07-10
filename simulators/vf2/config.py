"""VF-2 runtime configuration loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


@dataclass
class Vf2Config:
    name: str = "vf2-sim-01"
    source: str = "vf2-sim-01"
    interval_s: float = 1.0
    max_frames_buffer: int = 3600
    auto_start: bool = False
    output_mode: str = "memory"
    output_csv_path: str = "./out/vf2_output.csv"
    output_csv_append: bool = False
    default_scenario: str = ""
    transition_s: float = 30.0
    api_host: str = "0.0.0.0"
    api_port: int = 8102
    log_level: str = "INFO"


def load_config(path: str | Path | None = None) -> Vf2Config:
    """Load VF-2 configuration from YAML file.

    If *path* is ``None``, the default ``config.yaml`` next to this module
    is used.  If the file does not exist, default values are returned.
    """
    if path is None:
        path = DEFAULT_CONFIG_PATH
    path = Path(path)

    if not path.exists():
        return Vf2Config()

    with open(path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    sim = data.get("simulator", {})
    out = data.get("output", {})
    csv_cfg = out.get("csv", {})
    scn = data.get("scenario", {})
    api = data.get("api", {})
    log = data.get("logging", {})

    return Vf2Config(
        name=sim.get("name", "vf2-sim-01"),
        source=sim.get("source", "vf2-sim-01"),
        interval_s=float(sim.get("interval_s", 1.0)),
        max_frames_buffer=int(sim.get("max_frames_buffer", 3600)),
        auto_start=bool(sim.get("auto_start", False)),
        output_mode=out.get("default_mode", "memory"),
        output_csv_path=csv_cfg.get("path", "./out/vf2_output.csv"),
        output_csv_append=bool(csv_cfg.get("append", False)),
        default_scenario=scn.get("default", ""),
        transition_s=float(scn.get("transition_s", 30.0)),
        api_host=api.get("host", "0.0.0.0"),
        api_port=int(api.get("port", 8102)),
        log_level=log.get("level", "INFO"),
    )
