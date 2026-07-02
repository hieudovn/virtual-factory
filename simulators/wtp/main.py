"""Command-line entry point for the WTP Simulator.

Usage:
    python -m simulators.wtp.main --contract path/to/wtp-demo-01.contract.yaml
    python -m simulators.wtp.main --contract ... --scenario raw_water_contamination
    python -m simulators.wtp.main --contract ... --steps 3600
    python -m simulators.wtp.main --contract ... --api-only
"""

from __future__ import annotations

import argparse
import csv
import io
import logging
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

from .actuator_engine import ActuatorEngine
from .config import WtpConfig, load_config
from .contract_parser import parse_contract
from .disturbance_engine import DisturbanceEngine
from .ingest_client import IngestClient
from .models import Measurement, seeded_rng
from .opcua_gateway import WtpOpcUaGateway
from .scenario_manager import ScenarioManager
from .signal_registry import SignalRegistry
from .simulation_loop import WtpSimulationLoop

logger = logging.getLogger("wtp-sim")


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wtp-sim", description="WTP Simulator")
    parser.add_argument("--contract", required=True, help="Path to contract YAML")
    parser.add_argument("--config", default=None, help="Path to config YAML")
    parser.add_argument("--scenario", default=None, help="Override default scenario")
    parser.add_argument("--steps", type=int, default=0, help="Run N steps then exit (0=infinite)")
    parser.add_argument("--api-only", action="store_true", help="Start API only, no auto-sim")
    parser.add_argument("--csv-output", default=None, help="Optional CSV output path")
    parser.add_argument("--opcua-endpoint", default=None,
                        help="Override OPC UA endpoint (default from config)")
    parser.add_argument("--disable-opcua", action="store_true",
                        help="Disable the WTP OPC UA server for this run")
    return parser


class WtpSimulatorApp:
    """Main simulator application — orchestrates all components."""

    def __init__(self, config: WtpConfig, contract_path: str,
                 opcua_endpoint: str | None = None) -> None:
        self.config = config
        self.contract_path = contract_path
        self.running = False
        self._thread: threading.Thread | None = None

        # Parse contract
        self.contract = parse_contract(contract_path)
        logger.info("Contract parsed: %d signals defined", len(self.contract.get("signals", [])))

        # Create signal registry
        self.registry = SignalRegistry()
        logger.info("Signal registry: %d DVs, %d MVs, %d PVs, %d KPIs",
                     len(self.registry.DV_CONFIGS),
                     len(self.registry.MV_CONFIGS),
                     len(self.registry.PV_SIGNALS),
                     len(self.registry.KPI_SIGNALS))

        # Create engines
        self.disturbance_engine = DisturbanceEngine(self.registry.DV_CONFIGS)
        self.actuator_engine = ActuatorEngine(self.registry.MV_CONFIGS)
        self.simulation_loop = WtpSimulationLoop(
            registry=self.registry,
            disturbance_engine=self.disturbance_engine,
            actuator_engine=self.actuator_engine,
        )

        # Create scenario manager
        self.scenario_manager = ScenarioManager(
            default_scenario=config.default_scenario,
            transition_s=config.transition_s,
        )
        try:
            self.scenario_manager.load_all()
            logger.info("Loaded %d scenarios", len(self.scenario_manager.scenarios))
        except FileNotFoundError:
            logger.warning("No scenario files found")

        if self.config.default_scenario:
            self.scenario_manager.load_scenario_by_name(self.config.default_scenario)

        # Create ingest client
        self.ingest_client = IngestClient(
            ingest_url=config.ingest_url,
            source=config.source,
            api_key=config.plantos_api_key,
            max_retries=config.retry_max_retries,
            base_delay_s=config.retry_base_delay_s,
            max_delay_s=config.retry_max_delay_s,
            backoff_multiplier=config.retry_backoff_multiplier,
            max_buffer=config.max_frames_buffer,
        )

        # Create OPC UA gateway
        self.opcua_endpoint = opcua_endpoint or config.opcua_endpoint
        config.opcua_endpoint = self.opcua_endpoint
        self.opcua_gateway: WtpOpcUaGateway | None = None
        if config.opcua_enabled and self.opcua_endpoint:
            self.opcua_gateway = WtpOpcUaGateway(
                endpoint=self.opcua_endpoint,
                namespace_uri=config.opcua_namespace,
            )
            self.opcua_gateway.connect()
            self.opcua_gateway.publish_signals(self.simulation_loop.get_all_values())
            logger.info(
                "OPC UA gateway started on %s with %d WTP signal nodes",
                self.opcua_endpoint,
                self.opcua_gateway.node_count,
            )

    def step(self) -> list[Measurement]:
        """Run one simulation step and publish to PlantOS + OPC UA."""
        measurements = self.simulation_loop.step(self.config.interval_s)

        # Apply scenario transitions
        self.scenario_manager.step(
            self.config.interval_s,
            self.actuator_engine,
            self.disturbance_engine,
        )

        # Publish to PlantOS
        self.ingest_client.post_measurements(measurements)

        # Publish to OPC UA
        self._publish_opcua(measurements)

        return measurements

    def _publish_opcua(self, measurements: list[Measurement]) -> None:
        """Publish all measurement values via OPC UA gateway."""
        if self.opcua_gateway is None:
            return
        signals: dict[str, float | bool] = {}
        for m in measurements:
            signals[m.signal_id] = m.value
        self.opcua_gateway.publish_signals(signals)

    def run_loop(self, steps: int = 0, csv_path: str | None = None) -> None:
        """Run the main simulation loop."""
        self.running = True
        count = 0
        csv_file: Any = None
        csv_writer: Any = None

        if csv_path:
            csv_file = open(csv_path, "w", newline="")
            csv_writer = csv.writer(csv_file)

        logger.info("Simulation started (interval=%.1fs)", self.config.interval_s)

        try:
            while self.running:
                if steps > 0 and count >= steps:
                    break

                measurements = self.step()
                count += 1

                if csv_writer:
                    row = {"step": count, "time_s": self.simulation_loop.state.time_s}
                    for m in measurements:
                        row[m.signal_id] = m.value
                    if count == 1:
                        csv_writer.writerow(row.keys())
                    csv_writer.writerow(row.values())

                if count % 100 == 0:
                    logger.info("Step %d — time=%.0fs, ingested=%d",
                                count, self.simulation_loop.state.time_s,
                                self.ingest_client.total_ingested)

                time.sleep(max(self.config.interval_s - 0.05, 0.01))  # compensate for compute time

        except KeyboardInterrupt:
            logger.info("Simulation stopped by user")
        finally:
            self.running = False
            if csv_file:
                csv_file.close()
            self.ingest_client.close()
            logger.info("Simulation finished: %d steps, %d measurements ingested",
                        count, self.ingest_client.total_ingested)

    def start_background_loop(self) -> None:
        """Start the simulation loop in a background thread."""
        def _run():
            self.run_loop(steps=0)  # infinite

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.running = False
        if self.opcua_gateway is not None:
            self.opcua_gateway.disconnect()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)
    setup_logging(config.log_level)

    # Create app
    if args.disable_opcua:
        config.opcua_enabled = False

    app = WtpSimulatorApp(config, args.contract, opcua_endpoint=args.opcua_endpoint)

    # Override default scenario if specified
    if args.scenario:
        app.scenario_manager.default_scenario_id = args.scenario
        app.scenario_manager.load_scenario_by_name(args.scenario)

    # Create API server
    from .api_server import WtpApiServer
    api_server = WtpApiServer(
        sim_loop=app.simulation_loop,
        ingest_client=app.ingest_client,
        scenario_manager=app.scenario_manager,
        actuator_engine=app.actuator_engine,
        disturbance_engine=app.disturbance_engine,
        opcua_gateway=app.opcua_gateway,
        config=config,
    )

    # Start API server in background
    api_server.start()
    logger.info("API server started on %s:%d", config.api_host, config.api_port)

    # Handle signals
    stop_event = threading.Event()

    def handle_signal(signum, frame):
        logger.info("Shutdown signal received")
        stop_event.set()
        app.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    if not args.api_only:
        if args.steps > 0:
            # Run for N steps then exit
            app.run_loop(steps=args.steps, csv_path=args.csv_output)
        else:
            # Run indefinitely
            app.start_background_loop()
            logger.info("Simulation running in background. Press Ctrl+C to stop.")
            try:
                stop_event.wait()
            except KeyboardInterrupt:
                app.stop()
    else:
        logger.info("API-only mode. Waiting for requests...")
        try:
            stop_event.wait()
        except KeyboardInterrupt:
            pass

    app.ingest_client.close()
    logger.info("WTP Simulator shutdown complete.")


if __name__ == "__main__":
    main()
