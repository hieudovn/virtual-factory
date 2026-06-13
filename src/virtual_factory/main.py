"""Command-line entry point for Virtual Factory."""

import argparse
from pathlib import Path
from typing import Sequence

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine
from virtual_factory.telemetry.export import append_csv, append_jsonl, frame_to_records
from virtual_factory.telemetry.signal_value import SignalValue

DEFAULT_CONFIG = Path("configs/plants/continuous_mvp_01.yaml")
DISPLAY_SIGNALS = [
    "LT102_LEVEL",
    "LIC102_OUT",
    "V101_OPENING_FEEDBACK",
    "FT101_FLOW",
    "PT101_PRESSURE",
]


def get_frame_value(frame: list[SignalValue], signal_name: str, default=None):
    """Return a signal value from a telemetry frame."""
    for signal in frame:
        if signal.name == signal_name:
            return signal.value
    return default


def run_simulation(
    config_path: str | Path = DEFAULT_CONFIG,
    steps: int = 60,
    dt_s: float = 1.0,
    csv_output: str | Path | None = None,
    jsonl_output: str | Path | None = None,
    quiet: bool = False,
    debug_truth: bool = False,
) -> list[list[SignalValue]]:
    """Run a configured simulation and optionally export publishable telemetry."""
    config = load_plant_config(config_path)
    engine = SimulationEngine(config, dt_s=dt_s)
    frames: list[list[SignalValue]] = []

    if not quiet:
        print(_format_header(debug_truth))

    for _ in range(steps):
        snapshot = engine.step()
        frame = list(snapshot["telemetry_latest"])
        frames.append(frame)
        records = frame_to_records(frame)
        if csv_output:
            append_csv(csv_output, records)
        if jsonl_output:
            append_jsonl(jsonl_output, records)
        if not quiet:
            print(_format_row(frame, snapshot, debug_truth))

    return frames


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(prog="virtual-factory")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the MVP simulation demo.")
    run_parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Plant configuration YAML path.")
    run_parser.add_argument("--steps", type=int, default=60, help="Number of simulation steps.")
    run_parser.add_argument("--dt", type=float, default=1.0, help="Step duration in seconds.")
    run_parser.add_argument("--csv-output", default=None, help="Optional CSV telemetry output path.")
    run_parser.add_argument("--jsonl-output", default=None, help="Optional JSONL telemetry output path.")
    run_parser.add_argument("--debug-truth", action="store_true", help="Print selected truth values.")
    run_parser.add_argument("--quiet", action="store_true", help="Suppress console rows.")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Run the Virtual Factory command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        run_simulation(
            config_path=args.config,
            steps=args.steps,
            dt_s=args.dt,
            csv_output=args.csv_output,
            jsonl_output=args.jsonl_output,
            quiet=args.quiet,
            debug_truth=args.debug_truth,
        )
        return

    parser.print_help()


def _format_header(debug_truth: bool) -> str:
    columns = ["time_s", *DISPLAY_SIGNALS]
    if debug_truth:
        columns.append("truth.T102.level_true")
    return " | ".join(columns)


def _format_row(frame: list[SignalValue], snapshot: dict[str, object], debug_truth: bool) -> str:
    timestamp = frame[0].timestamp_s if frame else 0.0
    values = [_format_value(timestamp)]
    values.extend(_format_value(get_frame_value(frame, signal_name, "")) for signal_name in DISPLAY_SIGNALS)
    if debug_truth:
        truth = snapshot.get("truth", {})
        values.append(_format_value(truth.get("T102.level_true") if isinstance(truth, dict) else ""))
    return " | ".join(values)


def _format_value(value) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


if __name__ == "__main__":
    main()
