from pathlib import Path

from virtual_factory.scenarios.scenario_loader import load_scenario


def test_loads_demand_change_scenario() -> None:
    """Scenario loader should parse standalone scenario YAML files."""
    scenario = load_scenario(Path("configs/scenarios/demand_change.yaml"))

    assert scenario.id == "demand_change"
    assert scenario.actions[0].type == "set_parameter"
    assert scenario.actions[0].target == "equipment.T102.outlet_demand_m3_s"
