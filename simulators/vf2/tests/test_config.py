"""Tests for VF-2 configuration loader."""

from __future__ import annotations

from simulators.vf2.config import Vf2Config, load_config


def test_load_default_config():
    config = load_config()  # Uses default path
    assert isinstance(config, Vf2Config)
    assert config.name == "vf2-sim-01"
    assert config.api_port == 8102
    assert config.interval_s == 1.0


def test_load_nonexistent_returns_defaults():
    config = load_config("nonexistent.yaml")
    assert config.api_port == 8102


def test_config_dataclass_defaults():
    config = Vf2Config()
    assert config.name == "vf2-sim-01"
    assert config.api_port == 8102
    assert config.interval_s == 1.0
    assert config.output_mode == "memory"
