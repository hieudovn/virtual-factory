"""Graph representation for configured plant models."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class GraphNode:
    """Configured graph node for equipment, sensors, controllers, or actuators."""

    id: str
    category: str
    config: dict[str, Any]


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """Configured relationship between two graph endpoints."""

    source: str
    target: str
    category: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlantGraph:
    """Plant graph built from configuration rather than engine constants."""

    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "PlantGraph":
        """Build a minimal graph from a plant configuration dictionary."""
        graph = cls()

        for category in ("equipment", "sensors", "controllers", "actuators", "gateways"):
            items = config.get(category, [])
            if isinstance(items, dict):
                items = items.values()
            for item in items:
                node_id = item.get("id")
                if node_id:
                    graph.nodes[node_id] = GraphNode(id=node_id, category=category, config=item)

        for connection in config.get("connections", []):
            graph.edges.append(
                GraphEdge(
                    source=connection["from"],
                    target=connection["to"],
                    category=connection.get("type", "physical"),
                    config=connection,
                )
            )

        for sensor in config.get("sensors", []):
            if "measures" in sensor and "output_signal" in sensor:
                graph.edges.append(
                    GraphEdge(
                        source=sensor["measures"],
                        target=sensor["output_signal"],
                        category="measurement",
                        config=sensor,
                    )
                )

        for controller in config.get("controllers", []):
            if "pv_signal" in controller and "output_signal" in controller:
                graph.edges.append(
                    GraphEdge(
                        source=controller["pv_signal"],
                        target=controller["output_signal"],
                        category="control",
                        config=controller,
                    )
                )

        for actuator in config.get("actuators", []):
            if "command_signal" in actuator and "actuates" in actuator:
                graph.edges.append(
                    GraphEdge(
                        source=actuator["command_signal"],
                        target=actuator["actuates"],
                        category="actuation",
                        config=actuator,
                    )
                )

        return graph
