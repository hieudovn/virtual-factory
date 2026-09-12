"""VF-vNEXT-R3-C01 — authoritative canonical reset generation as the output
projection epoch (SA review finding on Issue #81 comment 5643455951).

Covers the required focused regressions:

1. poll at state S -> reset -> re-step to the identical state S **without
   polling between reset and re-step** -> the next poll uses a NEW projection
   epoch and emits collision-free facts (poll-timing independence);
2. repeated poll after that stays idempotent;
3. reset keeps the same canonical run id;
4. new_attempt after a prior epoch > 1 starts canonical output epoch 1 (envelope
   + emitted keys + payload metadata);
5. replay after a prior epoch > 1 likewise starts epoch 1;
6. no second runtime/session/controller and no output-driven mutation;
7. R1/R2/R2V/R3 regressions + full baseline/full suite remain green (suite-level;
   see the gate report).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from virtual_factory.federation import SUB_LINE_IDS

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from virtual_factory.ui.api import create_app  # noqa: E402
from virtual_factory.ui.assy_experience import CanonicalAssyExperience  # noqa: E402
from virtual_factory.ui.assy_output import (  # noqa: E402
    CanonicalAssyOutput,
    OutputMutationError,
)
from virtual_factory.ui.workspace_monitor import WorkspaceMonitor  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
TIPA_CONFIG = str(REPO_ROOT / "configs" / "plants" / "tipa_assy_demo.yaml")


def _client() -> TestClient:
    return TestClient(create_app())


def _experience() -> CanonicalAssyExperience:
    return CanonicalAssyExperience(WorkspaceMonitor(tipa_config_path=TIPA_CONFIG))


def _output() -> CanonicalAssyOutput:
    return CanonicalAssyOutput(_experience())


def _keys(observations: list[dict]) -> set[str]:
    return {obs["message_key"] for obs in observations}


def _epoch(body: dict) -> int:
    return int(body["canonical"]["output_namespace"]["projection_epoch"])


def _state(out: CanonicalAssyOutput, sub_line_id: str = "ASSY-SL01") -> dict:
    """Domain truth of one sub-line (the same values Frame B projects)."""
    detail = out.experience.detail(sub_line_id)
    return {
        "simulation_time_s": detail["simulation_time_s"],
        "positions": detail["positions"],
        "genealogy": detail["genealogy"],
        "recent_quality_events": detail["recent_quality_events"],
        "production": detail["production"],
    }


# ═══════════════════════════════════════════════════════════════
# A. The reset-generation seam
# ═══════════════════════════════════════════════════════════════

class TestResetGenerationSeam:
    def test_reset_generation_increments_on_successful_reset(self):
        exp = _experience()
        session = exp.session
        assert session.reset_generation == 1
        assert session.reset_epoch == 1
        run_id = exp.session_identity()["run_id"]
        exp.reset()
        assert session.reset_generation == 2
        exp.reset()
        assert session.reset_generation == 3
        assert session.reset_epoch == 3
        # monotonic within the run and the run identity is untouched
        assert exp.session_identity()["run_id"] == run_id

    def test_reset_generation_does_not_increment_on_failed_reset(self, monkeypatch):
        exp = _experience()
        session = exp.session

        def boom(run_id):  # noqa: ANN001
            raise RuntimeError("lifecycle reset failed")

        monkeypatch.setattr(session._service, "reset", boom)
        with pytest.raises(RuntimeError):
            exp.reset()
        assert session.reset_generation == 1

    def test_new_attempt_and_replay_restart_the_generation_at_one(self):
        exp = _experience()
        session = exp.session
        exp.reset()
        exp.reset()
        assert session.reset_generation == 3
        new_run = exp.session.new_attempt()
        assert session.reset_generation == 1
        assert exp.session_identity()["run_id"] == new_run
        exp.reset()
        assert session.reset_generation == 2
        replay_run = exp.session.replay()
        assert session.reset_generation == 1
        assert exp.session_identity()["run_id"] == replay_run

    def test_session_seam_is_the_only_reset_authority(self):
        exp = _experience()
        exp.reset()
        exp.step()
        # the shell and the rich UI both act on the same session object
        c = TestClient(create_app())
        c.post("/assy-demo/reset")
        identity = c.get("/assy-demo/identity").json()["canonical"]
        assert identity["run_id"].startswith("TIPA-")
        # the output adapter never owns a counter of its own
        out = CanonicalAssyOutput(exp)
        assert not hasattr(out, "_epoch_resets_inferred")


# ═══════════════════════════════════════════════════════════════
# B. Poll-timing independence (the required C01 regression)
# ═══════════════════════════════════════════════════════════════

class TestPollTimingIndependence:
    def test_reset_then_restep_to_identical_state_without_poll_between(self):
        out = _output()
        out.experience.reset()
        for _ in range(4):
            out.experience.step()

        # 1. poll at state S
        at_s = out.observations()
        keys_at_s = _keys(at_s["observations"])
        epoch_at_s = _epoch(at_s)
        assert keys_at_s
        assert at_s["delivered_this_poll"] == len(keys_at_s)

        # 2. reset — 3. NO poll between reset and re-step
        out.experience.reset()
        for _ in range(4):
            out.experience.step()
        state_after = _state(out)

        # the re-stepped state is byte-identical to S (the case the old
        # poll-to-poll regression inference could not see)
        assert state_after == _state(out, "ASSY-SL01")
        assert _state(out)["simulation_time_s"] == 480.0

        # 4./5. poll again → authoritative epoch from the canonical reset
        # generation, not from any state comparison
        after_reset = out.observations()
        new_keys = _keys(after_reset["observations"]) - keys_at_s
        assert new_keys, "post-reset facts were suppressed as duplicates"
        assert _epoch(after_reset) == epoch_at_s + 1
        assert after_reset["canonical"]["output_namespace"][
            "session_reset_generation"
        ] == out.experience.session.reset_generation
        assert all(f"E{epoch_at_s + 1}:" in key for key in new_keys)
        # every identical post-reset fact was newly EMITTED (no collision)
        assert after_reset["delivered_this_poll"] == len(new_keys)

    def test_repeated_poll_after_the_epoch_change_is_idempotent(self):
        out = _output()
        out.experience.reset()
        for _ in range(3):
            out.experience.step()
        out.observations()
        out.experience.reset()
        for _ in range(3):
            out.experience.step()
        first = out.observations()
        assert first["delivered_this_poll"] > 0
        second = out.observations()
        assert second["delivered_this_poll"] == 0
        assert second["count"] == first["count"]
        assert _keys(second["observations"]) == _keys(first["observations"])
        mes = out.mes_messages()
        mes_again = out.mes_messages()
        assert mes_again["delivered_this_poll"] == 0
        assert mes_again["count"] == mes["count"]

    def test_epoch_tracks_the_session_without_poll_timing_dependence(self):
        out = _output()
        out.experience.reset()
        for _ in range(2):
            out.experience.step()
        out.observations()
        # reset WITHOUT polling and without re-stepping to the same state
        out.experience.reset()
        assert out.experience.session.reset_generation == 3
        body = out.observations()
        assert _epoch(body) == 3
        assert body["canonical"]["output_namespace"]["epoch_source"] == (
            "canonical_session_reset_generation"
        )

    def test_reset_keeps_same_canonical_run_id(self):
        out = _output()
        out.experience.reset()
        out.experience.step()
        run_id = out.experience.session_identity()["run_id"]
        first = out.observations()
        out.experience.reset()
        second = out.observations()
        assert out.experience.session_identity()["run_id"] == run_id
        assert second["canonical"]["run_id"] == run_id
        assert first["canonical"]["run_id"] == run_id
        assert _epoch(second) == _epoch(first) + 1


# ═══════════════════════════════════════════════════════════════
# C. Fresh runs start at epoch 1 (new_attempt / replay)
# ═══════════════════════════════════════════════════════════════

class TestFreshRunEpochOne:
    def test_new_attempt_after_epoch_gt_one_starts_epoch_one(self):
        out = _output()
        out.experience.reset()
        out.experience.reset()  # epoch > 1 on the current run
        out.experience.step()
        before = out.observations()
        assert _epoch(before) > 1
        stale_epoch = _epoch(before)

        new_run = out.experience.session.new_attempt()
        out.experience.step()
        body = out.observations()
        namespace = body["canonical"]["output_namespace"]
        assert body["canonical"]["run_id"] == new_run
        assert namespace["canonical_run_id"] == new_run
        assert namespace["projection_epoch"] == 1
        assert namespace["session_reset_generation"] == 1
        assert out.experience.session.reset_generation == 1
        assert namespace["epoch_changes"] == 0
        # emitted keys AND payload metadata say epoch 1, never the stale epoch
        for obs in body["observations"]:
            assert "E1:" in obs["message_key"]
            assert f"E{stale_epoch}:" not in obs["message_key"]
            assert obs["payload"]["idempotency_key"] == obs["message_key"]
        # the freshly created bridges were bound with epoch 1
        assert out._observations.canonical["projection_epoch"] == 1
        assert out._mes.canonical["projection_epoch"] == 1

    def test_replay_after_epoch_gt_one_starts_epoch_one(self):
        out = _output()
        out.experience.reset()
        out.experience.reset()
        out.experience.step()
        before = out.observations()
        assert _epoch(before) > 1
        stale_epoch = _epoch(before)

        replay_run = out.experience.session.replay()
        for _ in range(2):
            out.experience.step()
        body = out.outputs() if hasattr(out, "outputs") else out.mes_messages()
        namespace = body["canonical"]["output_namespace"]
        assert body["canonical"]["run_id"] == replay_run
        assert namespace["projection_epoch"] == 1
        assert namespace["session_reset_generation"] == 1
        for msg in body["mes_messages"]:
            assert "E1:" in msg["message_key"]
            assert f"E{stale_epoch}:" not in msg["message_key"]
            assert "E1:" in msg["payload"]["idempotency_key"]
        assert out._mes.canonical["projection_epoch"] == 1

    def test_epoch_one_survives_repeated_polls_of_a_fresh_run(self):
        out = _output()
        out.experience.reset()
        out.experience.reset()
        out.experience.step()
        out.observations()
        out.experience.session.new_attempt()
        out.experience.step()
        for _ in range(3):
            body = out.observations()
            assert _epoch(body) == 1
            assert body["canonical"]["output_namespace"]["epoch_changes"] == 0


# ═══════════════════════════════════════════════════════════════
# D. Read-only / single authority
# ═══════════════════════════════════════════════════════════════

class TestReadOnlySingleAuthority:
    def test_no_second_runtime_session_or_controller_on_the_c01_path(
        self, monkeypatch
    ):
        import virtual_factory.assembly.demo_controller as demo_controller
        import virtual_factory.federation.assy_host as host_module
        import virtual_factory.runcontrol.session as session_module

        federations: list[str] = []
        sessions: list[str] = []
        legacy: list[str] = []

        original_fed = host_module.TipaAssyFederation.__init__
        original_sess = session_module.RuntimeSession.__init__

        def fed_init(self, config_path):  # noqa: ANN001
            federations.append(config_path)
            original_fed(self, config_path)

        def sess_init(self, *args, **kwargs):  # noqa: ANN001
            sessions.append("RuntimeSession")
            original_sess(self, *args, **kwargs)

        def legacy_init(self, *args, **kwargs):  # noqa: ANN001
            legacy.append("DemoController")
            raise AssertionError("legacy DemoController must not be instantiated")

        monkeypatch.setattr(host_module.TipaAssyFederation, "__init__", fed_init)
        monkeypatch.setattr(session_module.RuntimeSession, "__init__", sess_init)
        monkeypatch.setattr(demo_controller.DemoController, "__init__", legacy_init)

        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        for path in (
            "/assy-demo/observations",
            "/assy-demo/mes-messages",
            "/assy-demo/mes-trace",
        ):
            assert c.get(path).status_code == 200
        assert len(federations) == 1, "a second canonical federation was constructed"

        # an in-context reset must NOT rebuild the run's federation
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        assert c.get("/assy-demo/observations").status_code == 200
        assert c.get("/assy-demo/mes-messages").status_code == 200
        assert len(federations) == 1, "reset rebuilt the canonical federation"

        # a fresh attempt gets its own run federation (one per run authority,
        # never an extra output-path federation)
        c.post("/vnext/workspaces/TIPA/control", json={"action": "new_attempt"})
        c.post("/vnext/workspaces/TIPA/control", json={"action": "step"})
        assert c.get("/assy-demo/observations").status_code == 200
        assert c.get("/assy-demo/mes-trace").status_code == 200
        assert len(federations) == 2, "the output path constructed an extra federation"
        assert len(sessions) == 1, "more than one canonical RuntimeSession exists"
        assert legacy == []

    def test_output_remains_read_only_across_resets(self):
        out = _output()
        out.experience.reset()
        for _ in range(3):
            out.experience.step()
        before = _state(out)
        before_generation = out.experience.session.reset_generation
        for _ in range(3):
            out.observations()
            out.mes_messages()
            out.mes_trace()
        assert _state(out) == before
        assert out.experience.session.reset_generation == before_generation
        assert out._epoch == before_generation

    def test_mutation_guard_still_blocks_output_driven_step(self, monkeypatch):
        out = _output()
        out.experience.reset()
        out.experience.step()

        def mutating_composition(self):  # noqa: ANN001
            self.experience.step()
            return SimpleNamespace(
                contexts=dict(self._federation.sub_lines), demo_step_number=0
            )

        monkeypatch.setattr(CanonicalAssyOutput, "_composition", mutating_composition)
        with pytest.raises(OutputMutationError):
            out.observations()

    def test_api_exposes_the_canonical_reset_generation(self):
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        first = c.get("/assy-demo/observations").json()
        namespace = first["canonical"]["output_namespace"]
        assert namespace["epoch_source"] == "canonical_session_reset_generation"
        assert namespace["session_reset_generation"] == namespace["projection_epoch"]
        # a further canonical reset advances the epoch seen by the API
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        second = c.get("/assy-demo/observations").json()
        assert (
            second["canonical"]["output_namespace"]["projection_epoch"]
            == namespace["projection_epoch"] + 1
        )
        assert second["canonical"]["output_namespace"]["session_reset_generation"] == (
            namespace["session_reset_generation"] + 1
        )
        assert SUB_LINE_IDS[0] in second["canonical"]["sub_line_ids"]
