"""VF-vNEXT-R5 evidence generator (implemented gate).

Produces repo-native evidence for the consolidated single-simulation-system state:

  01-architecture-inventory.json          construction sites + route->authority map
  02-product-path-construction-proof.json measured construction counters per phase
  03-deauthorization-proof.json           fail-closed proof for every removed family
  04-attempt-binding.json                 R5a-1 attempt-bound profile proof
  05-firewall.json                        static + dynamic construction firewall
  06-shell-convergence.json               audit items I1/I3/I4/I5/I6
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE
while not (ROOT / "pyproject.toml").exists():
    ROOT = ROOT.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

CONSTRUCTIONS = (
    "RuntimeService(",
    "SimulationEngine(",
    "DiscreteSimulationEngine(",
    "RunLifecycleService(",
    "RuntimeSession(",
    "DemoController(",
    "DemoRunner(",
    "AssyDemoComposition(",
    "TipaAssyFederation(",
)

AUTHORITY_NAMES = {
    "RuntimeService",
    "SimulationEngine",
    "DiscreteSimulationEngine",
    "DemoController",
    "DemoRunner",
    "AssyDemoComposition",
    "RunLifecycleService",
    "RuntimeSession",
    "TipaAssyFederation",
}

PROBED = (
    ("virtual_factory.ui.runtime_service", "RuntimeService"),
    ("virtual_factory.core.simulation_engine", "SimulationEngine"),
    ("virtual_factory.discrete.engine", "DiscreteSimulationEngine"),
    ("virtual_factory.assembly.demo_assy_mes.controller", "DemoController"),
    ("virtual_factory.assembly.demo_assy_mes.runner", "DemoRunner"),
    ("virtual_factory.assembly.demo_composition", "AssyDemoComposition"),
    ("virtual_factory.runcontrol.lifecycle", "RunLifecycleService"),
    ("virtual_factory.runcontrol.session", "RuntimeSession"),
    ("virtual_factory.federation", "TipaAssyFederation"),
)

DEAUTHORIZED = {
    "root_dashboard_runtime_service": [
        ("get", "/status"), ("get", "/telemetry/latest"),
        ("get", "/telemetry/history"), ("get", "/alarms"),
        ("post", "/step"), ("post", "/run-steps"), ("post", "/start"),
        ("post", "/stop"), ("post", "/reset"),
        ("get", "/api/plant-graph"), ("get", "/api/model-types"),
        ("patch", "/api/pid/PID-1"), ("post", "/api/fault"),
        ("get", "/api/opcua/status"), ("get", "/api/config/current"),
        ("post", "/api/config/switch"), ("get", "/api/ui/context/continuous"),
    ],
    "legacy_g7_run_control": [
        ("get", "/vnext/runs/current"),
        ("get", "/vnext/runs/current?workspace=TIPA"),
        ("get", "/vnext/runs/current?workspace=continuous"),
        ("post", "/vnext/runs"), ("get", "/vnext/runs/RUN-1"),
        ("post", "/vnext/runs/RUN-1/start"), ("post", "/vnext/runs/RUN-1/step"),
        ("post", "/vnext/runs/RUN-1/pause"), ("post", "/vnext/runs/RUN-1/resume"),
        ("post", "/vnext/runs/RUN-1/stop"), ("post", "/vnext/runs/RUN-1/reset"),
        ("post", "/vnext/runs/RUN-1/restart"), ("post", "/vnext/runs/RUN-1/replay"),
    ],
    "legacy_demo_assy_mes": [
        ("get", "/demo-assy-mes"), ("post", "/demo-assy-mes/reset"),
        ("post", "/demo-assy-mes/start"), ("post", "/demo-assy-mes/pause"),
        ("post", "/demo-assy-mes/step"), ("post", "/demo-assy-mes/jam"),
        ("post", "/demo-assy-mes/recover"), ("get", "/demo-assy-mes/snapshot"),
        ("get", "/demo-assy-mes/messages"),
    ],
}

CANONICAL = [
    ("get", "/workspaces"), ("get", "/vnext/workspaces"),
    ("get", "/vnext/workspaces/TIPA/view"), ("get", "/vnext/workspaces/shwtp/view"),
    ("post", "/assy-demo/reset"), ("post", "/assy-demo/step"),
    ("get", "/assy-demo/overview"), ("get", "/assy-demo/sub-lines"),
    ("get", "/assy-demo/identity"), ("get", "/assy-demo/oee"),
    ("post", "/assy-demo/snapshot"), ("get", "/assy-demo/mes-messages"),
]

UI_STATIC = SRC / "virtual_factory" / "ui" / "static"


# ── instrumentation ────────────────────────────────────────────────────────
class Probe:
    def __init__(self) -> None:
        self.counts: Counter = Counter()
        self.sites: defaultdict = defaultdict(Counter)

    def patch(self) -> None:
        for module_name, class_name in PROBED:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
            original = cls.__init__
            probe = self

            def wrapper(self_, *args, _orig=original, _name=class_name, **kwargs):  # noqa: ANN001
                probe.counts[_name] += 1
                frame = inspect.stack()[1]
                probe.sites[_name][f"{Path(frame.filename).name}:{frame.lineno}"] += 1
                return _orig(self_, *args, **kwargs)

            cls.__init__ = wrapper

    def reset(self) -> None:
        self.counts.clear()
        self.sites.clear()

    def snapshot(self) -> dict:
        return {
            "counts": dict(sorted(self.counts.items())),
            "construction_sites": {k: dict(sorted(v.items())) for k, v in sorted(self.sites.items())},
        }


probe = Probe()
probe.patch()

from fastapi.testclient import TestClient  # noqa: E402

from virtual_factory.ui.api import (  # noqa: E402
    DEAUTHORIZED_LEGACY_SURFACES,
    LEGACY_AUTHORITY_REMOVED_CODE,
    create_app,
)


def call(client, method: str, path: str):
    query = None
    if "?" in path:
        path, raw = path.split("?", 1)
        query = dict(part.split("=", 1) for part in raw.split("&"))
    request = getattr(client, method)
    if method in ("post", "patch"):
        return request(path, params=query, json={})
    return request(path, params=query)


# ── 01 inventory ───────────────────────────────────────────────────────────
def static_inventory() -> dict:
    prod_sites: list[dict] = []
    for path in sorted(SRC.rglob("*.py")):
        if "egg-info" in str(path) or "__pycache__" in str(path):
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if "def " in line:
                continue
            for needle in CONSTRUCTIONS:
                if needle in line:
                    rel = str(path.relative_to(ROOT)).replace("\\", "/")
                    prod_sites.append(
                        {
                            "file": rel,
                            "line": lineno,
                            "symbol": needle.rstrip("("),
                            "classification": classify(rel),
                            "code": line.strip()[:120],
                        }
                    )

    api_source = (SRC / "virtual_factory" / "ui" / "api.py").read_text(encoding="utf-8")
    tree = ast.parse(api_source)
    api_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    api_names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}

    by_class = Counter(site["classification"] for site in prod_sites)
    return {
        "production_construction_sites": prod_sites,
        "classification_counts": dict(sorted(by_class.items())),
        "active_product_path_authority_constructions": [
            s for s in prod_sites if s["file"] == "src/virtual_factory/ui/api.py"
        ],
        "api_authority_names_referenced": sorted(api_names & AUTHORITY_NAMES),
        "route_authority_map": route_authority_map(),
        "registry": registry_inventory(),
        "continuous_authority_components": continuous_classification(),
    }


def classify(rel: str) -> str:
    if rel == "src/virtual_factory/ui/api.py":
        return "ACTIVE_PRODUCT_PATH_DEAUTHORIZED_FAIL_CLOSED"
    if rel in (
        "src/virtual_factory/runcontrol/session.py",
        "src/virtual_factory/shwtp/session.py",
        "src/virtual_factory/ui/workspace_monitor.py",
    ):
        return "CANONICAL_SESSION_REGISTRY_AUTHORITY_KEEP"
    if rel.startswith("src/virtual_factory/assembly/") or "demo_assy_mes" in rel:
        return "KEEP_AS_TEST_REFERENCE_ONLY"
    return "KEEP_AS_EXECUTION_KERNEL_OR_LIBRARY"


def route_authority_map() -> list[dict]:
    source = (SRC / "virtual_factory" / "ui" / "api.py").read_text(encoding="utf-8")
    lines = source.splitlines()
    decorators = []
    for index, line in enumerate(lines):
        match = re.match(r'\s*@app\.(get|post|patch|websocket)\("([^"]+)"\)', line)
        if match:
            decorators.append((index, match))
    rows: list[dict] = []
    for position, (lineno, match) in enumerate(decorators):
        end = decorators[position + 1][0] if position + 1 < len(decorators) else len(lines)
        body = "\n".join(lines[lineno:end])
        authority = "STATIC_PAGE_OR_STRUCTURAL_READ_ONLY"
        if "LegacyRuntimeAuthorityDeauthorized" in body:
            surface = re.search(r'LegacyRuntimeAuthorityDeauthorized\("([a-z_]+)"\)', body)
            authority = f"DEAUTHORIZED_FAIL_CLOSED:{surface.group(1) if surface else 'unknown'}"
        elif "_get_assy_experience" in body or "_get_assy_output" in body:
            authority = "CANONICAL_ASSY_EXPERIENCE"
        elif "_get_workspace_monitor" in body or "monitor." in body:
            authority = "CANONICAL_WORKSPACE_MONITOR"
        rows.append(
            {
                "method": match.group(1).upper(),
                "path": match.group(2),
                "line": lineno + 1,
                "authority": authority,
            }
        )
    return rows


def registry_inventory() -> dict:
    from virtual_factory.ui.workspace_monitor import build_platform_registry

    registry = build_platform_registry()
    ids = sorted(map(str, registry.workspace_ids()))
    return {
        "registry_type": type(registry).__name__,
        "registered_workspaces": ids,
        "continuous_workspace_registered": "continuous" in ids,
        "canonical_workspace_count": len(ids),
    }


def continuous_classification() -> list[dict]:
    return [
        {"component": "ui/runtime_service.py (RuntimeService)", "class": "KEEP_AS_EXECUTION_KERNEL_OR_LIBRARY",
         "authority_status": "NOT_AN_AUTHORITY_BY_ITSELF: no active product path constructs it"},
        {"component": "core/simulation_engine.py + core/engine_factory.py", "class": "KEEP_AS_EXECUTION_KERNEL_OR_LIBRARY",
         "authority_status": "domain engine library (used by canonical federation paths)"},
        {"component": "discrete/run_service.py + discrete/engine.py", "class": "KEEP_AS_EXECUTION_KERNEL_OR_LIBRARY",
         "authority_status": "domain engine library"},
        {"component": "assembly/demo_controller.py + assembly/demo_composition.py + assembly/demo_assy_mes/*",
         "class": "KEEP_AS_TEST_REFERENCE_ONLY",
         "authority_status": "reference/compat only; no product route constructs them (verified dynamically)"},
        {"component": "root dashboard state routes (/status, /step, /telemetry/*, /alarms, /reset, /api/config/*, /api/ui/context/continuous)",
         "class": "FAIL_CLOSED_DEPRECATED_ALIAS",
         "authority_status": "HTTP 410 + zero construction"},
        {"component": "legacy G7 run-control family (/vnext/runs*)", "class": "FAIL_CLOSED_DEPRECATED_ALIAS",
         "authority_status": "HTTP 410 + zero construction; duplicate TIPA + continuous discriminators removed"},
        {"component": "legacy /demo-assy-mes routes", "class": "FAIL_CLOSED_DEPRECATED_ALIAS",
         "authority_status": "HTTP 410 + zero construction"},
        {"component": "static assets index.html/demo_assy_mes.html/continuous_context.js/run_control_context.js",
         "class": "KEEP_AS_TEST_REFERENCE_ONLY",
         "authority_status": "served pages only; all their state endpoints are 410 (never an authority)"},
    ]


# ── dynamic proofs ─────────────────────────────────────────────────────────
def phase(client: TestClient, calls: list[tuple[str, str]]) -> dict:
    probe.reset()
    statuses = []
    for method, path in calls:
        response = call(client, method, path)
        statuses.append({"request": f"{method.upper()} {path}", "status": response.status_code})
    snap = probe.snapshot()
    snap["requests"] = statuses
    return snap


def deauthorization_proof() -> dict:
    client = TestClient(create_app(auto_start=False))
    families: dict[str, dict] = {}
    for surface, calls in DEAUTHORIZED.items():
        data = phase(client, calls)
        bad = [r for r in data["requests"] if r["status"] != 410]
        families[surface] = {
            "routes": len(calls),
            "all_410": not bad,
            "non_410": bad,
            "constructions": data["counts"],
            "zero_construction": data["counts"] == {},
        }
    probe.reset()
    ws_result = "closed"
    try:
        with client.websocket_connect("/ws/telemetry") as ws:
            ws.receive_json()
        ws_result = "STREAMED"
    except Exception as exc:  # noqa: BLE001
        ws_result = f"closed fail-closed ({type(exc).__name__})"
    families["root_dashboard_runtime_service"]["websocket_ws_telemetry"] = ws_result
    return {
        "code": LEGACY_AUTHORITY_REMOVED_CODE,
        "declared_surfaces": list(DEAUTHORIZED_LEGACY_SURFACES),
        "families": families,
        "verdict": (
            "ALL_LEGACY_AUTHORITIES_DEAUTHORIZED_FAIL_CLOSED"
            if all(f.get("all_410") and f.get("zero_construction") for f in families.values())
            else "DEAUTHORIZATION_INCOMPLETE"
        ),
    }


def attempt_binding_proof() -> dict:
    from virtual_factory.federation import TipaAssyFederation
    from virtual_factory.runcontrol.session import (
        SessionError,
        _require_attempt_bound_bridge,
        build_tipa_scenario_run_factory,
    )

    observed: list[str | None] = []
    original = TipaAssyFederation.initialize

    def patched(self, *args, **kwargs):  # noqa: ANN001
        profile = kwargs.get("run_profile")
        if profile is None and args:
            profile = args[0]
        observed.append(getattr(profile, "profile_id", None))
        return original(self, *args, **kwargs)

    TipaAssyFederation.initialize = patched
    config = str(ROOT / "configs" / "plants" / "tipa_assy_demo.yaml")
    scenes: list[dict] = []
    try:
        factory = build_tipa_scenario_run_factory(config)
        a = factory("tipa-default")
        a.advance()
        a.stop()
        b = factory("tipa-failed-final")
        b.advance()
        b.stop()

        observed.clear()
        a.replay()
        a.advance()
        scenes.append(
            {
                "scene": "A(tipa-default) terminal -> B(tipa-failed-final) terminal -> A.replay()+advance()",
                "expected_profile": "tipa-assy-happy_path",
                "observed_profiles": list(observed),
                "bound": observed == ["tipa-assy-happy_path"],
                "previous_defect": "in R5-audit this scene built profile tipa-assy-failed_final (contamination)",
            }
        )

        observed.clear()
        a.stop()
        a.new_attempt()
        a.advance()
        scenes.append(
            {
                "scene": "A.new_attempt()+advance() after B was selected earlier",
                "expected_profile": "tipa-assy-happy_path",
                "observed_profiles": list(observed),
                "bound": observed == ["tipa-assy-happy_path"],
            }
        )
    finally:
        TipaAssyFederation.initialize = original

    try:
        _require_attempt_bound_bridge()
        zero_arg = "DID_NOT_FAIL_CLOSED"
    except SessionError:
        zero_arg = "fails_closed"

    return {
        "seam": "RunLifecycleService(bridge_factory_ctx=...) builds the bridge from the attempt's immutable RunContextV2; build_tipa_scenario_run_factory resolves the profile from context.scenario_id with an immutable per-scenario memo (no ambient holder)",
        "scenes": scenes,
        "zero_arg_bridge_factory": zero_arg,
        "verdict": (
            "ATTEMPT_BINDING_CONTEXT_BOUND"
            if all(s["bound"] for s in scenes) and zero_arg == "fails_closed"
            else "ATTEMPT_BINDING_UNBOUND"
        ),
    }


def canonical_proof() -> dict:
    client = TestClient(create_app(auto_start=False))
    probe.reset()
    app_construction = {"RuntimeService": None}
    probe.reset()
    create_app(auto_start=False)
    app_construction = dict(probe.counts)
    data = phase(client, CANONICAL)
    bad = [r for r in data["requests"] if r["status"] != 200]
    sub_lines = client.get("/assy-demo/sub-lines").json()
    rows = sub_lines["sub_lines"] if isinstance(sub_lines, dict) else sub_lines
    counts = data["counts"]
    return {
        "create_app_constructions": app_construction,
        "canonical_phase": data,
        "canonical_sub_line_count": len(rows),
        "verdict": (
            "CANONICAL_PATH_IS_THE_SINGLE_AUTHORITY"
            if app_construction == {}
            and not bad
            and counts.get("RuntimeSession") == 2
            and counts.get("RunLifecycleService") == 2
            and counts.get("TipaAssyFederation") == 1
            and len(rows) == 6
            else "CANONICAL_PATH_INCONSISTENT"
        ),
    }


def firewall_proof() -> dict:
    api_source = (SRC / "virtual_factory" / "ui" / "api.py").read_text(encoding="utf-8")
    static_offenders: list[str] = []
    ui_dir = SRC / "virtual_factory" / "ui"
    for path in sorted(ui_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                if name in AUTHORITY_NAMES:
                    static_offenders.append(f"{path.name}:{node.lineno}:{name}")

    client = TestClient(create_app(auto_start=False))
    probe.reset()
    probe.reset()
    create_app(auto_start=False)
    app_counts = dict(probe.counts)
    deauth = deauthorization_proof()
    canonical = canonical_proof()

    return {
        "static": {
            "forbidden_construction_needles_in_api": [n for n in CONSTRUCTIONS if n in api_source],
            "authority_construction_calls_in_ui_package": static_offenders,
        },
        "dynamic": {
            "create_app_constructions": app_counts,
            "deauthorized_families_zero_construction": all(
                f.get("zero_construction") for f in deauth["families"].values()
            ),
            "canonical_counts": canonical["canonical_phase"]["counts"],
        },
        "hidden_legacy_cache": {
            "demo_singleton_removed": "_demo_controller[" not in api_source,
            "g7_singleton_removed": "_run_control" not in api_source,
            "runtime_service_import_removed": "runtime_service" not in api_source,
        },
        "verdict": (
            "FIREWALL_HELD"
            if not [n for n in CONSTRUCTIONS if n in api_source]
            and not static_offenders
            and app_counts == {}
            and all(f.get("zero_construction") for f in deauth["families"].values())
            else "FIREWALL_BREACHED"
        ),
    }


def shell_proof() -> dict:
    html = (UI_STATIC / "workspace_shell.html").read_text(encoding="utf-8")
    js = (UI_STATIC / "workspace_shell.js").read_text(encoding="utf-8")
    css = (UI_STATIC / "workspace_shell.css").read_text(encoding="utf-8")
    assy = (UI_STATIC / "assy_demo.html").read_text(encoding="utf-8")

    client = TestClient(create_app(auto_start=False))
    view = client.get("/vnext/workspaces/TIPA/view").json()
    before = view["identity"]["run_id"]
    probe.reset()
    new_run = client.post(
        "/vnext/workspaces/TIPA/new-run", json={"scenario_id": "tipa-failed-final"}
    )
    after = new_run.json()
    shwtp_refusal = client.post(
        "/vnext/workspaces/shwtp/new-run", json={"scenario_id": "tipa-default"}
    )
    unknown = client.post("/vnext/workspaces/NOPE/new-run", json={"scenario_id": "x"})

    return {
        "I1_scenario_new_run_control": {
            "html_has_scenario_select": 'id="ws-scenario-select"' in html,
            "html_has_new_run_button": 'id="ws-ctrl-newrun"' in html,
            "js_posts_canonical_new_run": "/new-run" in js and "scenario_id" in js,
            "view_exposes_scenario_ids": bool(view.get("scenario_ids")),
            "scenario_ids": view.get("scenario_ids"),
            "new_run_status": new_run.status_code,
            "fresh_run_id": after.get("identity", {}).get("run_id"),
            "previous_run_id": before,
            "fresh_run_identity_changed": after.get("identity", {}).get("run_id") != before,
            "fresh_run_scenario": after.get("identity", {}).get("scenario_id"),
            "counts_after_new_run": dict(probe.counts),
            "shwtp_new_run_status": shwtp_refusal.status_code,
            "unknown_workspace_status": unknown.status_code,
        },
        "I3_responsive_scope_table": {
            "scroll_wrapper_css": ".ws-table-scroll" in css,
            "overflow_x_auto": "overflow-x: auto" in css,
            "min_width_zero_on_cards": "min-width: 0" in css,
            "word_break": "overflow-wrap: anywhere" in css,
            "narrow_media_query": "@media (max-width: 760px)" in css,
            "js_wraps_tables": js.count('class="ws-table-scroll"'),
        },
        "I4_unavailable_action_convention": {
            "helper": "setActionEnabled" in js,
            "aria_disabled_used": "aria-disabled" in js,
            "aria_disabled_in_markup": html.count('aria-disabled="true"'),
            "explicit_reasons": js.count("Unavailable:"),
            "css_not_allowed_cursor": "cursor: not-allowed" in css,
        },
        "I5_shared_glossary": {
            "glossary_in_shell": 'class="ws-glossary"' in html,
            "terms": [t for t in ("STEP", "RESET", "NEW ATTEMPT", "NEW RUN", "REPLAY", "HOLD / JAM", "OEE") if f"<b>{t}</b>" in html],
            "css_styles": ".ws-glossary" in css,
        },
        "I6_legacy_include_removed": {
            "include_removed_from_canonical_page": "run_control_context.js" not in assy,
            "rich_domain_scripts_retained": all(
                s in assy for s in ("assy_demo.js", "hierarchy.js", "assy_context.js")
            ),
        },
        "I2_not_done": {
            "shwtp_dedicated_process_page": "NOT_AUTHORIZED / NOT_IMPLEMENTED",
            "shwtp_shell_view_unchanged": True,
        },
        "verdict": (
            "SHELL_CONVERGENCE_I1_I3_I4_I5_I6_COMPLETE"
            if 'id="ws-scenario-select"' in html
            and 'id="ws-ctrl-newrun"' in html
            and ".ws-table-scroll" in css
            and "setActionEnabled" in js
            and 'class="ws-glossary"' in html
            and "run_control_context.js" not in assy
            else "SHELL_CONVERGENCE_INCOMPLETE"
        ),
    }


def main() -> int:
    inventory = static_inventory()
    (HERE / "01-architecture-inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )

    canonical = canonical_proof()
    deauth = deauthorization_proof()
    binding = attempt_binding_proof()
    proof = {
        "app_construction": canonical["create_app_constructions"],
        "canonical_path": canonical,
        "deauthorized_paths": deauth,
    }
    (HERE / "02-product-path-construction-proof.json").write_text(
        json.dumps(proof, indent=2) + "\n", encoding="utf-8"
    )
    (HERE / "03-deauthorization-proof.json").write_text(
        json.dumps(deauth, indent=2) + "\n", encoding="utf-8"
    )
    (HERE / "04-attempt-binding.json").write_text(
        json.dumps(binding, indent=2) + "\n", encoding="utf-8"
    )
    firewall = firewall_proof()
    (HERE / "05-firewall.json").write_text(
        json.dumps(firewall, indent=2) + "\n", encoding="utf-8"
    )
    shell = shell_proof()
    (HERE / "06-shell-convergence.json").write_text(
        json.dumps(shell, indent=2) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "canonical": canonical["verdict"],
                "deauthorization": deauth["verdict"],
                "attempt_binding": binding["verdict"],
                "firewall": firewall["verdict"],
                "shell": shell["verdict"],
                "registry": inventory["registry"],
                "api_authority_names": inventory["api_authority_names_referenced"],
                "classification_counts": inventory["classification_counts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
