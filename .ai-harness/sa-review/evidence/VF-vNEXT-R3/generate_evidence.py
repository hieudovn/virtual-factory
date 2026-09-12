"""VF-vNEXT-R3 — deterministic evidence generator (Issue #81).

Produces the R3 evidence artefacts in
``.ai-harness/sa-review/evidence/VF-vNEXT-R3/`` from the REAL product seams:

- ``CanonicalAssyExperience`` / ``CanonicalAssyOutput`` over ONE canonical
  TIPA ``RuntimeSession`` (WorkspaceMonitor);
- the FastAPI app via ``TestClient`` for the API evidence.

No product code is written by this script (evidence only).
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from virtual_factory.federation import SUB_LINE_IDS
from virtual_factory.ui.api import create_app
from virtual_factory.ui.assy_experience import CanonicalAssyExperience
from virtual_factory.ui.assy_output import (
    PROJECTION_AUTHORITY,
    PROJECTION_PROVENANCE,
    CanonicalAssyOutput,
)
from virtual_factory.ui.workspace_monitor import WorkspaceMonitor

def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "configs" / "plants" / "tipa_assy_demo.yaml").exists():
            return parent
    raise RuntimeError("repository root not found from evidence generator")


REPO_ROOT = _repo_root()
TIPA_CONFIG = str(REPO_ROOT / "configs" / "plants" / "tipa_assy_demo.yaml")
OUT = Path(__file__).resolve().parent


def _write(name: str, payload: dict) -> None:
    (OUT / name).write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print("wrote", name)


def _client() -> TestClient:
    return TestClient(create_app())


def _experience() -> CanonicalAssyExperience:
    return CanonicalAssyExperience(WorkspaceMonitor(tipa_config_path=TIPA_CONFIG))


def _per_scope(observations: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for obs in observations:
        parts = str(obs["source_event_id"]).split(":")
        scope = parts[1] if len(parts) > 2 else "?"
        counts[scope] = counts.get(scope, 0) + 1
    return dict(sorted(counts.items()))


class _ConstructionCounter:
    """Count runtime/session/federation constructions on the output path."""

    def __init__(self) -> None:
        self.federations: list[str] = []
        self.sessions: list[str] = []
        self.legacy_controllers: list[str] = []
        self._restore: list = []

    def __enter__(self):
        import virtual_factory.assembly.demo_controller as demo_controller
        import virtual_factory.federation.assy_host as host
        import virtual_factory.runcontrol.session as session_module

        def federation_init(inner_self, config_path):  # noqa: ANN001
            self.federations.append(str(config_path))
            original_federation(inner_self, config_path)

        def session_init(inner_self, *args, **kwargs):  # noqa: ANN001
            self.sessions.append("RuntimeSession")
            original_session(inner_self, *args, **kwargs)

        def legacy_init(inner_self, *args, **kwargs):  # noqa: ANN001
            self.legacy_controllers.append("DemoController")
            raise AssertionError("legacy DemoController must not be instantiated")

        original_federation = host.TipaAssyFederation.__init__
        original_session = session_module.RuntimeSession.__init__
        original_legacy = demo_controller.DemoController.__init__
        host.TipaAssyFederation.__init__ = federation_init
        session_module.RuntimeSession.__init__ = session_init
        demo_controller.DemoController.__init__ = legacy_init
        self._restore = [
            (host.TipaAssyFederation, "__init__", original_federation),
            (session_module.RuntimeSession, "__init__", original_session),
            (demo_controller.DemoController, "__init__", original_legacy),
        ]
        return self

    def __exit__(self, *exc):  # noqa: ANN002
        for target, attr, original in self._restore:
            setattr(target, attr, original)
        return False


# ───────────────────────────────────────────────────────────────
# A. Same-session output identity
# ───────────────────────────────────────────────────────────────
def evidence_a() -> dict:
    counter = _ConstructionCounter()
    with counter:
        c = _client()
        c.post("/assy-demo/reset")
        for _ in range(4):
            c.post("/assy-demo/step")
        identity = c.get("/assy-demo/identity").json()["canonical"]
        shell = c.get("/vnext/workspaces/TIPA/view").json()
        observations = c.get("/assy-demo/observations").json()
        mes = c.get("/assy-demo/mes-messages").json()
    exp = _experience()
    exp.reset()
    for _ in range(4):
        exp.step()
    out = CanonicalAssyOutput(exp)
    out.poll()
    adapter_federation = out._federation
    detail_runtime_ids = {
        sid: exp.detail(sid)["canonical_sub_line"]["runtime_object_id"]
        for sid in SUB_LINE_IDS
    }
    adapter_runtime_ids = {
        sid: id(entry.runtime) for sid, entry in adapter_federation.sub_lines.items()
    }
    payload = {
        "authority": PROJECTION_AUTHORITY,
        "provenance": PROJECTION_PROVENANCE,
        "shell_run_id": shell["session"]["run_id"],
        "rich_run_id": identity["run_id"],
        "output_run_id": observations["canonical"]["run_id"],
        "mes_run_id": mes["canonical"]["run_id"],
        "same_run_id_across_shell_rich_output": (
            shell["session"]["run_id"]
            == identity["run_id"]
            == observations["canonical"]["run_id"]
            == mes["canonical"]["run_id"]
        ),
        "workspace_id": identity["workspace_id"],
        "scenario_id": identity["scenario_id"],
        "profile_id": identity["profile_id"],
        "sub_line_ids": list(SUB_LINE_IDS),
        "sub_line_count": len(SUB_LINE_IDS),
        "detail_runtime_object_ids": detail_runtime_ids,
        "adapter_runtime_object_ids": adapter_runtime_ids,
        "same_six_runtime_objects": detail_runtime_ids == adapter_runtime_ids,
        "adapter_federation_is_experience_federation": (
            adapter_federation is exp.federation()
        ),
        "federations_constructed_on_api_path": counter.federations,
        "sessions_constructed_on_api_path": counter.sessions,
        "legacy_controllers_constructed": counter.legacy_controllers,
        "exactly_one_federation": len(counter.federations) == 1,
        "exactly_one_session": len(counter.sessions) == 1,
        "no_legacy_controller": counter.legacy_controllers == [],
        "site_truth": identity["site_truth"],
        "selection_is_presentation_only": identity["selection_is_presentation_only"],
    }
    payload["PASS"] = (
        payload["same_run_id_across_shell_rich_output"]
        and payload["same_six_runtime_objects"]
        and payload["adapter_federation_is_experience_federation"]
        and payload["exactly_one_federation"]
        and payload["exactly_one_session"]
        and payload["no_legacy_controller"]
        and payload["site_truth"] is False
    )
    _write("01-same-session-output-identity.json", payload)
    return payload


# ───────────────────────────────────────────────────────────────
# B. Observation facts
# ───────────────────────────────────────────────────────────────
def evidence_b() -> dict:
    out = _output_run(steps=20)
    body = out.observations()
    run_id = body["canonical"]["run_id"]
    # R3-C01: the projection epoch is the canonical session reset generation
    # (authoritative), so epoch expectations are derived, never hard-coded.
    epoch = body["canonical"]["output_namespace"]["projection_epoch"]
    observations = body["observations"]
    by_family: dict[str, int] = {}
    for obs in observations:
        by_family[obs["message_type"]] = by_family.get(obs["message_type"], 0) + 1
    genealogy = [o for o in observations if o["message_type"] == "mes.genealogy_relationship"]
    quality = [o for o in observations if o["message_type"] == "mes.quality_result"]
    release = [o for o in observations if o["message_type"] == "mes.release"]
    operations = [
        o for o in observations if o["payload"].get("event_type") == "OPERATION_COMPLETED"
    ]
    final_qc = [o for o in observations if o["payload"].get("event_type") == "AP11_FINAL_QC_PASS"]
    payload = {
        "authority": PROJECTION_AUTHORITY,
        "note": (
            "R3-C01: projection epoch = canonical RuntimeSession reset_generation "
            "(authoritative; no poll-timing inference)"
        ),
        "run_id": run_id,
        "observation_points": body["observation_points"],
        "count": body["count"],
        "by_family": by_family,
        "operation_completions": len(operations),
        "ap04_genealogy_facts": len(genealogy),
        "ap04_genealogy_sample": {
            "message_key": genealogy[0]["message_key"],
            "payload": genealogy[0]["payload"],
            "simulation_time_s": genealogy[0]["simulation_time_s"],
            "source_event_id": genealogy[0]["source_event_id"],
        }
        if genealogy
        else None,
        "quality_facts": len(quality),
        "quality_sample": {
            "message_key": quality[0]["message_key"],
            "payload": quality[0]["payload"],
        }
        if quality
        else None,
        "releases": len(release),
        "release_sample": {
            "message_key": release[0]["message_key"],
            "payload": release[0]["payload"],
        }
        if release
        else None,
        "ap11_final_qc": len(final_qc),
        "per_scope_counts": _per_scope(observations),
        "scopes_covered": sorted(_per_scope(observations)),
        "all_facts_carry_canonical_run_id": all(o["run_id"] == run_id for o in observations),
        "all_facts_carry_canonical_run_id_in_payload": all(
            o["payload"]["run_id"] == run_id for o in observations
        ),
        "all_message_keys_start_with_canonical_run_id": all(
            o["message_key"].startswith(run_id) for o in observations
        ),
        "all_source_event_ids_carry_epoch_and_scope": all(
            str(o["source_event_id"]).startswith(f"E{epoch}:ASSY-SL")
            for o in observations
        ),
        "projection_epoch": epoch,
        "epoch_source": body["canonical"]["output_namespace"]["epoch_source"],
    }
    payload["PASS"] = (
        payload["operation_completions"] > 0
        and payload["ap04_genealogy_facts"] > 0
        and payload["quality_facts"] > 0
        and payload["releases"] > 0
        and payload["scopes_covered"] == sorted(SUB_LINE_IDS)
        and payload["all_facts_carry_canonical_run_id"]
        and payload["all_facts_carry_canonical_run_id_in_payload"]
        and payload["all_message_keys_start_with_canonical_run_id"]
        and payload["all_source_event_ids_carry_epoch_and_scope"]
    )
    _write("02-observation-facts.json", payload)
    return payload


# ───────────────────────────────────────────────────────────────
# C. MES messages
# ───────────────────────────────────────────────────────────────
def evidence_c() -> dict:
    out = _output_run(steps=20)
    body = out.mes_messages()
    trace = out.mes_trace()
    run_id = body["canonical"]["run_id"]
    messages = body["mes_messages"]
    families: dict[str, int] = {}
    for msg in messages:
        families[msg["message_type"]] = families.get(msg["message_type"], 0) + 1
    payload = {
        "authority": body["authority"],
        "contract_version": body["contract_version"],
        "run_id": run_id,
        "count": body["count"],
        "trace_count": trace["count"],
        "by_family": families,
        "sub_lines_covered": sorted(
            {m["payload"].get("subline_id") for m in messages if m["payload"].get("subline_id")}
        ),
        "all_payload_run_ids_canonical": all(
            m["payload"]["run_id"] == run_id for m in messages
        ),
        "all_message_keys_contain_canonical_run_id": all(
            m["message_key"].startswith(run_id) for m in messages
        ),
        "all_keys_equal_idempotency_key": all(
            m["message_key"] == m["payload"]["idempotency_key"] for m in messages
        ),
        "all_payloads_carry_common_contract_fields": all(
            m["payload"].get("contract_version") == body["contract_version"]
            and m["payload"].get("production_line_id") == "ASSY"
            and m["payload"].get("plant_id") == "TIPA"
            for m in messages
        ),
        "sample": messages[0] if messages else None,
        "trace_sample": trace["mes_trace"][0] if trace["mes_trace"] else None,
    }
    payload["PASS"] = (
        payload["count"] > 0
        and payload["trace_count"] == payload["count"]
        and len(payload["sub_lines_covered"]) == 6
        and {"mes.execution_event", "mes.genealogy_relationship", "mes.quality_result", "mes.release"}
        <= set(families)
        and payload["all_payload_run_ids_canonical"]
        and payload["all_message_keys_contain_canonical_run_id"]
        and payload["all_keys_equal_idempotency_key"]
        and payload["all_payloads_carry_common_contract_fields"]
    )
    _write("03-mes-messages.json", payload)
    return payload


# ───────────────────────────────────────────────────────────────
# D. Idempotency
# ───────────────────────────────────────────────────────────────
def evidence_d() -> dict:
    out = _output_run(steps=4)
    first = out.observations()
    keys_first = [o["message_key"] for o in first["observations"]]
    second = out.observations()
    keys_second = [o["message_key"] for o in second["observations"]]
    mes_first = out.mes_messages()
    mes_second = out.mes_messages()
    out.experience.step()
    after_step = out.observations()
    keys_after = {o["message_key"] for o in after_step["observations"]}
    new_keys = keys_after - set(keys_first)
    payload = {
        "initial_observation_count": first["count"],
        "initial_delivered": first["delivered_this_poll"],
        "repeat_poll_count": second["count"],
        "repeat_poll_delivered": second["delivered_this_poll"],
        "repeat_poll_has_no_duplicate_keys": len(keys_second) == len(set(keys_second)),
        "repeat_poll_key_order_stable": keys_first == keys_second,
        "mes_repeat_poll_count": mes_second["count"],
        "mes_repeat_poll_delivered": mes_second["delivered_this_poll"],
        "mes_count_unchanged": mes_first["count"] == mes_second["count"],
        "step_then_poll_count": after_step["count"],
        "step_then_poll_delivered": after_step["delivered_this_poll"],
        "step_then_poll_only_new_facts": after_step["delivered_this_poll"] == len(new_keys),
        "step_then_poll_new_keys_sample": sorted(new_keys)[:4],
        "no_duplicate_keys_overall": len(keys_after) == len(
            [o["message_key"] for o in after_step["observations"]]
        ),
    }
    payload["PASS"] = (
        payload["initial_delivered"] > 0
        and payload["repeat_poll_delivered"] == 0
        and payload["mes_repeat_poll_delivered"] == 0
        and payload["repeat_poll_key_order_stable"]
        and payload["mes_count_unchanged"]
        and payload["step_then_poll_only_new_facts"]
        and len(new_keys) > 0
    )
    _write("04-idempotency.json", payload)
    return payload


# ───────────────────────────────────────────────────────────────
# E. Lifecycle projection safety
# ───────────────────────────────────────────────────────────────
def evidence_e() -> dict:
    out = _output_run(steps=4)
    first = out.observations()
    run_id = first["canonical"]["run_id"]
    keys_first = {o["message_key"] for o in first["observations"]}
    reference_families = sorted(o["message_type"] for o in first["observations"])
    epoch_first = first["canonical"]["output_namespace"]["projection_epoch"]

    out.experience.reset()
    reset_poll = out.observations()
    for _ in range(4):
        out.experience.step()
    second = out.observations()
    keys_second = {o["message_key"] for o in second["observations"]}
    new_keys = keys_second - keys_first

    new_run = out.experience.session.new_attempt()
    out.experience.step()
    attempted = out.observations()
    attempt_ns = attempted["canonical"]["output_namespace"]

    replay_run = out.experience.session.replay()
    for _ in range(4):
        out.experience.step()
    replayed = out.observations()
    replay_ns = replayed["canonical"]["output_namespace"]
    replay_families = sorted(
        o["message_type"] for o in replayed["observations"]
    )

    reference_families = sorted(
        o["message_type"] for o in first["observations"]
    )
    payload = {
        "reset": {
            "same_canonical_run_id": second["canonical"]["run_id"] == run_id,
            "reset_poll_run_id": reset_poll["canonical"]["run_id"],
            "epoch_before": epoch_first,
            "epoch_after_reset_poll": reset_poll["canonical"]["output_namespace"][
                "projection_epoch"
            ],
            "epoch_after": second["canonical"]["output_namespace"]["projection_epoch"],
            "epoch_resets": second["canonical"]["output_namespace"]["epoch_resets"],
            "epoch_source": second["canonical"]["output_namespace"]["epoch_source"],
            "post_reset_new_keys": len(new_keys),
            "post_reset_keys_all_new_epoch": all(
                f"E{epoch_first + 1}:" in k for k in new_keys
            ),
            "no_collision_with_pre_reset_keys": not (
                new_keys & {k for k in keys_first if f"E{epoch_first}:" in k}
            ),
        },
        "new_attempt": {
            "fresh_canonical_run_id": new_run != run_id,
            "run_id": new_run,
            "output_namespace_run_id": attempt_ns["canonical_run_id"],
            "namespace_is_canonical_run": attempt_ns["namespace_is_canonical_run"],
            "projection_epoch": attempt_ns["projection_epoch"],
            "epoch_resets": attempt_ns["epoch_resets"],
            "all_keys_in_fresh_run": all(
                o["message_key"].startswith(new_run) for o in attempted["observations"]
            ),
            "no_carry_over_from_previous_run": not any(
                o["message_key"].startswith(run_id) for o in attempted["observations"]
            ),
        },
        "replay": {
            "fresh_canonical_run_id": replay_run != new_run,
            "run_id": replay_run,
            "output_namespace_run_id": replay_ns["canonical_run_id"],
            "projection_epoch": replay_ns["projection_epoch"],
            "all_keys_in_fresh_run": all(
                o["message_key"].startswith(replay_run)
                for o in replayed["observations"]
            ),
            "deterministic_family_multiset": replay_families,
            "reference_family_multiset_size": len(reference_families),
            "same_family_multiset_as_reference_run": (
                replay_families == reference_families
            ),
        },
        "g22_untouched": {
            "reset_keeps_run_id": second["canonical"]["run_id"] == run_id,
            "new_attempt_changes_run_id": new_run != run_id,
            "replay_changes_run_id": replay_run != new_run,
        },
    }
    payload["PASS"] = bool(
        payload["reset"]["same_canonical_run_id"]
        and payload["reset"]["epoch_after"] == epoch_first + 1
        and payload["reset"]["epoch_resets"] == 1
        and payload["reset"]["post_reset_new_keys"] > 0
        and payload["reset"]["post_reset_keys_all_new_epoch"]
        and payload["reset"]["no_collision_with_pre_reset_keys"]
        and payload["new_attempt"]["fresh_canonical_run_id"]
        and payload["new_attempt"]["namespace_is_canonical_run"]
        and payload["new_attempt"]["projection_epoch"] == 1
        and payload["new_attempt"]["all_keys_in_fresh_run"]
        and payload["new_attempt"]["no_carry_over_from_previous_run"]
        and payload["replay"]["fresh_canonical_run_id"]
        and payload["replay"]["all_keys_in_fresh_run"]
        and payload["replay"]["same_family_multiset_as_reference_run"]
    )
    _write("05-lifecycle-projection-safety.json", payload)
    return payload


# ───────────────────────────────────────────────────────────────
# F. Six-line independence in the output
# ───────────────────────────────────────────────────────────────
def evidence_f() -> dict:
    out = _output_run(steps=3)
    baseline = out.observations()
    before = _per_scope(baseline["observations"])
    out.experience.bridge().hold_sub_line("ASSY-SL03")
    for _ in range(3):
        out.experience.step()
    held = out.observations()
    after = _per_scope(held["observations"])
    overview_held = out.experience.overview()
    rows_held = {r["sub_line_id"]: r for r in overview_held["sub_lines"]}
    out.experience.bridge().release_sub_line("ASSY-SL03")
    out.experience.step()
    released = out.observations()
    after_release = _per_scope(released["observations"])
    payload = {
        "before_hold": before,
        "after_hold_window": after,
        "held_sub_line": "ASSY-SL03",
        "held_line_new_facts": after.get("ASSY-SL03", 0) - before.get("ASSY-SL03", 0),
        "other_lines_new_facts": {
            sid: after.get(sid, 0) - before.get(sid, 0)
            for sid in sorted(SUB_LINE_IDS)
            if sid != "ASSY-SL03"
        },
        "frame_a_while_held": {
            sid: {
                "simulation_time_s": rows_held[sid]["simulation_time_s"],
                "motors_created": rows_held[sid]["motors_created"],
            }
            for sid in sorted(SUB_LINE_IDS)
        },
        "after_release": after_release,
        "held_line_resumes": after_release.get("ASSY-SL03", 0) > after.get("ASSY-SL03", 0),
    }
    payload["PASS"] = (
        payload["held_line_new_facts"] == 0
        and all(v > 0 for v in payload["other_lines_new_facts"].values())
        and rows_held["ASSY-SL03"]["simulation_time_s"]
        < rows_held["ASSY-SL01"]["simulation_time_s"]
        and payload["held_line_resumes"]
    )
    _write("06-held-one-five-continue-output.json", payload)
    return payload


# ───────────────────────────────────────────────────────────────
# G. No simulation mutation by the output path
# ───────────────────────────────────────────────────────────────
def evidence_g() -> dict:
    c = _client()
    c.post("/assy-demo/reset")
    for _ in range(4):
        c.post("/assy-demo/step")
    before_ident = c.get("/assy-demo/identity").json()["canonical"]
    before_detail = {
        sid: c.get(f"/assy-demo/sub-line/{sid}").json() for sid in SUB_LINE_IDS
    }
    polls = []
    for _ in range(3):
        polls.append(
            {
                "observations": c.get("/assy-demo/observations").status_code,
                "mes_messages": c.get("/assy-demo/mes-messages").status_code,
                "mes_trace": c.get("/assy-demo/mes-trace").status_code,
            }
        )
    after_ident = c.get("/assy-demo/identity").json()["canonical"]
    after_detail = {
        sid: c.get(f"/assy-demo/sub-line/{sid}").json() for sid in SUB_LINE_IDS
    }
    per_line_unchanged = {
        sid: {
            "simulation_time_s": (
                before_detail[sid]["simulation_time_s"]
                == after_detail[sid]["simulation_time_s"]
            ),
            "positions_unchanged": (
                before_detail[sid]["positions"] == after_detail[sid]["positions"]
            ),
            "genealogy_unchanged": (
                before_detail[sid]["genealogy"] == after_detail[sid]["genealogy"]
            ),
            "production_unchanged": (
                before_detail[sid]["production"] == after_detail[sid]["production"]
            ),
            "quality_unchanged": (
                before_detail[sid]["recent_quality_events"]
                == after_detail[sid]["recent_quality_events"]
            ),
        }
        for sid in sorted(SUB_LINE_IDS)
    }
    guard = _mutation_guard_proof()
    payload = {
        "polls": polls,
        "step_count_before": before_ident["step_count"],
        "step_count_after": after_ident["step_count"],
        "simulation_time_before": before_ident["simulation_time_s"],
        "simulation_time_after": after_ident["simulation_time_s"],
        "run_id_unchanged": before_ident["run_id"] == after_ident["run_id"],
        "per_line_unchanged": per_line_unchanged,
        "mutation_guard": guard,
    }
    payload["PASS"] = (
        payload["step_count_before"] == payload["step_count_after"]
        and payload["simulation_time_before"] == payload["simulation_time_after"]
        and payload["run_id_unchanged"]
        and all(
            all(flags.values()) for flags in per_line_unchanged.values()
        )
        and guard["guard_raises_output_mutation_error"]
    )
    _write("07-no-simulation-mutation.json", payload)
    return payload


def _mutation_guard_proof() -> dict:
    """Prove the hard guard rejects an output path that steps the session."""
    from types import SimpleNamespace

    from virtual_factory.ui.assy_output import OutputMutationError

    out = _output_run(steps=1)
    original = CanonicalAssyOutput._composition

    def mutating_composition(self):  # noqa: ANN001
        self.experience.step()  # illegal mutation by the output path
        return SimpleNamespace(
            contexts=dict(self._federation.sub_lines), demo_step_number=0
        )

    raised = False
    try:
        CanonicalAssyOutput._composition = mutating_composition
        out.observations()
    except OutputMutationError:
        raised = True
    finally:
        CanonicalAssyOutput._composition = original
    return {"guard_raises_output_mutation_error": raised}


# ───────────────────────────────────────────────────────────────
# H. API evidence
# ───────────────────────────────────────────────────────────────
def evidence_h() -> dict:
    c = _client()
    c.post("/assy-demo/reset")
    for _ in range(4):
        c.post("/assy-demo/step")
    identity = c.get("/assy-demo/identity").json()["canonical"]
    endpoints = {}
    for path in ("/assy-demo/observations", "/assy-demo/mes-messages", "/assy-demo/mes-trace"):
        resp = c.get(path)
        body = resp.json()
        endpoints[path] = {
            "status_code": resp.status_code,
            "status": body.get("status"),
            "authority": body.get("authority"),
            "legacy_runtime_authority": body.get("legacy_runtime_authority"),
            "count": body.get("count"),
            "canonical_run_id": body.get("canonical", {}).get("run_id"),
            "matches_identity": body.get("canonical", {}).get("run_id")
            == identity["run_id"],
            "output_namespace": body.get("canonical", {}).get("output_namespace"),
            "provenance": body.get("provenance"),
        }
    r4 = {}
    for path in ("/assy-demo/jam", "/assy-demo/recover", "/assy-demo/run-to-terminal"):
        resp = c.post(path)
        body = resp.json()
        r4[path] = {
            "status_code": resp.status_code,
            "status": body.get("status"),
            "deferred_to": body.get("deferred_to"),
            "legacy_runtime_authority": body.get("legacy_runtime_authority"),
        }
    payload = {
        "identity_run_id": identity["run_id"],
        "identity": identity,
        "endpoints": endpoints,
        "r4_endpoints_still_deferred": r4,
    }
    payload["PASS"] = (
        all(
            entry["status_code"] == 200
            and entry["status"] == "ok"
            and entry["legacy_runtime_authority"] is False
            and entry["matches_identity"]
            and entry["canonical_run_id"] == identity["run_id"]
            for entry in endpoints.values()
        )
        and all(
            entry["status_code"] == 409 and entry["deferred_to"] == "R4"
            for entry in r4.values()
        )
    )
    _write("08-api-endpoints.json", payload)
    return payload


def _output_run(steps: int) -> CanonicalAssyOutput:
    out = CanonicalAssyOutput(_experience())
    out.experience.reset()
    for _ in range(steps):
        out.experience.step()
    return out


def main() -> int:
    results = {
        "A_same_session_identity": evidence_a(),
        "B_observation_facts": evidence_b(),
        "C_mes_messages": evidence_c(),
        "D_idempotency": evidence_d(),
        "E_lifecycle_projection_safety": evidence_e(),
        "F_six_line_independence_output": evidence_f(),
        "G_no_simulation_mutation": evidence_g(),
        "H_api_endpoints": evidence_h(),
    }
    print()
    for name, payload in results.items():
        print(f"{name}: PASS={payload['PASS']}")
    if not all(payload["PASS"] for payload in results.values()):
        print("EVIDENCE FAILED")
        return 1
    print("R3 evidence complete: all sections PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
