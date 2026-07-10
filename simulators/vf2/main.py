"""Command-line entry point for VF-2 PIM-native Simulation Runtime.

Usage::

    # Validate a package
    python -m simulators.vf2.main --package path/to/package.json --validate-only

    # Run dry simulation (60 steps)
    python -m simulators.vf2.main --package path/to/package.json --steps 60

    # Run with CSV output
    python -m simulators.vf2.main --package path/to/package.json --steps 60 --output csv

    # Run with scenario
    python -m simulators.vf2.main --package path/to/package.json --scenario SCN-PUMP-TRIP-002 --steps 120

    # Start API server
    python -m simulators.vf2.main --package path/to/package.json --api-server
"""

from __future__ import annotations

import argparse
import sys

from .config import Vf2Config, load_config
from .output.csv_output import CsvOutput
from .output.memory_output import MemoryOutput
from .output.stdout_output import StdoutOutput
from .package_loader import load_package
from .package_validator import validate_package
from .simulation_loop import Vf2SimulationLoop


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vf2-sim",
        description="VF-2 PIM-native Simulation Runtime",
    )
    parser.add_argument("--package", required=True, help="Path to PIM package JSON")
    parser.add_argument("--config", default=None, help="Path to config YAML")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Load and validate package, then exit",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=0,
        help="Number of simulation steps (0 = infinite in API mode, "
        "required for batch mode)",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help="Scenario ID to activate at start",
    )
    parser.add_argument(
        "--output",
        choices=["memory", "csv", "stdout"],
        default="memory",
        help="Output adapter (default: memory)",
    )
    parser.add_argument(
        "--output-path",
        default="./out/vf2_output.csv",
        help="Output path for CSV adapter",
    )
    parser.add_argument(
        "--api-server",
        action="store_true",
        help="Start FastAPI server instead of batch run",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8102,
        help="API server port (default: 8102)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    if args.port:
        config.api_port = args.port

    # ── 1. Load package ──────────────────────────────────────────────
    try:
        pkg = load_package(args.package)
        print(f"Loaded package: {pkg.package_id} "
              f"({len(pkg.objects)} objects, {len(pkg.signals)} signals)")
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # ── 2. Validate ──────────────────────────────────────────────────
    result = validate_package(pkg)
    has_fatal_errors = not result.valid

    for e in result.errors:
        print(f"  ERROR: {e}")
    for w in result.warnings:
        print(f"  WARNING: {w}")

    if args.validate_only:
        if result.valid:
            print("Validation OK — package is structurally valid.")
            return 0
        print("Validation FAILED — see errors above.")
        return 1

    if has_fatal_errors:
        print("Fatal validation errors. Aborting.")
        return 1

    # ── 3. Create simulator ──────────────────────────────────────────
    loop = Vf2SimulationLoop(pkg, config)

    # ── 4. Output adapter ────────────────────────────────────────────
    if args.output == "csv":
        output = CsvOutput(args.output_path)
    elif args.output == "stdout":
        output = StdoutOutput()
    else:
        output = MemoryOutput(config.max_frames_buffer)

    # ── 5. Activate scenario ─────────────────────────────────────────
    if args.scenario:
        act_result = loop.activate_scenario(args.scenario)
        if act_result.get("status") == "error":
            print(f"ERROR activating scenario: {act_result['message']}", file=sys.stderr)
            return 1
        print(f"Scenario '{args.scenario}' activated — {act_result['status']}")

    # ── 6. API server mode ───────────────────────────────────────────
    if args.api_server:
        print(f"Starting API server on {config.api_host}:{config.api_port}...")
        from .api_server import Vf2ApiServer

        server = Vf2ApiServer(loop, output, config)
        try:
            server.run()
        except KeyboardInterrupt:
            print("\nShutting down.")
        finally:
            output.close()
        return 0

    # ── 7. Batch run mode ────────────────────────────────────────────
    steps = args.steps or 60
    print(f"Running {steps} steps...")
    frames = loop.run(steps, config.interval_s)

    for frame in frames:
        output.write(frame)
    output.close()

    print(f"Done. {steps} steps, {len(frames)} frames generated.")
    print(f"  Time: {loop.state.time_s:.0f}s")
    print(f"  Signals per frame: {loop.sig_reg.signal_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
