from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.plant_graph import PlantGraph


def test_plant_graph_can_be_built_from_config() -> None:
    """PlantGraph should be constructed from config without hard-coded MVP logic."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    graph = PlantGraph.from_config(config)

    assert "T101" in graph.nodes
    assert "LT102" in graph.nodes
    assert "LIC102" in graph.nodes
    assert "VA101" in graph.nodes
    assert any(edge.source == "T101.outlet" and edge.target == "P101.inlet" for edge in graph.edges)


def test_plant_graph_contains_expected_edge_categories() -> None:
    """Graph should include physical, measurement, control, and actuation edges."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    graph = PlantGraph.from_config(config)
    edge_categories = {edge.category for edge in graph.edges}

    assert {"physical", "measurement", "control", "actuation"} <= edge_categories
