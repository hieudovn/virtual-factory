"""NL-to-YAML plant config generator with pluggable LLM backends.

Usage:
    from virtual_factory.ai.generator import generate_config

    # Using built-in template (no API key needed):
    config = generate_config("2 tanks, 1 pump, PID level control")
    config.model_dump() -> YAML string

    # With OpenAI:
    config = generate_config("...", backend="openai", api_key="sk-...")
"""

import json
from pathlib import Path
from typing import Any

import yaml

from virtual_factory.ai.prompts import build_prompt


def generate_config(
    description: str,
    backend: str = "template",
    api_key: str | None = None,
    model: str = "gpt-4",
    output_path: str | Path | None = None,
) -> str:
    """Generate a YAML plant configuration from a natural language description.

    Parameters
    ----------
    description : str
        Natural language description of the plant.
    backend : str
        Generation backend: ``"template"`` (built-in, no key), ``"openai"``,
        ``"anthropic"``, or ``"print-prompt"`` (debug).
    api_key : str | None
        API key for external LLM backends.
    model : str
        Model name for external backends (default ``"gpt-4"``).
    output_path : str | Path | None
        If provided, save the generated YAML to this file.

    Returns
    -------
    str
        Generated YAML string.
    """
    if backend == "template":
        yaml_str = _template_generator(description)
    elif backend == "openai":
        yaml_str = _openai_generator(description, api_key, model)
    elif backend == "anthropic":
        yaml_str = _anthropic_generator(description, api_key, model)
    elif backend == "print-prompt":
        sys_p, usr_p = build_prompt(description)
        yaml_str = f"# System prompt:\n{sys_p}\n\n# User prompt:\n{usr_p}"
    else:
        raise ValueError(f"Unknown backend: {backend}")

    if output_path:
        path = Path(output_path)
        path.write_text(yaml_str, encoding="utf-8")

    return yaml_str


def _template_generator(description: str) -> str:
    """Built-in template generator — produces a config from keywords.

    This is a fallback when no LLM API key is available. It parses
    keywords from the description and builds a minimal config.
    """
    desc_lower = description.lower()

    # Detect number of tanks
    tank_count = 2  # default: source + destination
    for word in ["2 tank", "two tank", "pair of tank"]:
        if word in desc_lower:
            tank_count = 2
    if "1 tank" in desc_lower or "one tank" in desc_lower or "single tank" in desc_lower:
        tank_count = 1
    if tank_count == 1:
        tank_count = 2  # Need at least 2 for a flow path

    # Detect equipment types
    has_pump = any(w in desc_lower for w in ["pump", "centrifugal"])
    has_valve = any(w in desc_lower for w in ["valve", "control valve", "cv"])
    has_controller = any(w in desc_lower for w in ["pid", "controller", "control", "level control"])
    has_sensor = any(w in desc_lower for w in ["sensor", "transmitter", "measure", "level tx"])
    has_heat_exchanger = any(w in desc_lower for w in ["heat", "heat exchanger", "hex", "cooling", "heating"])
    has_fan = any(w in desc_lower for w in ["fan", "blower", "ventilation"])
    has_compressor = any(w in desc_lower for w in ["compressor", "gas boost"])
    has_separator = any(w in desc_lower for w in ["separator", "gas-liquid", "knockout"])

    # Build config
    lines = []
    lines.append("plant:")
    lines.append("  id: ai_generated_plant")
    lines.append(f"  name: \"{description[:50]}\"")
    lines.append("  type: continuous_process")
    lines.append("")
    lines.append("medium:")
    lines.append("  id: water")
    lines.append("  density_kg_m3: 997.0")
    lines.append("  viscosity_pa_s: 0.00089")
    lines.append("  specific_heat_j_kg_k: 4182.0")
    lines.append("")
    lines.append("equipment:")

    # Tanks
    src_capacity = 10.0
    if "small" in desc_lower:
        src_capacity = 5.0
    elif "large" in desc_lower:
        src_capacity = 20.0

    lines.append(f"  - id: T101")
    lines.append(f"    model_type: tank_v1")
    lines.append(f"    display_name: Source Tank")
    lines.append(f"    parameters:")
    lines.append(f"      capacity_m3: {src_capacity}")
    lines.append(f"      initial_level_m: 4.0")
    lines.append(f"      max_level_m: 5.0")

    idx = 0
    if has_pump:
        idx += 1
        lines.append(f"  - id: P101")
        lines.append(f"    model_type: centrifugal_pump_v1")
        lines.append(f"    display_name: Centrifugal Pump")
        lines.append(f"    parameters:")
        lines.append(f"      rated_flow_m3_s: 0.012")
        lines.append(f"      rated_head_m: 18.0")

    if has_valve or has_controller:
        idx += 1
        lines.append(f"  - id: V101")
        lines.append(f"    model_type: control_valve_v1")
        lines.append(f"    display_name: Control Valve")
        lines.append(f"    parameters:")
        lines.append(f"      cv: 50.0")
        lines.append(f"      fail_position: closed")
        lines.append(f"      initial_opening_percent: 0.0")

    if has_heat_exchanger:
        idx += 1
        lines.append(f"  - id: HEX01")
        lines.append(f"    model_type: heat_exchanger_v1")
        lines.append(f"    display_name: Heat Exchanger")
        lines.append(f"    parameters:")
        lines.append(f"      area_m2: 5.0")
        lines.append(f"      u_w_m2k: 500.0")

    dst_capacity = 8.0
    if "large" in desc_lower:
        dst_capacity = 15.0

    lines.append(f"  - id: T102")
    lines.append(f"    model_type: tank_v1")
    lines.append(f"    display_name: Destination Tank")
    lines.append(f"    parameters:")
    lines.append(f"      capacity_m3: {dst_capacity}")
    lines.append(f"      initial_level_m: 1.0")
    lines.append(f"      max_level_m: 5.0")
    lines.append(f"      outlet_demand_m3_s: 0.006")

    if has_fan:
        lines.append(f"  - id: F101")
        lines.append(f"    model_type: fan_v1")
        lines.append(f"    display_name: Fan / Blower")
        lines.append(f"    parameters:")
        lines.append(f"      rated_pressure_rise_pa: 500.0")
        lines.append(f"      rated_flow_m3_s: 1.0")

    if has_compressor:
        lines.append(f"  - id: C101")
        lines.append(f"    model_type: compressor_v1")
        lines.append(f"    display_name: Gas Compressor")
        lines.append(f"    parameters:")
        lines.append(f"      rated_power_kw: 50.0")
        lines.append(f"      rated_flow_m3_s: 0.5")
        lines.append(f"      rated_pressure_ratio: 2.0")

    if has_separator:
        lines.append(f"  - id: S101")
        lines.append(f"    model_type: separator_v1")
        lines.append(f"    display_name: Gas-Liquid Separator")
        lines.append(f"    parameters:")
        lines.append(f"      diameter_m: 1.0")
        lines.append(f"      height_m: 3.0")
        lines.append(f"      initial_level_m: 0.5")

    # Connections
    lines.append("")
    lines.append("connections:")
    conns = []
    equip_ids = ["T101"]
    if has_pump:
        equip_ids.append("P101")
    if has_valve or has_controller:
        equip_ids.append("V101")
    if has_heat_exchanger:
        equip_ids.append("HEX01")
    equip_ids.append("T102")

    for i in range(len(equip_ids) - 1):
        conns.append((equip_ids[i], equip_ids[i+1]))

    for i, (src, dst) in enumerate(conns, 1):
        lines.append(f"  - id: C{i:03d}")
        lines.append(f"    type: physical")
        lines.append(f"    from: {src}.outlet")
        lines.append(f"    to: {dst}.inlet")
        lines.append(f"    medium: water")

    # Sensors
    lines.append("")
    lines.append("sensors:")
    if has_sensor or has_controller:
        lines.append(f"  - id: LT102")
        lines.append(f"    model_type: level_transmitter_v1")
        lines.append(f"    display_name: T102 Level Transmitter")
        lines.append(f"    measures: T102.level_true")
        lines.append(f"    output_signal: LT102_LEVEL")
        lines.append(f"    parameters:")
        lines.append(f"      sample_time_s: 1.0")
        lines.append(f"      resolution: 0.01")
        lines.append(f"      noise_std: 0.0")
        lines.append(f"      delay_s: 0.0")
        lines.append(f"      quality: GOOD")
        lines.append(f"  - id: FT101")
        lines.append(f"    model_type: flow_transmitter_v1")
        lines.append(f"    display_name: V101 Outlet Flow")
        lines.append(f"    measures: V101.outlet.flow_true")
        lines.append(f"    output_signal: FT101_FLOW")
        lines.append(f"    parameters:")
        lines.append(f"      sample_time_s: 1.0")
        lines.append(f"      resolution: 0.0001")
        lines.append(f"      quality: GOOD")

    # Controllers
    if has_controller:
        lines.append("")
        lines.append("controllers:")
        kp = 1.0
        ki = 0.1
        if any(w in desc_lower for w in ["aggressive", "fast"]):
            kp = 2.0; ki = 0.2
        elif any(w in desc_lower for w in ["slow", "gentle", "smooth"]):
            kp = 0.5; ki = 0.05
        lines.append(f"  - id: LIC102")
        lines.append(f"    model_type: pid_controller_v1")
        lines.append(f"    display_name: T102 Level Controller")
        lines.append(f"    pv_signal: LT102_LEVEL")
        lines.append(f"    setpoint: 2.5")
        lines.append(f"    output_signal: LIC102_OUT")
        lines.append(f"    scan_time_s: 0.5")
        lines.append(f"    parameters:")
        lines.append(f"      kp: {kp}")
        lines.append(f"      ki: {ki}")
        lines.append(f"      kd: 0.0")

    # Actuators
    if has_valve or has_controller:
        lines.append("")
        lines.append("actuators:")
        lines.append(f"  - id: VA101")
        lines.append(f"    model_type: valve_actuator_v1")
        lines.append(f"    display_name: V101 Valve Actuator")
        lines.append(f"    command_signal: LIC102_OUT")
        lines.append(f"    feedback_signal: V101_OPENING_FEEDBACK")
        lines.append(f"    actuates: V101.opening_actual")
        lines.append(f"    parameters:")
        lines.append(f"      max_rate: 20.0")

    return "\n".join(lines)


def _openai_generator(description: str, api_key: str | None, model: str) -> str:
    """Generate config using OpenAI API."""
    if not api_key:
        return _template_generator(description)

    try:
        import openai
    except ImportError:
        raise ImportError("openai package required. Install: pip install openai")

    sys_prompt, usr_prompt = build_prompt(description)
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": usr_prompt},
        ],
        temperature=0.3,
    )
    content = response.choices[0].message.content
    if content is None:
        return _template_generator(description)
    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0]
    return content.strip()


def _anthropic_generator(description: str, api_key: str | None, model: str) -> str:
    """Generate config using Anthropic API."""
    if not api_key:
        return _template_generator(description)
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package required. Install: pip install anthropic")

    sys_prompt, usr_prompt = build_prompt(description)
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        system=sys_prompt,
        max_tokens=2000,
        messages=[{"role": "user", "content": usr_prompt}],
    )
    content = response.content[0].text if response.content else ""
    return content.strip()
