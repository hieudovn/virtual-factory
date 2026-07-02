"""Configuration loader for the WTP Simulator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "wtp_config.yaml"


class WtpConfig:
    """WTP Simulator configuration loaded from YAML."""

    def __init__(self, data: dict[str, Any]) -> None:
        sim_cfg = data.get("simulator", {})
        self.name: str = sim_cfg.get("name", "wtp-sim-01")
        self.source: str = sim_cfg.get("source", "wtp-sim-01")
        self.interval_s: float = float(sim_cfg.get("interval_s", 1.0))
        self.max_frames_buffer: int = int(sim_cfg.get("max_frames_buffer", 3600))
        self.auto_start: bool = bool(sim_cfg.get("auto_start", True))

        plantos_cfg = data.get("plantos", {})
        self.plantos_base_url: str = plantos_cfg.get("base_url", "http://localhost:8000")
        self.plantos_ingest_endpoint: str = plantos_cfg.get("ingest_endpoint", "/api/v1/measurements/ingest")
        self.plantos_api_key: str = plantos_cfg.get("api_key", "")
        retry_cfg = plantos_cfg.get("retry", {})
        self.retry_max_retries: int = int(retry_cfg.get("max_retries", 5))
        self.retry_base_delay_s: float = float(retry_cfg.get("base_delay_s", 1.0))
        self.retry_max_delay_s: float = float(retry_cfg.get("max_delay_s", 30.0))
        self.retry_backoff_multiplier: float = float(retry_cfg.get("backoff_multiplier", 2.0))

        scen_cfg = data.get("scenario", {})
        self.default_scenario: str = scen_cfg.get("default", "normal_operation")
        self.transition_s: float = float(scen_cfg.get("transition_s", 30.0))

        api_cfg = data.get("api", {})
        self.api_host: str = api_cfg.get("host", "0.0.0.0")
        self.api_port: int = int(api_cfg.get("port", 8100))

        opcua_cfg = data.get("opcua", {})
        self.opcua_enabled: bool = bool(opcua_cfg.get("enabled", True))
        self.opcua_endpoint: str = opcua_cfg.get("endpoint", "opc.tcp://0.0.0.0:4841")
        self.opcua_namespace: str = opcua_cfg.get("namespace", "WTP-Simulator")

        log_cfg = data.get("logging", {})
        self.log_level: str = log_cfg.get("level", "INFO")

    @property
    def ingest_url(self) -> str:
        return f"{self.plantos_base_url.rstrip('/')}/{self.plantos_ingest_endpoint.lstrip('/')}"


def load_config(config_path: str | Path | None = None) -> WtpConfig:
    """Load configuration from a YAML file."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return WtpConfig(data)
