"""Command-line entry point for Virtual Factory."""

import argparse
from pathlib import Path
from typing import Sequence

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine
from virtual_factory.core.state_persistence import get_last_config, set_last_config
from virtual_factory.protocols.mqtt_gateway import MqttGateway
from virtual_factory.protocols.opcua_gateway import OpcUaGateway
from virtual_factory.protocols.sparkplug_gateway import SparkplugBGateway
from virtual_factory.scenarios.scenario_loader import load_scenario
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
ALARM_DISPLAY_SIGNALS = [
    "T102_LOW_LEVEL_ALARM",
    "T102_HIGH_LEVEL_ALARM",
    "P101_NO_FLOW_ALARM",
    "V101_POSITION_DEVIATION_ALARM",
    "LT102_BAD_QUALITY_ALARM",
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
    scenario_path: str | Path | None = None,
    mqtt_host: str | None = None,
    mqtt_port: int = 1883,
    mqtt_topic_prefix: str = "virtual-factory/demo/continuous_mvp_01",
    mqtt_client_id: str | None = None,
    mqtt_connect_retries: int = 20,
    mqtt_connect_delay: float = 1.0,
    opcua_endpoint: str | None = None,
    sparkplug: bool = False,
    quiet: bool = False,
    debug_truth: bool = False,
    show_alarms: bool = False,
) -> list[list[SignalValue]]:
    """Run a configured simulation and optionally export publishable telemetry."""
    config = load_plant_config(config_path)
    scenario = load_scenario(scenario_path) if scenario_path else None
    engine = SimulationEngine(config, dt_s=dt_s, scenario=scenario)
    mqtt_gateway = (
        MqttGateway(
            host=mqtt_host,
            port=mqtt_port,
            topic_prefix=mqtt_topic_prefix,
            client_id=mqtt_client_id,
        )
        if mqtt_host
        else None
    )
    opcua_gateway = (
        OpcUaGateway(endpoint=opcua_endpoint) if opcua_endpoint else None
    )
    spb_gateway = (
        SparkplugBGateway(mqtt=mqtt_gateway, edge_node_id=config.plant.id)
        if sparkplug and mqtt_gateway
        else None
    )
    frames: list[list[SignalValue]] = []

    if not quiet:
        print(_format_header(debug_truth, show_alarms))

    if mqtt_gateway:
        mqtt_gateway.connect(retries=mqtt_connect_retries, delay_s=mqtt_connect_delay)
    if opcua_gateway:
        opcua_gateway.connect()
    try:
        for _ in range(steps):
            snapshot = engine.step()
            frame = list(snapshot["telemetry_latest"])
            frames.append(frame)
            records = frame_to_records(frame)
            if csv_output:
                append_csv(csv_output, records)
            if jsonl_output:
                append_jsonl(jsonl_output, records)
            if mqtt_gateway:
                mqtt_gateway.publish_frame(frame)
            if opcua_gateway:
                opcua_gateway.publish_frame(frame)
            if spb_gateway:
                spb_gateway.publish_frame(frame)
            if not quiet:
                print(_format_row(frame, snapshot, debug_truth, show_alarms))
    finally:
        if spb_gateway:
            spb_gateway.send_death()
        if mqtt_gateway:
            mqtt_gateway.disconnect()
        if opcua_gateway:
            opcua_gateway.disconnect()

    return frames


def serve_api(
    config_path: str | Path | None = None,
    scenario_path: str | Path | None = None,
    dt_s: float = 1.0,
    host: str = "0.0.0.0",
    port: int = 8000,
    auto_start: bool = False,
    mqtt_host: str | None = None,
    mqtt_port: int = 1883,
    mqtt_topic_prefix: str = "virtual-factory/demo/continuous_mvp_01",
    mqtt_client_id: str | None = None,
    mqtt_connect_retries: int = 20,
    mqtt_connect_delay: float = 1.0,
    opcua_endpoint: str | None = None,
) -> None:
    """Run the optional FastAPI monitoring service.

    If config_path is None, the last-used config from ~/.virtual_factory/state.json
    is used. The chosen config is persisted for next time.
    """
    if config_path is None:
        config_path = get_last_config()
    config_path = str(config_path)
    set_last_config(config_path)

    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("API support requires installing the api extra: pip install -e .[api]") from exc

    from virtual_factory.ui.api import create_app

    app = create_app(
        config_path=config_path,
        scenario_path=scenario_path,
        dt_s=dt_s,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_topic_prefix=mqtt_topic_prefix,
        mqtt_client_id=mqtt_client_id,
        mqtt_connect_retries=mqtt_connect_retries,
        mqtt_connect_delay=mqtt_connect_delay,
        opcua_endpoint=opcua_endpoint,
        auto_start=auto_start,
    )
    uvicorn.run(app, host=host, port=port)


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
    run_parser.add_argument("--scenario", default=None, help="Optional scenario YAML path.")
    run_parser.add_argument("--mqtt-host", default=None, help="Optional MQTT broker host.")
    run_parser.add_argument("--mqtt-port", type=int, default=1883, help="Optional MQTT broker port.")
    run_parser.add_argument(
        "--mqtt-topic-prefix",
        default="virtual-factory/demo/continuous_mvp_01",
        help="MQTT topic prefix for signal topics.",
    )
    run_parser.add_argument("--mqtt-client-id", default=None, help="Optional MQTT client id.")
    run_parser.add_argument(
        "--mqtt-connect-retries",
        type=int,
        default=20,
        help="MQTT connection retry attempts.",
    )
    run_parser.add_argument(
        "--mqtt-connect-delay",
        type=float,
        default=1.0,
        help="Seconds between MQTT connection retry attempts.",
    )
    run_parser.add_argument("--show-alarms", action="store_true", help="Show alarm/event columns.")
    run_parser.add_argument("--debug-truth", action="store_true", help="Print selected truth values.")
    run_parser.add_argument("--quiet", action="store_true", help="Suppress console rows.")
    run_parser.add_argument("--opcua-endpoint", default=None, help="Optional OPC UA server endpoint (e.g. opc.tcp://0.0.0.0:4840).")
    run_parser.add_argument("--sparkplug", action="store_true", help="Use Sparkplug B topic format for MQTT (requires --mqtt-host).")

    serve_parser = subparsers.add_parser("serve", help="Run the monitoring API service.")
    serve_parser.add_argument("--config", default=None, help="Plant configuration YAML path (default: last used, or continuous_mvp_01).")
    serve_parser.add_argument("--scenario", default=None, help="Optional scenario YAML path.")
    serve_parser.add_argument("--dt", type=float, default=1.0, help="Step duration in seconds.")
    serve_parser.add_argument("--host", default="0.0.0.0", help="API bind host.")
    serve_parser.add_argument("--port", type=int, default=8000, help="API bind port.")
    serve_parser.add_argument("--auto-start", action="store_true", help="Start the simulation loop on API startup.")
    serve_parser.add_argument("--mqtt-host", default=None, help="Optional MQTT broker host for API runtime publishing.")
    serve_parser.add_argument("--mqtt-port", type=int, default=1883, help="Optional MQTT broker port.")
    serve_parser.add_argument(
        "--mqtt-topic-prefix",
        default="virtual-factory/demo/continuous_mvp_01",
        help="MQTT topic prefix for signal topics.",
    )
    serve_parser.add_argument("--mqtt-client-id", default=None, help="Optional MQTT client id.")
    serve_parser.add_argument(
        "--mqtt-connect-retries",
        type=int,
        default=20,
        help="MQTT connection retry attempts.",
    )
    serve_parser.add_argument(
        "--mqtt-connect-delay",
        type=float,
        default=1.0,
        help="Seconds between MQTT connection retry attempts.",
    )
    serve_parser.add_argument("--opcua-endpoint", default=None, help="Optional OPC UA server endpoint.")

    validate_parser = subparsers.add_parser("validate", help="Validate a plant configuration YAML.")
    validate_parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Plant configuration YAML path.")
    validate_parser.add_argument("--report", action="store_true", help="Print structured JSON report.")

    gen_parser = subparsers.add_parser("generate", help="Generate plant config from natural language.")
    gen_parser.add_argument("--prompt", required=True, help="Natural language description.")
    gen_parser.add_argument("--backend", default="template", choices=["template","openai","anthropic","print-prompt"])
    gen_parser.add_argument("--api-key", default=None, help="API key for LLM backend.")
    gen_parser.add_argument("--model", default="gpt-4", help="Model name.")
    gen_parser.add_argument("--output", default=None, help="Save YAML to file.")
    gen_parser.add_argument("--validate", action="store_true", help="Validate generated config.")

    parse_parser = subparsers.add_parser("parse", help="Parse P&ID shorthand into config.")
    parse_parser.add_argument("--text", required=True, help="P&ID text (e.g. 'T101->P101->V101->T102').")
    parse_parser.add_argument("--output", default=None, help="Save config to file.")
    parse_parser.add_argument("--validate", action="store_true", help="Validate parsed config.")

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
            scenario_path=args.scenario,
            mqtt_host=args.mqtt_host,
            mqtt_port=args.mqtt_port,
            mqtt_topic_prefix=args.mqtt_topic_prefix,
            mqtt_client_id=args.mqtt_client_id,
            mqtt_connect_retries=args.mqtt_connect_retries,
            mqtt_connect_delay=args.mqtt_connect_delay,
            quiet=args.quiet,
            debug_truth=args.debug_truth,
            show_alarms=args.show_alarms,
            opcua_endpoint=args.opcua_endpoint,
            sparkplug=args.sparkplug,
        )
        return

    if args.command == "serve":
        serve_api(
            config_path=args.config,
            scenario_path=args.scenario,
            dt_s=args.dt,
            host=args.host,
            port=args.port,
            auto_start=args.auto_start,
            mqtt_host=args.mqtt_host,
            mqtt_port=args.mqtt_port,
            mqtt_topic_prefix=args.mqtt_topic_prefix,
            mqtt_client_id=args.mqtt_client_id,
            mqtt_connect_retries=args.mqtt_connect_retries,
            mqtt_connect_delay=args.mqtt_connect_delay,
            opcua_endpoint=args.opcua_endpoint,
        )
        return

    if args.command == "validate":
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: config file not found: {config_path}")
            return
        config = load_plant_config(config_path)
        from virtual_factory.core.validators import validate_with_report
        report = validate_with_report(config)
        if args.report:
            import json
            print(json.dumps(report, indent=2, default=str))
        else:
            print(f"Config: {config.plant.id} ({config.plant.name})")
            print(f"Valid:  {'✅ YES' if report['valid'] else '❌ NO'}")
            if report["errors"]:
                for e in report["errors"]:
                    print(f"  Error:   {e}")
            if report["warnings"]:
                for w in report["warnings"]:
                    print(f"  Warning: {w}")
            if report["graph_checks"]:
                gc = report["graph_checks"]
                print(f"  Equipment: {gc.get('equipment_connected', '?')}/{gc.get('equipment_total', '?')} connected")
            if report["policy_checks"]:
                pc = report["policy_checks"]
                print(f"  Signals:  {pc.get('signals_publishable', '?')}/{pc.get('signals_total', '?')} publishable")
        return

    if args.command == "generate":
        from virtual_factory.ai.generator import generate_config
        print(f"Generating config for: \"{args.prompt}\" (backend: {args.backend})")
        yaml_str = generate_config(
            description=args.prompt,
            backend=args.backend,
            api_key=args.api_key,
            model=args.model,
            output_path=args.output,
        )
        if args.output:
            print(f"Saved to: {args.output}")
        print("\n--- Generated YAML ---")
        print(yaml_str)
        if args.validate and args.output:
            try:
                config = load_plant_config(args.output)
                from virtual_factory.core.validators import validate_with_report
                report = validate_with_report(config)
                print(f"\nValidation: {'✅ PASS' if report['valid'] else '❌ FAIL'}")
                if report['errors']:
                    for e in report['errors']:
                        print(f"  Error: {e}")
            except Exception as ex:
                print(f"  Validation error: {ex}")
        return

    if args.command == "parse":
        from virtual_factory.ai.pid_parser import parse_pid_shorthand, parse_and_save
        print(f"Parsing P&ID shorthand...")
        if args.output:
            path = parse_and_save(args.text, args.output)
            print(f"Saved to: {path}")
            if args.validate:
                from virtual_factory.core.validators import validate_with_report
                config = load_plant_config(path)
                report = validate_with_report(config)
                print(f"Validation: {'✅ PASS' if report['valid'] else '❌ FAIL'}")
        else:
            config = parse_pid_shorthand(args.text, plant_name="Parsed Plant")
            import yaml
            yaml_str = yaml.dump(config.model_dump(mode="json"), default_flow_style=False, allow_unicode=True)
            print(yaml_str)
        return

    parser.print_help()


def _format_header(debug_truth: bool, show_alarms: bool) -> str:
    columns = ["time_s", *DISPLAY_SIGNALS]
    if show_alarms:
        columns.extend(ALARM_DISPLAY_SIGNALS)
    if debug_truth:
        columns.append("truth.T102.level_true")
    return " | ".join(columns)


def _format_row(
    frame: list[SignalValue],
    snapshot: dict[str, object],
    debug_truth: bool,
    show_alarms: bool,
) -> str:
    timestamp = frame[0].timestamp_s if frame else 0.0
    values = [_format_value(timestamp)]
    values.extend(_format_value(get_frame_value(frame, signal_name, "")) for signal_name in DISPLAY_SIGNALS)
    if show_alarms:
        values.extend(_format_value(get_frame_value(frame, signal_name, "")) for signal_name in ALARM_DISPLAY_SIGNALS)
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
