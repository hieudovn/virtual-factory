"""VF-CONTRACT-FINALITY-01 — terminal quality evidence enrichment tests.

Additive producer-contract tests: the authoritative FAILED_FINAL runtime
outcome is exposed on the final attempt's `mes.quality_result` as
`is_terminal` / `terminal_state` (additive; nothing renamed/removed).

Covers the gate §12 requirements 1-16.
"""

from __future__ import annotations

from pathlib import Path

from virtual_factory.assembly.demo_composition import (
    AssyDemoComposition,
    DemoScenario,
)
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
    WipLifecycle,
)
from virtual_factory.assembly.observation_bridge import (
    EVENT_QUALITY_RESULT,
    build_assy_observation_pipeline,
)
from virtual_factory.assembly.operation_execution import OperationState
from virtual_factory.assembly.station_contracts import (
    CompletionMode,
    StationCommand,
)

REPO = Path(__file__).resolve().parent.parent
TIPA_YAML = str(REPO / "configs" / "plants" / "tipa_assy_demo.yaml")
CHILD = "MTR-0001"


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def serialized(message) -> dict:
    return {
        "message_key": message.key,
        "message_type": message.message_type,
        "schema_name": message.schema_name,
        "schema_version": message.schema_version,
        "headers": dict(message.headers),
        "payload": dict(message.payload),
    }


def drive_projected(scenario: str, sl_id: str, max_steps: int = 400) -> list[dict]:
    """Drive a composition scenario context and return serialized messages."""
    comp = AssyDemoComposition(config_path=TIPA_YAML, scenario=scenario)
    comp.initialize()
    bridge = build_assy_observation_pipeline().bridge
    ctx = comp.get_context(sl_id)
    for _ in range(max_steps):
        ctx.step_context()
        ws = ctx.runtime.get_wip(CHILD)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            break
    bridge.poll(comp)
    return [serialized(m) for m in bridge.projected_messages]


def quality_msgs(msgs: list[dict], station: str) -> list[dict]:
    return [m for m in msgs
            if m["message_type"] == "mes.quality_result"
            and m["payload"].get("station_id") == station]


def terminal_msgs(msgs: list[dict]) -> list[dict]:
    return [m for m in msgs
            if m["message_type"] == "mes.quality_result"
            and m["payload"].get("is_terminal") is True]


def release_msgs(msgs: list[dict]) -> list[dict]:
    return [m for m in msgs if m["message_type"] == "mes.release"]


def make_config(ap06: str = "PASS", ap08: str = "PASS") -> AssyLineConfig:
    c = AssyLineConfig()
    c.conveyor.nominal_line_dwell_time_s = 10.0
    c.conveyor.index_movement_duration_s = 0.0
    for k in c.station_durations:
        c.station_durations[k] = 5.0
    c.quality.ap06.scenario = ap06
    c.quality.ap08.scenario = ap08
    return c


def setup_line(cfg: AssyLineConfig) -> AssyLineRuntime:
    line = AssyLineRuntime(config=cfg)
    line.global_run_mode = CompletionMode.AUTO
    line.produce_sso2_wip()
    line.produce_rso2_wip()
    line.introduce_to_assy("SSO2-0001", "PAL-001")
    return line


def resolve_awaiting(line: AssyLineRuntime) -> None:
    for op in list(line.operation_registry.active_operations()):
        if op.completion_mode != CompletionMode.MANUAL:
            continue
        st, wip = op.station_id, op.wip_id
        if op.state == OperationState.AWAITING_DECISION:
            decision = op.proposed_quality_result or "PASS"
            line.submit_operation_command(
                st, wip, StationCommand.CONFIRM, payload={"decision": decision})
        elif op.state == OperationState.AWAITING_COMPLETION:
            contract = line.station_contracts[st]
            cmd = contract.required_action or contract.normal_action or StationCommand.DONE
            payload = None
            if (contract.checklist_required_for_action is not None
                    and contract.checklist_required_for_action == cmd):
                payload = {"checklist": [
                    {"item_id": i, "completed": True}
                    for i in contract.checklist_items
                ]}
            line.submit_operation_command(st, wip, cmd, payload)


def drive_runtime(line: AssyLineRuntime, mode: CompletionMode,
                  max_steps: int = 200) -> None:
    """Drive one runtime in the given mode until first child RELEASED."""
    line.global_run_mode = mode
    for _ in range(max_steps):
        line.execute_dwell()
        if mode == CompletionMode.MANUAL:
            resolve_awaiting(line)
            line.conveyor.check_ready()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()
        ws = line.get_wip(CHILD)
        if ws and ws.lifecycle == WipLifecycle.RELEASED:
            return


def bridge_for_runtime(line: AssyLineRuntime, sub_line_id: str = "ASSY-SL03"):
    import types
    bridge = build_assy_observation_pipeline().bridge
    identity = types.SimpleNamespace(
        sub_line_id=sub_line_id, variant="hydraulic", production_line_id="ASSY")
    ctx = types.SimpleNamespace(runtime=line, identity=identity)
    comp = types.SimpleNamespace(contexts={sub_line_id: ctx})
    return bridge, comp


def ap06_always_fail_config() -> AssyLineConfig:
    c = make_config(ap06="ALWAYS_FAIL")
    c.quality.ap06.max_attempts = 2
    return c


# ═══════════════════════════════════════════════════════════
# 1-5. FAILED_FINAL authoritative finality
# ═══════════════════════════════════════════════════════════

class TestFailedFinalAuthoritative:
    def test_failed_final_emits_terminal_finality(self):
        """(1) FAILED_FINAL scenario: the final attempt carries terminal truth."""
        msgs = drive_projected("FAILED_FINAL", "ASSY-SL03")
        term = terminal_msgs(msgs)
        assert len(term) == 1
        p = term[0]["payload"]
        assert p["is_terminal"] is True
        assert p["terminal_state"] == "failed_final"
        assert p["disposition"] == "FAIL"

    def test_terminal_evidence_correct_wip(self):
        """(2) Terminal evidence corresponds to the failing WIP."""
        msgs = drive_projected("FAILED_FINAL", "ASSY-SL03")
        term = terminal_msgs(msgs)[0]["payload"]
        assert term["wip_id"] == CHILD
        assert term["subject_id"] == CHILD

    def test_correct_station_ap06(self):
        """(3) Correct station = AP06 for the current TIPA scenario."""
        msgs = drive_projected("FAILED_FINAL", "ASSY-SL03")
        term = terminal_msgs(msgs)[0]["payload"]
        assert term["station_id"] == "AP06"
        assert term["check_type"] == "TEST"

    def test_correct_attempt_final(self):
        """(4) Correct attempt = the actual final attempt (2)."""
        msgs = drive_projected("FAILED_FINAL", "ASSY-SL03")
        term = terminal_msgs(msgs)[0]["payload"]
        assert term["attempt_number"] == 2

    def test_prior_fail_remains_non_terminal(self):
        """(5) The prior FAIL attempt stays non-terminal."""
        msgs = drive_projected("FAILED_FINAL", "ASSY-SL03")
        ap06 = quality_msgs(msgs, "AP06")
        assert len(ap06) == 2
        by_attempt = {m["payload"]["attempt_number"]: m["payload"] for m in ap06}
        assert by_attempt[1]["is_terminal"] is False
        assert by_attempt[1]["terminal_state"] == ""
        assert by_attempt[2]["is_terminal"] is True


# ═══════════════════════════════════════════════════════════
# 6-8. Non-terminal journeys emit no terminal marker
# ═══════════════════════════════════════════════════════════

class TestNonTerminalJourneys:
    def test_ap06_fail_then_pass_no_terminal(self):
        """(6) AP06 FAIL1 -> PASS2: no terminal failure, release proceeds."""
        msgs = drive_projected("AP06_FAIL_RETEST_PASS", "ASSY-SL03")
        assert terminal_msgs(msgs) == []
        ap06 = quality_msgs(msgs, "AP06")
        assert any(m["payload"]["attempt_number"] == 2
                   and m["payload"]["disposition"] == "PASS" for m in ap06)
        assert len(release_msgs(msgs)) >= 1

    def test_ap08_ng_then_pass_no_terminal(self):
        """(7) AP08 NG1 -> PASS2: no terminal marker."""
        msgs = drive_projected("AP08_NG_REINSPECT_PASS", "ASSY-SL02")
        assert terminal_msgs(msgs) == []
        ap08 = quality_msgs(msgs, "AP08")
        assert any(m["payload"]["disposition"] == "NG"
                   and m["payload"]["attempt_number"] == 1 for m in ap08)
        assert any(m["payload"]["disposition"] == "PASS"
                   and m["payload"]["attempt_number"] == 2 for m in ap08)
        assert len(release_msgs(msgs)) >= 1

    def test_happy_path_no_terminal(self):
        """(8) HAPPY_PATH across all sub-lines: no terminal marker anywhere."""
        for sl in ("ASSY-SL01", "ASSY-SL03", "ASSY-SL06"):
            msgs = drive_projected("HAPPY_PATH", sl)
            assert terminal_msgs(msgs) == []
            # only AP06/AP08 quality-result messages carry is_terminal
            ap06_ap08 = [m for m in msgs
                         if m["message_type"] == "mes.quality_result"
                         and "is_terminal" in m["payload"]]
            assert ap06_ap08
            assert all(m["payload"]["is_terminal"] is False
                       and m["payload"]["terminal_state"] == ""
                       for m in ap06_ap08)


# ═══════════════════════════════════════════════════════════
# 9. RELEASE absent for FAILED_FINAL
# ═══════════════════════════════════════════════════════════

class TestReleaseAbsent:
    def test_release_absent_for_failed_final(self):
        """(9) FAILED_FINAL: no RELEASE fact is emitted."""
        msgs = drive_projected("FAILED_FINAL", "ASSY-SL03")
        assert release_msgs(msgs) == []
        assert terminal_msgs(msgs)  # terminal evidence present


# ═══════════════════════════════════════════════════════════
# 10. Idempotency
# ═══════════════════════════════════════════════════════════

class TestIdempotency:
    def test_poll_replay_no_duplicate_terminal_fact(self):
        """(10) Poll/replay does not duplicate the terminal fact."""
        line = setup_line(ap06_always_fail_config())
        bridge, comp = bridge_for_runtime(line)
        drive_runtime(line, CompletionMode.AUTO, max_steps=120)
        bridge.poll(comp)
        first = list(bridge.outbound_trace)
        assert len(terminal_msgs([serialized(m) for m in bridge.projected_messages])) == 1
        results = bridge.poll(comp)
        assert results == []                      # nothing re-delivered
        assert list(bridge.outbound_trace) == first


# ═══════════════════════════════════════════════════════════
# 11. Six-line isolation
# ═══════════════════════════════════════════════════════════

class TestSixLineIsolation:
    def test_terminal_only_on_target_sub_line(self):
        """(11) Terminal marker appears only on the FAILED_FINAL target sub-line."""
        comp = AssyDemoComposition(config_path=TIPA_YAML,
                                   scenario=DemoScenario.FAILED_FINAL)
        comp.initialize()
        bridge = build_assy_observation_pipeline().bridge
        # drive all contexts
        for _ in range(60):
            comp.step_all()
        bridge.poll(comp)
        msgs = [serialized(m) for m in bridge.projected_messages]
        term = terminal_msgs(msgs)
        assert len(term) == 1
        run_id = term[0]["payload"]["run_id"]
        assert run_id.startswith("ASSY-SL03:")   # target only
        # other sub-lines have quality results but none terminal
        for sl in ("ASSY-SL01", "ASSY-SL02", "ASSY-SL04", "ASSY-SL05", "ASSY-SL06"):
            sl_msgs = [m for m in msgs if m["payload"]["run_id"].startswith(f"{sl}:")]
            assert terminal_msgs(sl_msgs) == []


# ═══════════════════════════════════════════════════════════
# 12. AUTO/MANUAL semantics unchanged
# ═══════════════════════════════════════════════════════════

class TestAutoManualEquivalence:
    def test_auto_manual_enriched_contract_identical(self):
        """(12) AUTO and MANUAL drive the identical enriched contract.

        simulation_time_s is intentionally excluded: MANUAL operator
        resolution adds a dwell cycle before the decision, so the record is
        timestamped a cadence later — the same accepted MANUAL≡AUTO timing
        behavior (M6-INT-01). The enriched semantic content (identity,
        attempt, disposition, finality) is identical.
        """
        def compact(msgs):
            return sorted(
                (m["message_key"], m["payload"]["record_id"],
                 m["payload"]["attempt_number"], m["payload"]["disposition"],
                 m["payload"]["is_terminal"], m["payload"]["terminal_state"],
                 m["payload"]["station_id"], m["payload"]["wip_id"])
                for m in msgs if m["message_type"] == "mes.quality_result")

        results = {}
        for mode in (CompletionMode.AUTO, CompletionMode.MANUAL):
            line = setup_line(ap06_always_fail_config())
            bridge, comp = bridge_for_runtime(line)
            drive_runtime(line, mode, max_steps=120)
            bridge.poll(comp)
            msgs = [serialized(m) for m in bridge.projected_messages]
            results[mode.value] = {
                "quality_records": compact(msgs),
                "terminal_count": len(terminal_msgs(msgs)),
                "releases": len(release_msgs(msgs)),
            }
        assert results["AUTO"] == results["MANUAL"]


# ═══════════════════════════════════════════════════════════
# 13-15. Backward compatibility + no MES/Odoo IDs
# ═══════════════════════════════════════════════════════════

class TestConsumerCompatibility:
    EXISTING_FIELDS = (
        "event_type", "record_id", "wip_id", "station_id",
        "check_type", "disposition", "attempt_number",
        "simulation_time_s", "reason_code",
    )

    def test_existing_payload_fields_intact(self):
        """(15) Non-upgraded consumer fields remain present and unchanged."""
        msgs = drive_projected("FAILED_FINAL", "ASSY-SL03")
        ap06 = quality_msgs(msgs, "AP06")
        assert ap06, "no AP06 quality messages"
        for m in ap06:
            p = m["payload"]
            for f in self.EXISTING_FIELDS:
                assert f in p, f"missing existing field {f}"
            assert m["schema_version"] == "1.0"
        # record_id / message_key identity preserved (per-attempt distinct)
        keys = {m["message_key"] for m in ap06}
        assert len(keys) == len(ap06)

    def test_message_type_and_schema_unchanged(self):
        """Additive only: same message_type / schema_name as before."""
        msgs = drive_projected("FAILED_FINAL", "ASSY-SL03")
        ap06 = quality_msgs(msgs, "AP06")
        for m in ap06:
            assert m["message_type"] == "mes.quality_result"
            assert m["schema_name"] == "vf.mes.quality_result"
            assert m["schema_version"] == "1.0"

    def test_no_mes_odoo_ids(self):
        """(14) No MES/Odoo integer DB ids introduced in any payload."""
        msgs = drive_projected("FAILED_FINAL", "ASSY-SL03")
        for m in msgs:
            p = m["payload"]
            for k, v in p.items():
                # observation_id is a UUID (audit), not an Odoo id
                if k == "observation_id":
                    continue
                assert not (isinstance(v, int) and k.lower().endswith("_id")), \
                    f"integer *_id field leaked: {k}={v}"
        # identity keys of quality-result messages are stable external codes
        ap06 = quality_msgs(msgs, "AP06")
        for m in ap06:
            p = m["payload"]
            for f in ("record_id", "wip_id", "station_id"):
                assert isinstance(p.get(f), str) and p.get(f), f"{f} not a code"


# ═══════════════════════════════════════════════════════════
# 16. Flows through the real projection path
# ═══════════════════════════════════════════════════════════

class TestProjectionPath:
    def test_terminal_fields_flow_through_mes_projection(self):
        """(16) The enriched fields reach the ProjectedMessage via the real path."""
        msgs = drive_projected("FAILED_FINAL", "ASSY-SL03")
        term = terminal_msgs(msgs)
        assert len(term) == 1
        t = term[0]
        # full envelope fields all present (identity/idempotency preserved)
        for f in ("observation_id", "idempotency_key", "run_id",
                  "simulation_time_s", "subject_type", "subject_id",
                  "station_id", "event_type", "record_id", "wip_id"):
            assert f in t["payload"], f"missing {f}"
        assert t["payload"]["idempotency_key"] == t["message_key"]
        assert t["payload"]["run_id"] == "ASSY-SL03:R1"
