"""Disturbance Engine — generates values for 7 Disturbance Variables."""

from __future__ import annotations

import math
import random
from typing import Any

from .models import DVConfig, clamp, seeded_rng


class DisturbanceEngine:
    """Generates realistic values for 7 disturbance variables.

    Each DV follows either random_walk (with mean-reversion) or sine pattern.
    """

    def __init__(self, dv_configs: dict[str, DVConfig]) -> None:
        self.configs = dv_configs
        self.state: dict[str, dict[str, Any]] = {}
        self.overrides: dict[str, float | None] = {}
        for sid, cfg in dv_configs.items():
            self.state[sid] = {"current": cfg.baseline, "phase": random.random() * 2 * math.pi}

    def override(self, signal_id: str, value: float) -> None:
        """Force a DV to a specific value (for scenario injection)."""
        if signal_id in self.configs:
            self.overrides[signal_id] = value

    def release_override(self, signal_id: str) -> None:
        """Release override, resume normal DV generation."""
        self.overrides.pop(signal_id, None)

    def step(self, dt_s: float, rng: random.Random | None = None) -> dict[str, float]:
        """Advance all DVs by dt_s seconds. Returns {signal_id: value}."""
        rng = rng or seeded_rng()
        results: dict[str, float] = {}

        for sid, cfg in self.configs.items():
            # Check override
            if sid in self.overrides and self.overrides[sid] is not None:
                results[sid] = self.overrides[sid]
                continue

            state = self.state[sid]
            current = state["current"]

            if cfg.pattern == "random_walk":
                step = rng.gauss(0, 0.3) * math.sqrt(dt_s)
                current += step
                # Mean-reversion toward baseline
                current += (cfg.baseline - current) * 0.01 * dt_s
                current = clamp(current, cfg.bounds_min, cfg.bounds_max)
                # Add noise
                value = current + rng.gauss(0, cfg.noise_std) * math.sqrt(dt_s)
                value = clamp(value, cfg.bounds_min, cfg.bounds_max)
                state["current"] = current

            elif cfg.pattern == "sine":
                state["phase"] += 2 * math.pi * cfg.frequency_hz * dt_s
                value = cfg.baseline + cfg.amplitude * math.sin(state["phase"])
                value += rng.gauss(0, cfg.noise_std) * math.sqrt(dt_s)
                value = clamp(value, cfg.bounds_min, cfg.bounds_max)

            else:
                value = cfg.baseline

            results[sid] = round(value, 4)

        return results

    def get_status(self) -> dict[str, Any]:
        """Return current status of all DVs."""
        return {
            sid: {
                "config": {
                    "pattern": cfg.pattern,
                    "baseline": cfg.baseline,
                    "bounds_min": cfg.bounds_min,
                    "bounds_max": cfg.bounds_max,
                },
                "overridden": sid in self.overrides,
            }
            for sid, cfg in self.configs.items()
        }
