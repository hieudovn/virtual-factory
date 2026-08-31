"""M6-INT-01-C01 evidence generator.

Reproducible evidence for the three corrections:
- A: reset/run generation stability
- B: per-gateway delivery retry
- C: authoritative AP11 RELEASE occurrence time

Writes reset-run-identity.md, gateway-retry.md, release-time.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent / "src"))

from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
    WipLifecycle,
)
from virtual_factory.assembly.observation_bridge import (
    EVENT_AP11_RELEASE,
    build_assy_observation_pipeline,
)
from virtual_factory.assembly.station_contracts import CompletionMode
from virtual_factory.integration.gateways.memory import InMemoryObsGateway
import types

OUT = Path(__file__).resolve().parent
CHILD = "MTR-0001"


def make_config() -> AssyLineConfig:
    c = AssyLineConfig()
    c.conveyor.nominal_line_dwell_time_s = 10.0
    c.conveyor.index_movement_duration_s = 0.0
    for k in c.station_durations:
        c.station_durations[k] = 5.0
    return c


def setup_line(cfg: AssyLineConfig) -> AssyLineRuntime:
    line = AssyLineRuntime(config=cfg)
    line.global_run_mode = CompletionMode.AUTO
    line.produce_sso2_wip()
    line.produce_rso2_wip()
    line.introduce_to_assy("SSO2-0001", "PAL-001")
    return line


def ctx_for(line, sub_line_id="ASSY-SL01", variant="hydraulic"):
    identity = types.SimpleNamespace(
        sub_line_id=sub_line_id, variant=variant, production_line_id="ASSY")
    ctx = types.SimpleNamespace(runtime=line, identity=identity)
    return types.SimpleNamespace(contexts={sub_line_id: ctx})


def drive(line: AssyLineRuntime, max_steps=200) -> AssyLineRuntime:
    for _ in range(max_steps):
        line.execute_dwell()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()
        ws = line.get_wip(CHILD)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            break
    return line


def reset_identity_evidence() -> str:
    cfg = make_config()
    cfg.conveyor.nominal_line_dwell_time_s = 100.0
    line = setup_line(cfg)
    bridge = build_assy_observation_pipeline().bridge
    comp = ctx_for(line)

    def advance(n):
        for _ in range(n):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

    advance(60)
    bridge.poll(comp)
    end_t = line.simulation_time_s
    rows = [f"run to t={end_t:.0f}s → poll → run_id={bridge.run_id_for('ASSY-SL01')}"]

    line.reset()
    bridge.poll(comp)
    rows.append(f"reset (t=0) → poll → run_id={bridge.run_id_for('ASSY-SL01')}")

    for i in range(5):
        advance(1)
        bridge.poll(comp)
        rows.append(
            f"step{i+1} (t={line.simulation_time_s:.0f}s) → poll → "
            f"run_id={bridge.run_id_for('ASSY-SL01')}")

    line.reset()
    bridge.poll(comp)
    rows.append(f"second reset → poll → run_id={bridge.run_id_for('ASSY-SL01')}")

    expected = ["ASSY-SL01:R1"] + ["ASSY-SL01:R2"] * 6 + ["ASSY-SL01:R3"]
    actual = [r.rsplit("=", 1)[1] for r in rows]
    assert actual == expected, (actual, expected)
    return "\n".join(rows)


def gateway_retry_evidence() -> str:
    ga = InMemoryObsGateway(gateway_id="A")
    gb = InMemoryObsGateway(gateway_id="B")
    bridge = build_assy_observation_pipeline(gateways=[ga, gb]).bridge
    line = setup_line(make_config())
    drive(line)
    comp = ctx_for(line)

    rows = []
    gb.set_fail_next(999)
    r1 = bridge.poll(comp)
    a_delivered = sum(1 for r in r1 if r.gateway_id == "A" and r.status.value == "delivered")
    b_failed = sum(1 for r in r1 if r.gateway_id == "B" and r.status.value == "failed")
    rows.append(f"poll1: gateway A = DELIVERED ×{a_delivered}, "
                f"gateway B = FAILED ×{b_failed}")

    gb.set_fail_next(0)
    r2 = bridge.poll(comp)
    a_retry = sum(1 for r in r2 if r.gateway_id == "A")
    b_delivered = sum(1 for r in r2 if r.gateway_id == "B" and r.status.value == "delivered")
    rows.append(f"poll2: gateway A = no resend ({a_retry} attempts), "
                f"gateway B = DELIVERED ×{b_delivered}")
    rows.append(f"        gateway A messages = {len(ga.messages)} (unchanged), "
                f"gateway B messages = {len(gb.messages)} (caught up)")

    r3 = bridge.poll(comp)
    rows.append(f"poll3: {len(r3)} new deliveries")

    assert len(r3) == 0
    assert a_retry == 0
    return "\n".join(rows)


def release_time_evidence() -> str:
    bridge = build_assy_observation_pipeline().bridge
    line = setup_line(make_config())
    drive(line)
    ws = line.get_wip(CHILD)
    T = ws.released_at_sim_s

    for _ in range(30):
        line.execute_dwell()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()
    late = line.simulation_time_s

    comp = ctx_for(line)
    bridge.poll(comp)
    rel = [t for t in bridge.outbound_trace
           if t["payload"].get("event_type") == EVENT_AP11_RELEASE]
    emitted = rel[0]["payload"]["release_time_s"]

    rows = [
        f"actual release time T = {T:.0f}s",
        f"late poll time (T+n) = {late:.0f}s",
        f"emitted release_time_s = {emitted:.0f}s",
    ]
    assert emitted == T
    assert late > T
    return "\n".join(rows)


def main() -> None:
    (OUT / "reset-run-identity.md").write_text(
        "# M6-INT-01-C01 — Reset / run identity\n\n```text\n"
        + reset_identity_evidence() + "\n```\n",
        encoding="utf-8")
    (OUT / "gateway-retry.md").write_text(
        "# M6-INT-01-C01 — Per-gateway delivery retry\n\n```text\n"
        + gateway_retry_evidence() + "\n```\n",
        encoding="utf-8")
    (OUT / "release-time.md").write_text(
        "# M6-INT-01-C01 — Authoritative RELEASE occurrence time\n\n```text\n"
        + release_time_evidence() + "\n```\n",
        encoding="utf-8")
    print("evidence written")


if __name__ == "__main__":
    main()
