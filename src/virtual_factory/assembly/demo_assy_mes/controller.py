"""TIPA ASSY Customer Demo Scenario v1 — control surface.

VF-DM-DEMO-ASSY-MES-01. Minimal control surface over DemoRunner:
reset / start / pause / trigger jam / recover / snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass

from virtual_factory.assembly.demo_assy_mes.runner import DemoRunner


@dataclass
class DemoController:
    """Wraps DemoRunner with the customer-facing control surface."""

    runner: DemoRunner

    def reset(self) -> dict:
        self.runner.reset()
        return self.runner.snapshot()

    def start(self) -> dict:
        # C02: start must NOT process the whole timeline synchronously;
        # it only enables stepping. Advancement happens via step().
        self.runner.start()
        return self.runner.snapshot()

    def pause(self) -> dict:
        self.runner.pause()
        return self.runner.snapshot()

    def step(self) -> dict:
        self.runner.step()
        return self.runner.snapshot()

    def trigger_jam(self) -> dict:
        self.runner.trigger_jam()
        return self.runner.snapshot()

    def recover(self) -> dict:
        self.runner.recover()
        return self.runner.snapshot()

    def snapshot(self) -> dict:
        return self.runner.snapshot()

    def messages(self) -> list[dict]:
        return [
            {
                "message_key": m.key,
                "projection_id": m.projection_id,
                "message_type": m.message_type,
                "schema_name": m.schema_name,
                "schema_version": m.schema_version,
                "headers": dict(m.headers),
                "payload": dict(m.payload),
            }
            for m in self.runner.delivered_messages()
        ]
