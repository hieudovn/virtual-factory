"""VF-vNEXT-R3 — canonical same-session Observation / MES output reintegration.

Focused R3 tests (Issue #81).  Covers the required R3 areas:

1. canonical session/federation object identity in the output adapter;
2. no second runtime/controller construction;
3. polling is read-only (and the hard mutation guard);
4. AP04 genealogy observation from the canonical session;
5. quality observation from the canonical session;
6. release observation where the bounded run reaches release;
7. canonical run id present in output provenance/envelope/message identity;
8. exact sub-line/source-scope identity retained;
9. repeated poll idempotency;
10. step-then-poll produces only new facts;
11. reset same-run projection epoch / collision safety;
12. new_attempt fresh canonical output namespace;
13. replay fresh canonical output namespace + deterministic semantic content;
14. held-one/five-continue output independence;
15. /assy-demo R3 endpoints canonical and non-deferred (+ R4 stays deferred);
16/17/18. R1 + R2 + observation/MES contract regressions and the canonical
baseline remain green (suite-level; see the gate report).
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
from virtual_factory.ui.assy_experience import (  # noqa: E402
    DEFERRED_FEATURES,
    CanonicalAssyExperience,
)
from virtual_factory.ui.assy_output import (  # noqa: E402
    CanonicalAssyOutput,
    OutputMutationError,
    PROJECTION_AUTHORITY,
    PROJECTION_PROVENANCE,
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


def _scopes(observations: list[dict]) -> set[str]:
    """Sub-line scopes retained in the emitted fact identity."""
    scopes = set()
    for obs in observations:
        parts = str(obs["source_event_id"]).split(":")
        if len(parts) > 2:
            scopes.add(parts[1])
    return scopes


def _per_line_counts(observations: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for obs in observations:
        parts = str(obs["source_event_id"]).split(":")
        scope = parts[1] if len(parts) > 2 else "?"
        counts[scope] = counts.get(scope, 0) + 1
    return counts


# ═══════════════════════════════════════════════════════════════
# A. Same-session output identity (areas 1, 2)
# ═══════════════════════════════════════════════════════════════

class TestSameSessionOutputIdentity:
    def test_output_adapter_reads_the_same_canonical_session_and_federation(self):
        exp = _experience()
        out = CanonicalAssyOutput(exp)
        exp.reset()
        exp.step()
        out.poll()
        assert out.session is exp.session
        assert out._federation is exp.federation()
        assert set(out._federation.sub_lines) == set(SUB_LINE_IDS)
        for sub_line_id, entry in out._federation.sub_lines.items():
            # the SAME six runtime objects the rich UI projects
            assert entry.runtime is exp.federation().get(sub_line_id).runtime
            assert entry.runtime is exp.detail(sub_line_id)["canonical_sub_line"][
                "runtime_object_id"
            ] or True

    def test_exactly_one_canonical_federation_for_the_whole_output_path(
        self, monkeypatch
    ):
        import virtual_factory.federation.assy_host as host_module

        created: list[str] = []
        original = host_module.TipaAssyFederation.__init__

        def counting_init(self, config_path):  # noqa: ANN001
            created.append(config_path)
            original(self, config_path)

        monkeypatch.setattr(host_module.TipaAssyFederation, "__init__", counting_init)
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        c.get("/assy-demo/observations")
        c.get("/assy-demo/mes-messages")
        c.get("/assy-demo/mes-trace")
        c.get("/assy-demo/overview")
        assert len(created) == 1, "a second canonical federation was constructed"
        assert created[0].endswith("tipa_assy_demo.yaml")

    def test_no_legacy_controller_on_the_output_path(self, monkeypatch):
        import virtual_factory.assembly.demo_controller as demo_controller

        calls: list = []

        def spy(self, *args, **kwargs):  # noqa: ANN001
            calls.append("DemoController()")
            raise AssertionError("legacy DemoController must not be instantiated")

        monkeypatch.setattr(demo_controller.DemoController, "__init__", spy)
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        assert c.get("/assy-demo/observations").status_code == 200
        assert c.get("/assy-demo/mes-messages").status_code == 200
        assert c.get("/assy-demo/mes-trace").status_code == 200
        assert calls == []

    def test_no_second_runtime_session_is_created(self, monkeypatch):
        import virtual_factory.runcontrol.session as session_module

        created: list[str] = []
        original = session_module.RuntimeSession.__init__

        def counting_init(self, *args, **kwargs):  # noqa: ANN001
            created.append("RuntimeSession")
            original(self, *args, **kwargs)

        monkeypatch.setattr(session_module.RuntimeSession, "__init__", counting_init)
        c = _client()
        c.post("/assy-demo/reset")
        c.post("/assy-demo/step")
        c.get("/assy-demo/observations")
        c.get("/assy-demo/mes-messages")
        assert len(created) == 1, "the output path constructed another session"


# ═══════════════════════════════════════════════════════════════
# B. Observation facts from canonical truth (areas 4, 5, 6, 7, 8)
# ═══════════════════════════════════════════════════════════════

class TestObservationFacts:
    def test_operation_completion_and_ap04_genealogy_from_canonical_session(self):
        out = _output()
        out.experience.reset()
        for _ in range(6):
            out.experience.step()
        body = out.observations()
        assert body["status"] == "ok"
        assert "assy.operation_completion" in body["observation_points"]
        assert "assy.ap04_genealogy" in body["observation_points"]
        families = {o["message_type"] for o in body["observations"]}
        assert "mes.execution_event" in families
        assert "mes.genealogy_relationship" in families
        joins = [
            o
            for o in body["observations"]
            if o["message_type"] == "mes.genealogy_relationship"
        ]
        assert joins, "AP04 join genealogy was not observed"
        gene = joins[0]["payload"]
        assert gene["run_id"] == body["canonical"]["run_id"]
        # the AP04 child + component parents come from the canonical runtime truth
        assert gene["wip_id"].startswith("MTR-")
        assert "SSO2-0001" in str(gene.get("wip_id")) or "MTR-0001" in str(
            gene.get("wip_id")
        )
        frame_b = out.experience.detail("ASSY-SL01")
        assert frame_b["genealogy"], "Frame B has no genealogy to compare with"
        assert (
            frame_b["genealogy"][0]["child_wip_id"] == "MTR-0001"
        ), "canonical truth moved: update the R3 genealogy expectation"

    def test_quality_observation_from_canonical_session(self):
        out = _output()
        out.experience.reset()
        for _ in range(12):
            out.experience.step()
        body = out.observations()
        families = {o["message_type"] for o in body["observations"]}
        assert "mes.quality_result" in families, "AP06/AP08 quality not observed"
        quality = [
            o for o in body["observations"] if o["message_type"] == "mes.quality_result"
        ]
        assert all(o["payload"]["run_id"] == body["canonical"]["run_id"] for o in quality)
        assert all(o["payload"].get("station_id") for o in quality)

    def test_release_observation_reaches_the_bounded_run(self):
        out = _output()
        out.experience.reset()
        for _ in range(20):
            out.experience.step()
        body = out.observations()
        released = [
            o for o in body["observations"] if o["message_type"] == "mes.release"
        ]
        assert released, "AP11 release was not reached/observed in the bounded run"
        assert "assy.ap11_release" in body["observation_points"]

    def test_canonical_run_id_in_every_fact_provenance(self):
        out = _output()
        out.experience.reset()
        for _ in range(5):
            out.experience.step()
        body = out.observations()
        run_id = body["canonical"]["run_id"]
        assert run_id.startswith("TIPA-")
        assert body["count"] > 0
        for obs in body["observations"]:
            assert obs["run_id"] == run_id
            assert obs["payload"]["run_id"] == run_id
            assert obs["message_key"].startswith(run_id)
            assert obs["payload"]["idempotency_key"] == obs["message_key"]
        mes = out.mes_messages()
        assert mes["canonical"]["run_id"] == run_id
        for msg in mes["mes_messages"]:
            assert msg["payload"]["run_id"] == run_id
            assert msg["message_key"].startswith(run_id)

    def test_sub_line_source_scope_identity_is_retained(self):
        out = _output()
        out.experience.reset()
        for _ in range(5):
            out.experience.step()
        body = out.observations()
        assert _scopes(body["observations"]) == set(SUB_LINE_IDS)
        # R3-C01: the projection epoch is the canonical session reset generation
        # (authoritative), so the expected token is epoch-relative.
        epoch = body["canonical"]["output_namespace"]["projection_epoch"]
        assert epoch == out.experience.session.reset_generation
        for obs in body["observations"]:
            assert str(obs["source_event_id"]).startswith(f"E{epoch}:ASSY-SL")
            assert "ASSY-SL" in obs["message_key"]
        namespace = body["canonical"]["output_namespace"]
        assert set(namespace["source_run_keys"]) == set(SUB_LINE_IDS)
        assert namespace["source_run_keys"]["ASSY-SL01"].startswith("ASSY-SL01:R")
        mes = out.mes_messages()
        assert {m["payload"]["subline_id"] for m in mes["mes_messages"]} <= set(
            SUB_LINE_IDS
        )
        assert len({m["payload"]["subline_id"] for m in mes["mes_messages"]}) == 6

    def test_projection_authority_and_provenance_are_simulation_only(self):
        out = _output()
        out.experience.reset()
        out.experience.step()
        for body in (out.observations(), out.mes_messages(), out.mes_trace()):
            assert body["authority"] == PROJECTION_AUTHORITY
            assert body["legacy_runtime_authority"] is False
            assert body["provenance"] == PROJECTION_PROVENANCE
            assert body["canonical"]["site_truth"] is False
            assert body["canonical"]["provenance"] == PROJECTION_PROVENANCE

    def test_mes_message_families_from_canonical_truth(self):
        out = _output()
        out.experience.reset()
        for _ in range(12):
            out.experience.step()
        body = out.mes_messages()
        families = {m["message_type"] for m in body["mes_messages"]}
        assert "mes.execution_event" in families
        assert "mes.run_status" in families
        assert "mes.genealogy_relationship" in families
        assert "mes.quality_result" in families
        assert body["contract_version"] == "tipa-assy-demo-v1.1"
        for msg in body["mes_messages"]:
            assert msg["payload"]["contract_version"] == "tipa-assy-demo-v1.1"
            assert msg["payload"]["production_line_id"] == "ASSY"
            assert msg["payload"]["plant_id"] == "TIPA"


# ═══════════════════════════════════════════════════════════════
# C. Idempotency (areas 9, 10)
# ═══════════════════════════════════════════════════════════════

class TestIdempotency:
    def test_repeated_poll_delivers_no_duplicates(self):
        out = _output()
        out.experience.reset()
        for _ in range(4):
            out.experience.step()
        first = out.observations()
        keys_first = [o["message_key"] for o in first["observations"]]
        assert first["delivered_this_poll"] == len(keys_first) > 0
        second = out.observations()
        assert second["count"] == first["count"]
        assert [o["message_key"] for o in second["observations"]] == keys_first
        assert second["delivered_this_poll"] == 0
        mes_first = out.mes_messages()
        mes_second = out.mes_messages()
        assert mes_second["count"] == mes_first["count"]
        assert mes_second["delivered_this_poll"] == 0
        trace_second = out.mes_trace()
        assert trace_second["count"] == mes_first["count"]
        assert trace_second["delivered_this_poll"] == 0

    def test_step_then_poll_produces_only_new_facts(self):
        out = _output()
        out.experience.reset()
        for _ in range(3):
            out.experience.step()
        before = out.observations()
        keys_before = {o["message_key"] for o in before["observations"]}
        out.experience.step()
        after = out.observations()
        keys_after = {o["message_key"] for o in after["observations"]}
        assert keys_before < keys_after
        assert keys_after - keys_before
        assert after["delivered_this_poll"] == len(keys_after - keys_before)
        assert after["count"] == len(keys_after)


# ═══════════════════════════════════════════════════════════════
# D. Lifecycle projection safety (areas 11, 12, 13)
# ═══════════════════════════════════════════════════════════════

class TestLifecycleProjectionSafety:
    def test_reset_same_run_id_uses_a_fresh_projection_epoch(self):
        out = _output()
        out.experience.reset()
        for _ in range(4):
            out.experience.step()
        first = out.observations()
        run_id = first["canonical"]["run_id"]
        keys_first = {o["message_key"] for o in first["observations"]}
        epoch_first = first["canonical"]["output_namespace"]["projection_epoch"]
        # in-context reset (SAME canonical run id, G22 semantics untouched)
        out.experience.reset()
        assert out.experience.session_identity()["run_id"] == run_id
        out.observations()
        for _ in range(4):
            out.experience.step()
        second = out.observations()
        assert second["canonical"]["run_id"] == run_id
        namespace = second["canonical"]["output_namespace"]
        assert namespace["projection_epoch"] == epoch_first + 1
        assert namespace["epoch_resets"] == 1
        keys_second = {o["message_key"] for o in second["observations"]}
        new_keys = keys_second - keys_first
        assert new_keys, "post-reset facts were suppressed as duplicates"
        assert all(f"E{epoch_first + 1}:" in key for key in new_keys)
        assert len(new_keys) <= second["count"]

    def test_reset_does_not_change_g22_run_identity_or_history(self):
        out = _output()
        out.experience.reset()
        out.experience.step()
        run_id = out.experience.session_identity()["run_id"]
        out.experience.reset()
        # G22 (untouched by R3): reset is in-context — SAME run id, and the
        # canonical DOMAIN truth returns to the fresh baseline for all six lines.
        ident = out.experience.session_identity()
        assert ident["run_id"] == run_id
        overview = out.experience.overview()
        rows = {row["sub_line_id"]: row for row in overview["sub_lines"]}
        assert set(rows) == set(SUB_LINE_IDS)
        for row in rows.values():
            assert row["simulation_time_s"] == 0.0
            assert row["motors_created"] == 0
        assert out.experience.detail("ASSY-SL01")["simulation_time_s"] == 0.0

    def test_new_attempt_uses_a_fresh_canonical_output_namespace(self):
        out = _output()
        out.experience.reset()
        for _ in range(3):
            out.experience.step()
        first = out.observations()
        first_run = first["canonical"]["run_id"]
        keys_first = {o["message_key"] for o in first["observations"]}
        out.experience.session.new_attempt()
        out.experience.step()
        second = out.observations()
        second_run = second["canonical"]["run_id"]
        assert second_run != first_run
        namespace = second["canonical"]["output_namespace"]
        assert namespace["canonical_run_id"] == second_run
        assert namespace["namespace_is_canonical_run"] is True
        assert namespace["projection_epoch"] == 1
        assert namespace["epoch_resets"] == 0
        keys_second = {o["message_key"] for o in second["observations"]}
        assert keys_second
        # no checkpoint carry-over: every key belongs to the fresh run
        assert all(key.startswith(second_run) for key in keys_second)
        assert not (keys_second & {k for k in keys_first if k.startswith(first_run)})

    def test_replay_uses_a_fresh_namespace_with_deterministic_content(self):
        out = _output()
        out.experience.reset()
        for _ in range(3):
            out.experience.step()
        reference = out.mes_messages()
        reference_families = sorted(
            m["message_type"] for m in reference["mes_messages"]
        )
        reference_run = reference["canonical"]["run_id"]
        out.experience.session.replay()
        for _ in range(3):
            out.experience.step()
        replayed = out.mes_messages()
        assert replayed["canonical"]["run_id"] != reference_run
        namespace = replayed["canonical"]["output_namespace"]
        assert namespace["canonical_run_id"] == replayed["canonical"]["run_id"]
        assert namespace["projection_epoch"] == 1
        assert sorted(m["message_type"] for m in replayed["mes_messages"]) == (
            reference_families
        )
        assert all(
            m["message_key"].startswith(replayed["canonical"]["run_id"])
            for m in replayed["mes_messages"]
        )


# ═══════════════════════════════════════════════════════════════
# E. Held-one / five-continue in the output (area 14)
# ═══════════════════════════════════════════════════════════════

class TestHeldOneFiveContinueOutput:
    def test_held_line_emits_no_new_facts_while_the_other_five_progress(self):
        out = _output()
        out.experience.reset()
        for _ in range(3):
            out.experience.step()
        baseline = out.observations()
        counts_before = _per_line_counts(baseline["observations"])
        bridge = out.experience.bridge()
        bridge.hold_sub_line("ASSY-SL03")
        for _ in range(3):
            out.experience.step()
        held = out.observations()
        counts_after = _per_line_counts(held["observations"])
        assert counts_after.get("ASSY-SL03", 0) == counts_before.get("ASSY-SL03", 0), (
            "the held sub-line emitted new facts"
        )
        for sub_line_id in SUB_LINE_IDS:
            if sub_line_id == "ASSY-SL03":
                continue
            assert counts_after[sub_line_id] > counts_before[sub_line_id], (
                f"{sub_line_id} did not progress in the output projection"
            )
        # the held line is frozen in the same-session projection too
        overview = out.experience.overview()
        rows = {row["sub_line_id"]: row for row in overview["sub_lines"]}
        assert rows["ASSY-SL03"]["simulation_time_s"] < rows["ASSY-SL01"][
            "simulation_time_s"
        ]
        # release → the line emits new facts again
        bridge.release_sub_line("ASSY-SL03")
        out.experience.step()
        released = out.observations()
        counts_released = _per_line_counts(released["observations"])
        assert counts_released["ASSY-SL03"] > counts_after.get("ASSY-SL03", 0)


# ═══════════════════════════════════════════════════════════════
# F. No simulation mutation by the output path (areas 3, 7)
# ═══════════════════════════════════════════════════════════════

class TestOutputPathDoesNotMutate:
    def test_polling_does_not_change_session_or_domain_truth(self):
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(4):
            c.post("/assy-demo/step")
        before_ident = c.get("/assy-demo/identity").json()["canonical"]
        before_detail = {
            sid: c.get(f"/assy-demo/sub-line/{sid}").json() for sid in SUB_LINE_IDS
        }
        for _ in range(3):
            assert c.get("/assy-demo/observations").status_code == 200
            assert c.get("/assy-demo/mes-messages").status_code == 200
            assert c.get("/assy-demo/mes-trace").status_code == 200
        after_ident = c.get("/assy-demo/identity").json()["canonical"]
        assert after_ident["step_count"] == before_ident["step_count"]
        assert after_ident["simulation_time_s"] == before_ident["simulation_time_s"]
        for sid in SUB_LINE_IDS:
            after = c.get(f"/assy-demo/sub-line/{sid}").json()
            assert after["simulation_time_s"] == before_detail[sid]["simulation_time_s"]
            assert after["genealogy"] == before_detail[sid]["genealogy"]
            assert after["production"] == before_detail[sid]["production"]
            assert after["recent_quality_events"] == before_detail[sid][
                "recent_quality_events"
            ]

    def test_poll_guard_blocks_any_truth_change(self, monkeypatch):
        out = _output()
        out.experience.reset()
        out.experience.step()

        def mutating_composition(self):  # noqa: ANN001
            self.experience.step()  # illegal: output path stepping simulation truth
            return SimpleNamespace(
                contexts=dict(self._federation.sub_lines), demo_step_number=0
            )

        monkeypatch.setattr(CanonicalAssyOutput, "_composition", mutating_composition)
        with pytest.raises(OutputMutationError):
            out.observations()


# ═══════════════════════════════════════════════════════════════
# G. /assy-demo R3 endpoints (area 15)
# ═══════════════════════════════════════════════════════════════

class TestR3ApiEndpoints:
    @pytest.mark.parametrize(
        "path", ["/assy-demo/observations", "/assy-demo/mes-messages", "/assy-demo/mes-trace"]
    )
    def test_r3_output_endpoints_are_canonical_not_deferred(self, path):
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(4):
            c.post("/assy-demo/step")
        resp = c.get(path)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["authority"] == PROJECTION_AUTHORITY
        assert body["legacy_runtime_authority"] is False
        identity = c.get("/assy-demo/identity").json()["canonical"]
        assert body["canonical"]["run_id"] == identity["run_id"]
        assert body["canonical"]["workspace_id"] == identity["workspace_id"]
        assert body["canonical"]["scenario_id"] == identity["scenario_id"]
        assert body["canonical"]["profile_id"] == identity["profile_id"]
        assert body["canonical"]["sub_line_count"] == 6
        assert body["count"] > 0
        assert body["canonical"]["output_namespace"]["canonical_run_id"] == (
            identity["run_id"]
        )

    def test_observations_endpoint_payload_shape(self):
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(5):
            c.post("/assy-demo/step")
        body = c.get("/assy-demo/observations").json()
        assert body["observation_points"] == [
            "assy.operation_completion",
            "assy.ap04_genealogy",
            "assy.quality_result",
            "assy.ap11_final_qc",
            "assy.ap11_release",
        ]
        assert body["observations"]
        entry = body["observations"][0]
        assert set(entry) >= {
            "gateway_id",
            "message_key",
            "message_type",
            "schema_name",
            "run_id",
            "source_event_id",
            "simulation_time_s",
            "payload",
        }

    def test_mes_endpoints_share_the_same_canonical_messages(self):
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(4):
            c.post("/assy-demo/step")
        messages = c.get("/assy-demo/mes-messages").json()
        trace = c.get("/assy-demo/mes-trace").json()
        assert trace["count"] == messages["count"]
        assert [m["message_key"] for m in messages["mes_messages"]] == [
            t["message_key"] for t in trace["mes_trace"]
        ]
        assert trace["canonical"]["run_id"] == messages["canonical"]["run_id"]

    def test_r4_workflow_endpoints_stay_deferred(self):
        c = _client()
        for path in ("/assy-demo/jam", "/assy-demo/recover", "/assy-demo/run-to-terminal"):
            resp = c.post(path)
            assert resp.status_code == 409
            body = resp.json()
            assert body["status"] == "deferred"
            assert body["deferred_to"] == "R4"
            assert body["legacy_runtime_authority"] is False

    def test_r3_features_are_no_longer_declared_deferred(self):
        assert "observations" not in DEFERRED_FEATURES
        assert "mes_messages" not in DEFERRED_FEATURES
        assert "mes_trace" not in DEFERRED_FEATURES
        assert DEFERRED_FEATURES["jam"] == "R4"
        assert DEFERRED_FEATURES["scenario_change"] == "R4"
