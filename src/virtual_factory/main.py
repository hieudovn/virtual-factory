"""Command-line entry point for Virtual Factory."""

from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine


def main() -> None:
    """Run a tiny closed-loop signal-flow demo."""
    config_path = Path("configs/plants/continuous_mvp_01.yaml")
    config = load_plant_config(config_path)
    engine = SimulationEngine(config)
    engine.initialize()

    snapshot = {}
    for _ in range(3):
        snapshot = engine.step()

    compact = {
        "LT102_LEVEL": snapshot["signals"].get("LT102_LEVEL"),
        "LIC102_OUT": snapshot["signals"].get("LIC102_OUT"),
        "V101_OPENING_FEEDBACK": snapshot["signals"].get("V101_OPENING_FEEDBACK"),
        "truth.V101.opening_actual": snapshot["truth"].get("V101.opening_actual"),
        "truth.T102.level_true": snapshot["truth"].get("T102.level_true"),
    }
    print(compact)


if __name__ == "__main__":
    main()
