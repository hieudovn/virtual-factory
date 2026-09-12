"""VF-vNEXT-R3-C01 — deterministic evidence generator (Issue #81 comment 5643455951).

Proves the SA finding is closed: the canonical output projection epoch is the
authoritative monotonic ``RuntimeSession.reset_generation`` (never inferred from
poll-to-poll state regression), fresh runs restart at epoch 1, the output stays
read-only/single-authority, and all regressions stay green.

Writes the C01 evidence artefacts next to this file; no product code is written.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from virtual_factory.federation import SUB_LINE_IDS
from virtual_factory.ui.api import create_app
from virtual_factory.ui.assy_experience import CanonicalAssyExperience
from virtual_factory.ui.assy_output import CanonicalAssyOutput, OutputMutationError
from virtual_factory.ui.workspace_monitor import WorkspaceMonitor

OUT = Path(__file__).resolve().parent


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "configs" / "plants" / "tipa_assy_demo.yaml").exists():
            return parent
    raise RuntimeError("repository root not found from C01 evidence generator")


REPO_ROOT = _repo_root()
TIPA_CONFIG = str(REPO_ROOT / "configs" / "plants" / "tipa_assy_demo.yaml")
PYTHON = sys.executable


def _write(name: str, payload: dict) -> None:
    (OUT / name).write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print("wrote", name)


def _client() -> TestClient:
    return TestClient(create_app())


def _output() -> CanonicalAssyOutput:
    return CanonicalAssyOutput(
        CanonicalAssyExperience(WorkspaceMonitor(tipa_config_path=TIPA_CONFIG))
    )


def _keys(observations: list[dict]) -> set[str]:
    return {obs["message_key"] for obs in observations}


def _state(out: CanonicalAssyOutput, sub_line_id: str = "ASSY-SL01") -> dict:
    detail = out.experience.detail(sub_line_id)
    return {
        "simulation_time_s": detail["simulation_time_s"],
        "positions": detail["positions"],
        "genealogy": detail["genealogy"],
        "recent_quality_events": detail["recent_quality_events"],
        "production": detail["production"],
    }


def _run_pytest(*targets: str) -> dict:
    proc = subprocess.run(
        [PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider", *targets],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    tail = (proc.stdout or "").strip().splitlines()[-1:] or [""]
    summary = tail[0].strip()
    match = re.search(r"(\d+) passed", summary)
    failed = re.search(r"(\d+) failed", summary)
    return {
        "targets": list(targets),
        "exit_code": proc.returncode,
        "summary": summary,
        "passed": int(match.group(1)) if match else 0,
        "failed": int(failed.group(1)) if failed else 0,
    }


# ───────────────────────────────────────────────────────────────
# 01. Authoritative reset-generation seam
# ───────────────────────────────────────────────────────────────
def evidence_01() -> dict:
    exp = CanonicalAssyExperience(WorkspaceMonitor(tipa_config_path=TIPA_CONFIG))
    session = exp.session
    initial = session.reset_generation
    run_id = exp.session_identity()["run_id"]

    exp.reset()
    after_first = session.reset_generation
    exp.reset()
    after_second = session.reset_generation
    run_id_after_resets = exp.session_identity()["run_id"]

    # a FAILED reset must not advance the generation
    original = session._service.reset
    failure_raised = False

    def boom(_run_id):  # noqa: ANN001
        raise RuntimeError("lifecycle reset failure (simulated)")

    session._service.reset = boom
    try:
        exp.reset()
    except RuntimeError:
        failure_raised = True
    finally:
        session._service.reset = original
    after_failed_reset = session.reset_generation

    new_run = exp.session.new_attempt()
    after_new_attempt = session.reset_generation
    exp.reset()
    after_reset_in_new_attempt = session.reset_generation
    replay_run = exp.session.replay()
    after_replay = session.reset_generation

    out = _output()
    out.experience.reset()
    generation_before_polls = out.experience.session.reset_generation
    out.observations()
    out.mes_messages()
    generation_after_polls = out.experience.session.reset_generation
    payload = {
        "seam": "RuntimeSession.reset_generation / reset_epoch (runcontrol/session.py)",
        "initial_generation": initial,
        "after_first_reset": after_first,
        "after_second_reset": after_second,
        "monotonic_within_run": initial == 1 and after_first == 2 and after_second == 3,
        "run_id": run_id,
        "run_id_unchanged_by_reset": run_id_after_resets == run_id,
        "failed_reset_raised": failure_raised,
        "generation_after_failed_reset": after_failed_reset,
        "failed_reset_did_not_advance": after_failed_reset == after_second,
        "new_attempt_run_id": new_run,
        "generation_after_new_attempt": after_new_attempt,
        "generation_after_reset_in_new_run": after_reset_in_new_attempt,
        "replay_run_id": replay_run,
        "generation_after_replay": after_replay,
        "fresh_runs_start_at_one": (
            after_new_attempt == 1 and after_replay == 1
        ),
        "adapter_has_no_epoch_inference": (
            not hasattr(CanonicalAssyOutput, "_advance_epoch_if_reset")
        ),
        "adapter_epoch_equals_session_generation": (
            out._epoch == out.experience.session.reset_generation
        ),
        "epoch_source_reported": out.observations()["canonical"]["output_namespace"][
            "epoch_source"
        ],
        "read_only_output_does_not_change_generation": (
            generation_before_polls == generation_after_polls
        ),
    }
    payload["PASS"] = (
        payload["monotonic_within_run"]
        and payload["run_id_unchanged_by_reset"]
        and payload["failed_reset_raised"]
        and payload["failed_reset_did_not_advance"]
        and payload["fresh_runs_start_at_one"]
        and payload["adapter_has_no_epoch_inference"]
        and payload["adapter_epoch_equals_session_generation"]
        and payload["epoch_source_reported"] == "canonical_session_reset_generation"
        and payload["read_only_output_does_not_change_generation"]
    )
    _write("01-reset-generation-seam.json", payload)
    return payload


# ───────────────────────────────────────────────────────────────
# 02. Poll-timing independence (the required focused regression)
# ───────────────────────────────────────────────────────────────
def evidence_02() -> dict:
    out = _output()
    out.experience.reset()
    for _ in range(4):
        out.experience.step()

    at_s = out.observations()
    keys_at_s = _keys(at_s["observations"])
    epoch_at_s = at_s["canonical"]["output_namespace"]["projection_epoch"]
    state_at_s = _state(out)

    # reset, then re-step deterministically to the SAME state WITHOUT any poll
    out.experience.reset()
    for _ in range(4):
        out.experience.step()
    state_after_restep = _state(out)

    after_reset = out.observations()
    new_keys = _keys(after_reset["observations"]) - keys_at_s
    epoch_after = after_reset["canonical"]["output_namespace"]["projection_epoch"]
    repeat = out.observations()
    mes_repeat = out.mes_messages()

    payload = {
        "sequence": [
            "poll at state S",
            "RuntimeSession.reset()",
            "no poll between reset and re-step",
            "step back to the identical state S",
            "poll again",
        ],
        "state_S_time_s": state_at_s["simulation_time_s"],
        "state_after_restep_identical": state_after_restep == state_at_s,
        "epoch_at_state_S": epoch_at_s,
        "epoch_after_reset_poll": epoch_after,
        "session_reset_generation": out.experience.session.reset_generation,
        "session_generation_matches_epoch": (
            epoch_after == out.experience.session.reset_generation
        ),
        "epoch_source": after_reset["canonical"]["output_namespace"]["epoch_source"],
        "new_facts_emitted": len(new_keys),
        "delivered_this_poll": after_reset["delivered_this_poll"],
        "delivered_equals_new_keys": after_reset["delivered_this_poll"] == len(new_keys),
        "all_new_keys_in_new_epoch": all(
            f"E{epoch_after}:" in key for key in new_keys
        ),
        "no_collision_with_pre_reset_keys": not (new_keys & keys_at_s),
        "repeated_poll_delivered": repeat["delivered_this_poll"],
        "repeated_poll_count_unchanged": repeat["count"] == after_reset["count"],
        "repeated_mes_poll_delivered": mes_repeat["delivered_this_poll"],
    }
    payload["PASS"] = (
        payload["state_after_restep_identical"]
        and payload["epoch_after_reset_poll"] == epoch_at_s + 1
        and payload["session_generation_matches_epoch"]
        and payload["new_facts_emitted"] > 0
        and payload["delivered_equals_new_keys"]
        and payload["all_new_keys_in_new_epoch"]
        and payload["no_collision_with_pre_reset_keys"]
        and payload["repeated_poll_delivered"] == 0
        and payload["repeated_mes_poll_delivered"] == 0
    )
    _write("02-poll-timing-independence.json", payload)
    return payload


# ───────────────────────────────────────────────────────────────
# 03. Fresh runs (new attempt / replay) start at epoch 1
# ───────────────────────────────────────────────────────────────
def evidence_03() -> dict:
    out = _output()
    out.experience.reset()
    out.experience.reset()
    out.experience.step()
    stale = out.observations()
    stale_epoch = stale["canonical"]["output_namespace"]["projection_epoch"]

    new_run = out.experience.session.new_attempt()
    out.experience.step()
    attempted = out.observations()
    attempt_ns = attempted["canonical"]["output_namespace"]

    replay_run = out.experience.session.replay()
    out.experience.step()
    replayed = out.mes_messages()
    replay_ns = replayed["canonical"]["output_namespace"]

    payload = {
        "stale_epoch_before_fresh_run": stale_epoch,
        "stale_epoch_gt_one": stale_epoch > 1,
        "new_attempt": {
            "run_id": new_run,
            "canonical_run_id_in_envelope": attempted["canonical"]["run_id"],
            "output_namespace_run_id": attempt_ns["canonical_run_id"],
            "projection_epoch": attempt_ns["projection_epoch"],
            "session_reset_generation": attempt_ns["session_reset_generation"],
            "epoch_changes": attempt_ns["epoch_changes"],
            "keys_in_epoch_one": all(
                "E1:" in obs["message_key"] for obs in attempted["observations"]
            ),
            "payload_metadata_in_epoch_one": all(
                "E1:" in obs["payload"]["idempotency_key"]
                for obs in attempted["observations"]
            ),
            "no_stale_epoch_in_keys": all(
                f"E{stale_epoch}:" not in obs["message_key"]
                for obs in attempted["observations"]
            ),
            "bridge_binding_epoch": out._observations.canonical["projection_epoch"],
        },
        "replay": {
            "run_id": replay_run,
            "canonical_run_id_in_envelope": replayed["canonical"]["run_id"],
            "output_namespace_run_id": replay_ns["canonical_run_id"],
            "projection_epoch": replay_ns["projection_epoch"],
            "session_reset_generation": replay_ns["session_reset_generation"],
            "keys_in_epoch_one": all(
                "E1:" in msg["message_key"] for msg in replayed["mes_messages"]
            ),
            "payload_metadata_in_epoch_one": all(
                "E1:" in msg["payload"]["idempotency_key"]
                for msg in replayed["mes_messages"]
            ),
            "no_stale_epoch_in_keys": all(
                f"E{stale_epoch}:" not in msg["message_key"]
                for msg in replayed["mes_messages"]
            ),
            "bridge_binding_epoch": out._mes.canonical["projection_epoch"],
        },
    }
    payload["PASS"] = (
        payload["stale_epoch_gt_one"]
        and payload["new_attempt"]["projection_epoch"] == 1
        and payload["new_attempt"]["session_reset_generation"] == 1
        and payload["new_attempt"]["epoch_changes"] == 0
        and payload["new_attempt"]["keys_in_epoch_one"]
        and payload["new_attempt"]["payload_metadata_in_epoch_one"]
        and payload["new_attempt"]["no_stale_epoch_in_keys"]
        and payload["new_attempt"]["bridge_binding_epoch"] == 1
        and payload["replay"]["projection_epoch"] == 1
        and payload["replay"]["keys_in_epoch_one"]
        and payload["replay"]["payload_metadata_in_epoch_one"]
        and payload["replay"]["no_stale_epoch_in_keys"]
        and payload["replay"]["bridge_binding_epoch"] == 1
    )
    _write("03-fresh-run-epoch-one.json", payload)
    return payload


# ───────────────────────────────────────────────────────────────
# 04. Read-only / single authority
# ───────────────────────────────────────────────────────────────
class _Counter:
    def __init__(self) -> None:
        self.federations: list[str] = []
        self.sessions: list[str] = []
        self.legacy: list[str] = []

    def __enter__(self):
        import virtual_factory.assembly.demo_controller as demo_controller
        import virtual_factory.federation.assy_host as host
        import virtual_factory.runcontrol.session as session_module

        self._restore = []

        def fed_init(inner, config_path):  # noqa: ANN001
            self.federations.append(str(config_path))
            original_fed(inner, config_path)

        def sess_init(inner, *args, **kwargs):  # noqa: ANN001
            self.sessions.append("RuntimeSession")
            original_sess(inner, *args, **kwargs)

        def legacy_init(inner, *args, **kwargs):  # noqa: ANN001
            self.legacy.append("DemoController")
            raise AssertionError("legacy DemoController must not be instantiated")

        original_fed = host.TipaAssyFederation.__init__
        original_sess = session_module.RuntimeSession.__init__
        original_legacy = demo_controller.DemoController.__init__
        host.TipaAssyFederation.__init__ = fed_init
        session_module.RuntimeSession.__init__ = sess_init
        demo_controller.DemoController.__init__ = legacy_init
        self._restore = [
            (host.TipaAssyFederation, original_fed),
            (session_module.RuntimeSession, original_sess),
            (demo_controller.DemoController, original_legacy),
        ]
        return self

    def __exit__(self, *exc):  # noqa: ANN002
        for target, original in self._restore:
            target.__init__ = original
        return False


def evidence_04() -> dict:
    counter = _Counter()
    with counter:
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        for path in (
            "/assy-demo/observations",
            "/assy-demo/mes-messages",
            "/assy-demo/mes-trace",
        ):
            assert c.get(path).status_code == 200
        federations_after_first_run = len(counter.federations)
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        assert c.get("/assy-demo/observations").status_code == 200
        federations_after_reset = len(counter.federations)
        c.post("/vnext/workspaces/TIPA/control", json={"action": "new_attempt"})
        c.post("/vnext/workspaces/TIPA/control", json={"action": "step"})
        assert c.get("/assy-demo/mes-messages").status_code == 200
        federations_after_new_attempt = len(counter.federations)

    out = _output()
    out.experience.reset()
    for _ in range(3):
        out.experience.step()
    before_state = _state(out)
    before_generation = out.experience.session.reset_generation
    for _ in range(3):
        out.observations()
        out.mes_messages()
        out.mes_trace()
    after_state = _state(out)
    after_generation = out.experience.session.reset_generation

    def mutating_composition(self):  # noqa: ANN001
        self.experience.step()
        from types import SimpleNamespace

        return SimpleNamespace(
            contexts=dict(self._federation.sub_lines), demo_step_number=0
        )

    guard_raised = False
    original = CanonicalAssyOutput._composition
    try:
        CanonicalAssyOutput._composition = mutating_composition
        out.observations()
    except OutputMutationError:
        guard_raised = True
    finally:
        CanonicalAssyOutput._composition = original

    payload = {
        "federations_after_first_run": federations_after_first_run,
        "federations_after_in_context_reset": federations_after_reset,
        "federations_after_new_attempt": federations_after_new_attempt,
        "reset_does_not_rebuild_federation": (
            federations_after_reset == federations_after_first_run == 1
        ),
        "one_federation_per_run_authority": federations_after_new_attempt == 2,
        "sessions_constructed": len(counter.sessions),
        "exactly_one_canonical_session": len(counter.sessions) == 1,
        "legacy_controllers_constructed": counter.legacy,
        "no_legacy_controller": counter.legacy == [],
        "polling_leaves_state_unchanged": before_state == after_state,
        "polling_leaves_reset_generation_unchanged": (
            before_generation == after_generation
        ),
        "mutation_guard_raises": guard_raised,
        "sub_line_count": len(SUB_LINE_IDS),
    }
    payload["PASS"] = (
        payload["reset_does_not_rebuild_federation"]
        and payload["one_federation_per_run_authority"]
        and payload["exactly_one_canonical_session"]
        and payload["no_legacy_controller"]
        and payload["polling_leaves_state_unchanged"]
        and payload["polling_leaves_reset_generation_unchanged"]
        and payload["mutation_guard_raises"]
    )
    _write("04-no-second-authority-read-only.json", payload)
    return payload


# ───────────────────────────────────────────────────────────────
# 05. Regression (machine-derived pytest counts)
# ───────────────────────────────────────────────────────────────
def evidence_05() -> dict:
    suites = {
        "c01_reset_generation": [
            "tests/test_vnext_r3_c01_reset_generation.py"
        ],
        "r3_canonical_observation_mes": [
            "tests/test_vnext_r3_canonical_observation_mes.py"
        ],
        "r1_production_semantics": ["tests/test_vnext_r1_production_semantics.py"],
        "r2_same_session_rich_assy": [
            "tests/test_vnext_r2_same_session_rich_assy.py"
        ],
        "g22_session_replay": ["tests/test_vnext_g22_session.py"],
        "observation_lifecycle": [
            "tests/test_m6_int_01.py",
            "tests/test_assy_mes_bridge_v1.py",
            "tests/test_assy_mes_03_evidence.py",
            "tests/test_vf_contract_finality_01.py",
        ],
    }
    results: dict[str, dict] = {}
    for name, targets in suites.items():
        if not all((REPO_ROOT / t).exists() for t in targets):
            results[name] = {"targets": targets, "skipped": "module not present"}
            continue
        results[name] = _run_pytest(*targets)
    full = _run_pytest("tests")
    payload = {
        "suites": results,
        "full_suite": full,
        "baseline": (
            "canonical baseline (40 groups + checks) is run at the pushed head and "
            "recorded in the gate report / SA submission"
        ),
    }
    payload["PASS"] = all(
        entry.get("exit_code") == 0 and entry.get("failed") == 0
        for entry in results.values()
        if "exit_code" in entry
    ) and full["exit_code"] == 0
    _write("05-regression.json", payload)
    return payload


def main() -> int:
    results = {
        "01_reset_generation_seam": evidence_01(),
        "02_poll_timing_independence": evidence_02(),
        "03_fresh_run_epoch_one": evidence_03(),
        "04_no_second_authority_read_only": evidence_04(),
        "05_regression": evidence_05(),
    }
    print()
    for name, payload in results.items():
        print(f"{name}: PASS={payload['PASS']}")
    if not all(payload["PASS"] for payload in results.values()):
        print("EVIDENCE FAILED")
        return 1
    print("R3-C01 evidence complete: all sections PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
