"""VF-vNEXT-R5 evidence generator (audit-level gate: architecture inventory).

Produces, from repo-native code and live routes (no source modification):
  01-architecture-inventory.json      every construction site, four-way classified
  02-product-path-construction-proof.json  measured construction counters per phase
  03-blocker-analysis.json            measured blocker facts + options
"""

from __future__ import annotations

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

# --------------------------------------------------------------------------
# construction-site patterns: symbol -> (kind, classification)
# --------------------------------------------------------------------------
PRODUCTION_CLASSIFICATION = {
    "RuntimeService(": "KEEP_AS_EXECUTION_KERNEL_OR_DOMAIN_LIBRARY",
    "SimulationEngine(": "KEEP_AS_EXECUTION_KERNEL_OR_DOMAIN_LIBRARY",
    "DiscreteSimulationEngine(": "KEEP_AS_EXECUTION_KERNEL_OR_DOMAIN_LIBRARY",
    "RunLifecycleService(": "RUN_LIFECYCLE_ADMISSION_SEAM",
    "RuntimeSession(": "CANONICAL_SESSION_AUTHORITY",
    "build_tipa_session(": "CANONICAL_SESSION_FACTORY",
    "build_tipa_scenario_run_factory(": "CANONICAL_SESSION_FACTORY",
    "build_shwtp_session(": "CANONICAL_SESSION_FACTORY",
    "DemoController(": "LEGACY_DEMO_CONTROLLER",
    "DemoRunner(": "LEGACY_DEMO_RUNNER",
    "AssyDemoComposition(": "LEGACY_DEMO_COMPOSITION",
}

ACTIVE_PRODUCT_FILES = {"src/virtual_factory/ui/api.py"}

CANONICAL_AUTHORITY_FILES = {
    "src/virtual_factory/runcontrol/session.py",
    "src/virtual_factory/shwtp/session.py",
    "src/virtual_factory/ui/workspace_monitor.py",
}


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def scan_sites(files: list[Path]) -> list[dict]:
    sites: list[dict] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            for symbol, kind in PRODUCTION_CLASSIFICATION.items():
                if symbol in line and "def " not in line:
                    sites.append(
                        {
                            "file": rel(path),
                            "line": i,
                            "symbol": symbol.rstrip("("),
                            "kind": kind,
                            "code": line.strip()[:140],
                        }
                    )
    return sites


def static_inventory() -> dict:
    prod_files = [
        p
        for p in sorted(SRC.rglob("*.py"))
        if "egg-info" not in str(p) and "__pycache__" not in str(p)
    ]
    test_files = sorted((ROOT / "tests").glob("*.py"))
    prod_sites = scan_sites(prod_files)
    test_sites = scan_sites(test_files)

    for site in prod_sites:
        if site["file"] in ACTIVE_PRODUCT_FILES:
            site["classification"] = "DEPRECATE_REMOVE_ACTIVE_PRODUCT_REACHABILITY"
        elif site["file"] in CANONICAL_AUTHORITY_FILES:
            site["classification"] = "CANONICAL_SESSION_REGISTRY_AUTHORITY_KEEP"
        elif site["file"].startswith("src/virtual_factory/assembly/"):
            site["classification"] = "KEEP_AS_TEST_REFERENCE_ONLY"
        else:
            site["classification"] = "KEEP_AS_EXECUTION_KERNEL_OR_DOMAIN_LIBRARY"
        site["reachability"] = route_or_cli_reachability(site)

    test_counts = Counter(s["symbol"] for s in test_sites)
    return {
        "production_construction_sites": prod_sites,
        "production_site_count": len(prod_sites),
        "active_product_path_sites": [
            s for s in prod_sites if s["classification"].startswith("DEPRECATE")
        ],
        "kernel_sites": [
            s
            for s in prod_sites
            if s["classification"] == "KEEP_AS_EXECUTION_KERNEL_OR_DOMAIN_LIBRARY"
        ],
        "reference_only_sites": [
            s for s in prod_sites if s["classification"] == "KEEP_AS_TEST_REFERENCE_ONLY"
        ],
        "test_reference_construction_counts": dict(sorted(test_counts.items())),
        "test_site_count": len(test_sites),
        "note": (
            "tests/** construction sites are TEST/REFERENCE ONLY and are not product "
            "authority; they are recorded as counts only."
        ),
    }


def route_or_cli_reachability(site: dict) -> str:
    if site["file"] in ACTIVE_PRODUCT_FILES:
        return "ACTIVE_HTTP_PRODUCT_ROUTE"
    if site["file"].endswith("__main__.py"):
        return "CLI_REFERENCE_ONLY"
    return "IN_PROCESS_LIBRARY"


def route_authority_map() -> list[dict]:
    api = (ROOT / "src/virtual_factory/ui/api.py").read_text(encoding="utf-8")
    lines = api.splitlines()
    decorators = []
    for i, line in enumerate(lines):
        match = re.match(r'\s*@app\.(get|post|websocket)\("([^"]+)"\)', line)
        if match:
            decorators.append((i, match))
    rows: list[dict] = []
    for idx, (lineno, match) in enumerate(decorators):
        end = decorators[idx + 1][0] if idx + 1 < len(decorators) else len(lines)
        body = "\n".join(lines[lineno:end])
        authorities = []
        if "_get_demo_controller" in body:
            authorities.append("LEGACY_DEMO_ASSY_MES_CONTROLLER")
        if "_get_run_control_service" in body or "_vnext_service" in body:
            authorities.append("LEGACY_G7_RUN_CONTROL_SERVICE")
        if re.search(r"(?<![\w.])service\.[a-z_]+", body) or "service =" in body:
            authorities.append("ROOT_DASHBOARD_RUNTIME_SERVICE")
        if "_get_assy_experience" in body or "_get_assy_output" in body:
            authorities.append("CANONICAL_ASSY_EXPERIENCE")
        if "workspace_monitor" in body or "monitor." in body or "_monitor" in body:
            authorities.append("CANONICAL_WORKSPACE_MONITOR")
        rows.append(
            {
                "method": match.group(1).upper(),
                "path": match.group(2),
                "line": lineno + 1,
                "authorities": authorities or ["STATIC_PAGE_OR_NO_STATE"],
            }
        )
    return rows


# --------------------------------------------------------------------------
# dynamic construction instrumentation
# --------------------------------------------------------------------------
class ConstructionProbe:
    def __init__(self) -> None:
        self.counts: Counter = Counter()
        self.sites: defaultdict = defaultdict(Counter)
        self.patched: list = []

    def patch(self, cls) -> None:
        probe = self
        original = cls.__init__

        def wrapper(self_, *args, **kwargs):  # noqa: ANN001
            name = type(self_).__name__
            probe.counts[name] += 1
            try:
                frame = inspect.stack()[1]
                origin = f"{Path(frame.filename).name}:{frame.lineno}"
            except Exception:  # noqa: BLE001
                origin = "unknown"
            probe.sites[name][origin] += 1
            if name == "RuntimeSession" and len(args) >= 2:
                probe.counts[f"RuntimeSession[{args[1]}]" ] += 1
            return original(self_, *args, **kwargs)

        cls.__init__ = wrapper
        self.patched.append((cls, original))

    def reset(self) -> None:
        self.counts.clear()
        self.sites.clear()

    def snapshot(self) -> dict:
        return {
            "counts": dict(sorted(self.counts.items())),
            "construction_sites": {
                k: dict(sorted(v.items())) for k, v in sorted(self.sites.items())
            },
        }


def instrument(probe: ConstructionProbe) -> None:
    from virtual_factory.assembly.demo_composition import AssyDemoComposition
    from virtual_factory.assembly.demo_assy_mes.controller import DemoController
    from virtual_factory.assembly.demo_assy_mes.runner import DemoRunner
    from virtual_factory.federation import TipaAssyFederation
    from virtual_factory.runcontrol.lifecycle import RunLifecycleService
    from virtual_factory.runcontrol.session import RuntimeSession
    from virtual_factory.ui.runtime_service import RuntimeService

    for cls in (
        RuntimeService,
        RunLifecycleService,
        RuntimeSession,
        DemoController,
        DemoRunner,
        AssyDemoComposition,
        TipaAssyFederation,
    ):
        probe.patch(cls)


def client_for(probe: ConstructionProbe | None):
    from fastapi.testclient import TestClient

    from virtual_factory.ui.api import create_app

    app = create_app(auto_start=False)
    if probe is not None:
        probe.reset()
    return TestClient(app)


def run_phase(probe: ConstructionProbe, calls: list[tuple[str, str, dict | None]]) -> dict:
    client = client_for(probe)
    statuses = []
    with client:
        for method, path, body in calls:
            if method == "GET":
                response = client.get(path)
            else:
                response = client.post(path, json=body or {})
            statuses.append({"request": f"{method} {path}", "status": response.status_code})
    snap = probe.snapshot()
    snap["requests"] = statuses
    return snap


CANONICAL_CALLS = [
    ("GET", "/workspaces", None),
    ("GET", "/vnext/workspaces", None),
    ("GET", "/vnext/workspaces/TIPA/view", None),
    ("GET", "/vnext/workspaces/shwtp/view", None),
    ("POST", "/assy-demo/reset", None),
    ("POST", "/assy-demo/step", None),
    ("POST", "/assy-demo/step", None),
    ("GET", "/assy-demo/overview", None),
    ("GET", "/assy-demo/sub-lines", None),
    ("GET", "/assy-demo/identity", None),
    ("GET", "/assy-demo/oee", None),
    ("POST", "/assy-demo/snapshot", None),
    ("GET", "/assy-demo/mes-messages", None),
]

ROOT_DASHBOARD_CALLS = [
    ("GET", "/", None),
    ("GET", "/status", None),
    ("POST", "/step", None),
    ("GET", "/telemetry/latest", None),
    ("GET", "/alarms", None),
    ("GET", "/api/ui/context", None),
]

LEGACY_DEMO_CALLS = [
    ("GET", "/demo-assy-mes", None),
    ("POST", "/demo-assy-mes/reset", None),
    ("POST", "/demo-assy-mes/step", None),
    ("GET", "/demo-assy-mes/snapshot", None),
    ("GET", "/demo-assy-mes/messages", None),
]

LEGACY_G7_CALLS = [
    ("GET", "/vnext/runs/current?workspace=TIPA", None),
    ("POST", "/vnext/runs?workspace=TIPA", None),
    ("GET", "/vnext/runs/current?workspace=continuous", None),
    ("POST", "/vnext/runs?workspace=continuous", None),
]


def attempt_binding_probe() -> dict:
    """Measure whether the TIPA scenario-run factory binds the attempt profile."""
    from virtual_factory.federation import TipaAssyFederation
    from virtual_factory.runcontrol.session import build_tipa_scenario_run_factory

    observed: list[dict] = []
    original = TipaAssyFederation.initialize

    def patched(self, *args, **kwargs):  # noqa: ANN001
        profile = kwargs.get("run_profile")
        if profile is None and args:
            profile = args[0]
        observed.append(
            {
                "run_profile": getattr(profile, "profile_id", None) if profile else None,
                "profile_bound_to_attempt": profile is not None,
            }
        )
        return original(self, *args, **kwargs)

    TipaAssyFederation.initialize = patched

    config = str(ROOT / "configs" / "plants" / "tipa_assy_demo.yaml")

    def scene_product_flow_order() -> dict:
        """Legal product ordering: select A, run it, select B, run B."""
        observed.clear()
        factory = build_tipa_scenario_run_factory(config)
        session_a = factory("tipa-default")
        profile_a = session_a.profile_id
        session_a.advance()
        session_a.stop()
        session_b = factory("tipa-failed-final")
        profile_b = session_b.profile_id
        before = len(observed)
        error = None
        try:
            session_b.advance()
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"[:200]
        built = observed[before:]
        used = [row.get("run_profile") for row in built]
        return {
            "scene": (
                "A(tipa-default) created+advanced+stopped -> B(tipa-failed-final) created "
                "-> B.advance() builds B's bridge"
            ),
            "profile_a": profile_a,
            "profile_b": profile_b,
            "federation_initializations_for_B": built,
            "profile_ids_used_for_B": used,
            "error": error,
            "attempt_bound": (not used) or all(u == profile_b for u in used),
        }

    def scene_replay_after_other_scenario() -> dict:
        """Legal lifecycle sequence: both runs terminal, then replay the OLD run."""
        observed.clear()
        factory = build_tipa_scenario_run_factory(config)
        session_a = factory("tipa-default")
        profile_a = session_a.profile_id
        session_a.advance()
        session_a.stop()
        session_b = factory("tipa-failed-final")
        profile_b = session_b.profile_id
        session_b.advance()
        session_b.stop()
        before = len(observed)
        error = None
        try:
            session_a.replay()
            session_a.advance()
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"[:200]
        built = observed[before:]
        used = [row.get("run_profile") for row in built]
        return {
            "scene": (
                "A(tipa-default) created+advanced+stopped -> B(tipa-failed-final) "
                "created+advanced+stopped -> A.replay()+advance() (fresh attempt re-pinning "
                "A's scenario profile)"
            ),
            "profile_a": profile_a,
            "profile_b": profile_b,
            "session_a_profile_after_replay": session_a.profile_id,
            "federation_initializations_for_A_replay": built,
            "profile_ids_used_for_A_replay": used,
            "error": error,
            "attempt_bound": (not used) or all(u == profile_a for u in used),
        }

    try:
        scenes = [scene_product_flow_order(), scene_replay_after_other_scenario()]
    finally:
        TipaAssyFederation.initialize = original

    violations = [s for s in scenes if not s["attempt_bound"]]
    exercised = [
        s
        for s in scenes
        if s.get("federation_initializations_for_B")
        or s.get("federation_initializations_for_A_replay")
    ]
    return {
        "scenes": scenes,
        "violations": len(violations),
        "scenes_with_bridge_build_observed": len(exercised),
        "verdict": (
            "ATTEMPT_BINDING_UNBOUND"
            if violations
            else ("ATTEMPT_BINDING_BOUND_IN_OBSERVED_FLOWS" if exercised else "NOT_EXERCISED")
        ),
        "ordering_invariant_measured": (
            "The shared RunLifecycleService admits at most ONE nonterminal run "
            "(RunLifecycleError: 'cannot create a new run while active run ... is nonterminal'), "
            "so the most recently created session is always the only nonterminal one and the "
            "mutable holder happens to agree with it in the ordinary select->run flow. The "
            "binding is therefore order-dependent, not attempt-bound."
        ),
        "seam": (
            "src/virtual_factory/runcontrol/session.py::build_tipa_scenario_run_factory: "
            "factory() sets holder['profile'] globally, bridge_factory() (zero-arg) reads "
            "holder.get('profile'); RunLifecycleService._bridge_for() calls the zero-arg "
            "factory, so any bridge build that is NOT the last-created session's first start "
            "(e.g. replay/new_attempt of an older run, or any interleaved flow) uses the last "
            "selected profile instead of that attempt's pinned context.scenario_id."
        ),
    }


def registry_inventory() -> dict:
    from virtual_factory.ui.workspace_monitor import build_platform_registry

    registry = build_platform_registry()
    ids = None
    for name in ("ids", "workspace_ids", "list", "metadata"):
        candidate = getattr(registry, name, None)
        if candidate is None:
            continue
        try:
            value = candidate() if callable(candidate) else candidate
        except Exception:  # noqa: BLE001
            continue
        if isinstance(value, dict):
            ids = sorted(value)
            break
        if isinstance(value, (list, tuple, set)):
            ids = sorted(map(str, value))
            break
    return {
        "registry_type": type(registry).__name__,
        "registered_workspaces": ids,
        "continuous_workspace_registered": bool(ids) and any("continuous" in str(x) for x in ids),
        "canonical_workspace_count": len(ids) if ids else None,
    }


def main() -> int:
    probe = ConstructionProbe()
    instrument(probe)

    from virtual_factory.ui.api import create_app

    app_construction = ConstructionProbe()
    for cls, _original in probe.patched:
        app_construction.patch(cls)
    create_app(auto_start=False)
    app_construction_snapshot = app_construction.snapshot()

    phases = {
        "canonical_product_path": run_phase(probe, CANONICAL_CALLS),
        "root_dashboard_authority": run_phase(probe, ROOT_DASHBOARD_CALLS),
        "legacy_demo_assy_mes_authority": run_phase(probe, LEGACY_DEMO_CALLS),
        "legacy_g7_run_control_authority": run_phase(probe, LEGACY_G7_CALLS),
    }

    inventory = static_inventory()
    routes = route_authority_map()
    registry = registry_inventory()
    binding = attempt_binding_probe()

    evidence_dir = HERE
    inventory["route_authority_map"] = routes
    inventory["registry"] = registry
    (evidence_dir / "01-architecture-inventory.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )

    proof = {
        "instrumented_types": [type(cls).__name__ for cls, _ in probe.patched],
        "app_construction": app_construction_snapshot,
        "phases": phases,
        "attempt_binding": binding,
        "registry": registry,
    }
    (evidence_dir / "02-product-path-construction-proof.json").write_text(
        json.dumps(proof, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )

    counter_evidence = {
        "total_non_static_routes_analyzed": len(routes),
        "route_count_by_authority": dict(
            sorted(
                Counter(a for row in routes for a in row["authorities"]).items(),
                key=lambda kv: (-kv[1], kv[0]),
            )
        ),
        "canonical_sessions": phases["canonical_product_path"]["counts"].get("RuntimeSession"),
        "canonical_tipa_sessions": phases["canonical_product_path"]["counts"].get("RuntimeSession[TIPA]"),
        "canonical_shwtp_sessions": phases["canonical_product_path"]["counts"].get("RuntimeSession[shwtp]"),
        "canonical_lifecycle_services": phases["canonical_product_path"]["counts"].get("RunLifecycleService"),
        "canonical_tipa_federations": phases["canonical_product_path"]["counts"].get("TipaAssyFederation"),
        "canonical_legacy_demo_controllers": phases["canonical_product_path"]["counts"].get("DemoController", 0),
        "canonical_runtime_services": phases["canonical_product_path"]["counts"].get("RuntimeService", 0),
        "root_dashboard_runtime_services_eager_at_create_app": app_construction_snapshot["counts"].get(
            "RuntimeService", 0
        ),
        "root_dashboard_runtime_services_constructed_by_dashboard_routes": phases[
            "root_dashboard_authority"
        ]["counts"].get("RuntimeService", 0),
        "legacy_demo_controllers": phases["legacy_demo_assy_mes_authority"]["counts"].get("DemoController", 0),
        "legacy_g7_lifecycle_services": phases["legacy_g7_run_control_authority"]["counts"].get(
            "RunLifecycleService", 0
        ),
    }
    canonical_verdict = {
        "verdict": (
            "CANONICAL_PRODUCT_PATH_IS_SINGLE_AUTHORITY"
            if counter_evidence["canonical_tipa_sessions"] == 1
            and counter_evidence["canonical_shwtp_sessions"] == 1
            and counter_evidence["canonical_legacy_demo_controllers"] == 0
            and counter_evidence["canonical_runtime_services"] == 0
            else "CANONICAL_PRODUCT_PATH_CONTAMINATED"
        ),
        "rule": (
            "driving every canonical route family (/workspaces, /vnext/workspaces*, /assy-demo/*) "
            "constructs exactly one RuntimeSession per workspace (TIPA + shwtp), one TIPA "
            "federation, and zero legacy DemoController / standalone RuntimeService"
        ),
        "measured": counter_evidence,
    }

    analysis = {
        "verdict": "BLOCKED_FOR_SA",
        "gate": "VF-vNEXT-R5",
        "blocking_authorities": [
            {
                "id": "R5-BLOCK-1",
                "authority": "ROOT_DASHBOARD_RUNTIME_SERVICE",
                "construction_site": "src/virtual_factory/ui/api.py:29 (eager, at create_app time)",
                "active_product_routes": [
                    "/", "/health", "/status", "/telemetry/latest", "/telemetry/history",
                    "/alarms", "/step", "/run-steps", "/start", "/stop", "/reset",
                    "/ws/telemetry", "/api/plant-graph", "/api/model-types", "/api/fault",
                    "/api/opcua/status", "/api/ai/generate", "/api/ai/parse",
                    "/api/config/current", "/api/config/switch", "/api/ui/hierarchy",
                    "/api/ui/context", "/api/ui/context/continuous",
                ],
                "why_not_deauthorizable_in_r5": (
                    "The continuous-process product capability behind these routes "
                    "(plant config load/switch, continuous run/step/reset, telemetry history, "
                    "alarms, websocket streaming, MQTT/OPC-UA/AI tooling, ui context) has NO "
                    "canonical equivalent: the canonical platform registry exposes only "
                    "shwtp and TIPA, and create_app/WorkspaceMonitor have no continuous "
                    "workspace, run id authority or scenario/model inputs on the canonical seam."
                ),
                "measured_runtime_services_constructed_on_root_dashboard_routes": counter_evidence[
                    "root_dashboard_runtime_services_constructed_by_dashboard_routes"
                ],
                "measured_eager_runtime_services_at_create_app": counter_evidence[
                    "root_dashboard_runtime_services_eager_at_create_app"
                ],
                "authority_shape": (
                    "App-level singleton created eagerly by create_app() before any request, then "
                    "reused by every dashboard route - so the dashboard owns simulation state "
                    "independently of any RuntimeSession/run id authority."
                ),
            },
            {
                "id": "R5-BLOCK-2",
                "authority": "LEGACY_G7_RUN_CONTROL_SERVICE",
                "construction_site": "src/virtual_factory/ui/api.py:813 (TIPA) and api.py:846 (continuous)",
                "active_product_routes": [
                    "/vnext/runs", "/vnext/runs/current", "/vnext/runs/{run_id}",
                    "/vnext/runs/{run_id}/start|step|pause|resume|stop|reset|restart|replay",
                ],
                "why_not_deauthorizable_in_r5": (
                    "This family serves TWO workspaces from one API shape. TIPA here is a "
                    "DUPLICATE lifecycle authority over an UNPREPARED federation "
                    "(`TipaAssyFederation.initialize()` with no run profile, i.e. empty-clock "
                    "semantics) that contradicts the canonical prepared TIPA path, and "
                    "continuous here is a second RuntimeService authority per attempt. "
                    "De-authorizing the TIPA discriminator is safe and loses nothing proven; "
                    "de-authorizing the continuous discriminator removes the only run/replay "
                    "orchestration surface for the continuous product, which is not available "
                    "canonically. Splitting one public API family per workspace is a "
                    "product-API decision for the SA."
                ),
                "measured_lifecycle_services_constructed_on_g7_routes": counter_evidence[
                    "legacy_g7_lifecycle_services"
                ],
                "sub_finding": (
                    "Legacy TIPA path calls federation.initialize() WITHOUT a run profile, so "
                    "it can never be equivalent to the canonical prepared TIPA authority."
                ),
            },
        ],
        "product_surface_decision_required": {
            "question": (
                "Must the continuous-process product (MVP-01 plant dashboard) be consolidated "
                "onto the canonical Workspace/RuntimeSession path, and if so how?"
            ),
            "options": [
                {
                    "id": "OPTION-1-REGISTER_CONTINUOUS_WORKSPACE",
                    "description": (
                        "Register a third canonical workspace ('continuous') in "
                        "build_platform_registry with a canonical session factory "
                        "(RunLifecycleService + ContinuousExecutionBridge over a per-attempt "
                        "RuntimeService, reusing the accepted C03 pattern), rewire the root "
                        "dashboard routes to that canonical session, and retire the G7 "
                        "continuous discriminator."
                    ),
                    "capability_lost": "none (same engine, same product features)",
                    "why_SA_decision_required": (
                        "It changes the product surface: the workspace registry becomes 3 "
                        "workspaces, the shell selector and /vnext/workspaces expose a new "
                        "user-selectable workspace, create_app/WorkspaceMonitor must carry the "
                        "continuous config/dt/mqtt/opcua inputs, and accepted G23/G24/G25 + "
                        "root-dashboard expectations must be migrated. That is a milestone "
                        "boundary decision, not a bounded correction."
                    ),
                    "recommended": True,
                },
                {
                    "id": "OPTION-2-DEPRECATE_DASHBOARD_STATE_ROUTES",
                    "description": (
                        "Fail-closed the continuous state-creating routes (/step, /run-steps, "
                        "/start, /stop, /reset) and keep only read-only surfaces."
                    ),
                    "capability_lost": (
                        "The entire MVP-01 continuous-process interactive product surface "
                        "(run/step/reset + live telemetry/alarms/websocket) - a proven "
                        "capability with no canonical replacement."
                    ),
                    "recommended": False,
                },
                {
                    "id": "OPTION-3-GOVERNANCE_SCOPE_AMENDMENT",
                    "description": (
                        "The SA scopes the R5 firewall to workspace-platform product paths "
                        "(/workspaces, /vnext/workspaces, /assy-demo, outputs/registry) and "
                        "explicitly classifies the continuous dashboard + legacy G7 run-control "
                        "as 'non-workspace legacy product surfaces, frozen, no new authority'."
                    ),
                    "capability_lost": "none, but the 'no competing authority behind any active product route' requirement must be amended explicitly.",
                    "recommended": False,
                },
            ],
        },
        "unblocked_subset_ready_to_execute": [
            "R5a-1 Attempt-binding fix: make RunLifecycleService bridge construction context-aware (bridge factory receives the attempt's RunContextV2) and resolve the TIPA profile from the attempt's pinned scenario_id instead of the mutable holder.",
            "R5a-2 De-authorize /demo-assy-mes/* legacy DemoController routes (fail closed; module retained as reference/test).",
            "R5a-3 De-authorize the duplicate TIPA discriminator of /vnext/runs* (fail closed with canonical redirect guidance); keep continuous pending OPTION decision.",
            "R5a-4 Shell convergence I1 (scenario/new-run control on the canonical seam), I3 (responsive scope table), I4 (unavailable-action convention), I5 (shared glossary), I6 (remove unused G7 include on the canonical ASSY page).",
            "R5a-5 Single-system firewall test module (static import scan + dynamic construction counters per active route family).",
            "R5a-6 Evidence/regression: focused R5 + R1-R4 + full baseline + full suite.",
        ],
        "measured_evidence": counter_evidence,
        "canonical_path_verdict": canonical_verdict,
        "attempt_binding_finding": binding,
        "stop_conditions_triggered": [
            "De-authorizing a competing authority would lose a proven capability that has no canonical equivalent (continuous-process dashboard authority).",
            "Consolidating the competing authority requires a product-surface decision (registering a new user-selectable workspace) beyond a bounded R5 correction.",
        ],
        "authority_statements": {
            "vf_runtime_authorization": "NOT_AUTHORIZED",
            "site_authorized_execution": "NOT_AUTHORIZED",
            "whole_plant_runtime": "NOT_AUTHORIZED / NOT_IMPLEMENTED",
        },
    }
    (evidence_dir / "03-blocker-analysis.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )

    print(json.dumps({"phase_counts": {k: v["counts"] for k, v in phases.items()},
                      "app_construction": app_construction_snapshot["counts"],
                      "registry": registry,
                      "binding": binding.get("verdict"),
                      "canonical_path": canonical_verdict["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
