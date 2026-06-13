"""Graph representation for configured plant models."""

from dataclasses import dataclass, field
from typing import Any

from virtual_factory.core.schema import PlantConfig, endpoint_object_id


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
    def from_config(cls, config: PlantConfig) -> "PlantGraph":
        """Build a minimal graph from a validated plant configuration."""
        graph = cls()

        for category in ("equipment", "sensors", "controllers", "actuators"):
            items = getattr(config, category)
            for item in items:
                graph.nodes[item.id] = GraphNode(id=item.id, category=category, config=item.model_dump())

        for connection in config.connections:
            graph.edges.append(
                GraphEdge(
                    source=connection.from_endpoint,
                    target=connection.to,
                    category=connection.type,
                    config=connection.model_dump(by_alias=True),
                )
            )

        for sensor in config.sensors:
            graph.edges.append(
                GraphEdge(
                    source=sensor.measures,
                    target=sensor.output_signal,
                    category="measurement",
                    config=sensor.model_dump(),
                )
            )

        for controller in config.controllers:
            graph.edges.append(
                GraphEdge(
                    source=controller.pv_signal,
                    target=controller.output_signal,
                    category="control",
                    config=controller.model_dump(),
                )
            )

        for actuator in config.actuators:
            graph.edges.append(
                GraphEdge(
                    source=actuator.command_signal,
                    target=actuator.actuates,
                    category="actuation",
                    config=actuator.model_dump(),
                )
            )

        return graph


__all__ = ["GraphEdge", "GraphNode", "PlantGraph", "endpoint_object_id"]
