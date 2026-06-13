"""MQTT gateway skeleton.

Network publishing is intentionally not implemented in this phase.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class MQTTGateway:
    """Future MQTT publisher for allowed industrial telemetry signals."""

    broker_url: str
    topic_prefix: str

    def publish(self, topic: str, payload: dict) -> None:
        """Publish a payload when MQTT support is implemented."""
        raise NotImplementedError("MQTT network publishing is not implemented yet.")
