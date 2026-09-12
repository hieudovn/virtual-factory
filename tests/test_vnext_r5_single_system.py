"""VF-vNEXT-R5 — Single Simulation System Consolidation (freeze / firewall tests).

Proves, from the repo and from the live app, that:

1. NO active product path constructs a competing simulation authority:
   standalone ``RuntimeService``, ``DemoController``/``DemoRunner``, a duplicate
   ``RunLifecycleService`` authority, a standalone engine authority, or a hidden
   legacy session/runtime cache;
2. the de-authorized legacy families fail closed (HTTP 410 + machine-readable
   code) and construct ZERO runtime state;
3. the canonical product path is the ONE authority (one session per workspace;
   TIPA = one session, one federation, six sub-lines);
4. R5a-1: TIPA attempts are bound to their OWN immutable run context
   (A -> B -> replay/new_attempt never inherits another run's profile);
5. the bounded shared-shell convergence I1/I3/I4/I5 and the I6 legacy-include
   removal are in place and wired to the canonical seam.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import sys
from collections import Counter
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from virtual_factory.ui.api import (  # noqa: E402
    DEAUTHORIZED_LEGACY_SURFACES,
    LEGACY_AUTHORITY_REMOVED_CODE,
    create_app,
)

UI_STATIC = ROOT / "src" / "virtual_factory" / "ui" / "static"
API_SOURCE = ROOT / "src" / "virtual_factory" / "ui" / "api.py"

#: Types that represent a simulation authority / runtime state owner.
PROBED_TYPES: tuple[tuple[str, str], ...] = (
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


@pytest.fixture()
def probe(monkeypatch):
    """Instrument every authority constructor and record its call sites."""
    counts: Counter = Counter()
    sites: dict[str, Counter] = {}

    for module_name, class_name in PROBED_TYPES:
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        original = cls.__init__

        def wrapper(self_, *args, _orig=original, _name=class_name, **kwargs):  # noqa: ANN001
            counts[_name] += 1
            frame = inspect.stack()[1]
            sites.setdefault(_name, Counter())[
                f"{Path(frame.filename).name}:{frame.lineno}"
            ] += 1
            return _orig(self_, *args, **kwargs)

        monkeypatch.setattr(cls, "__init__", wrapper)

    def reset() -> None:
        counts.clear()
        sites.clear()

    class Probe:
        def __init__(self) -> None:
            self.counts = counts
            self.sites = sites
            self.reset = reset

    return Probe()


# ═══════════════════════════════════════════════════════════════════════════
# 1. Static firewall: the active product UI declares no legacy authority
# ═══════════════════════════════════════════════════════════════════════════

FORBIDDEN_API_CONSTRUCTIONS = (
    "RuntimeService(",
    "DemoController(",
    "DemoRunner(",
    "RunLifecycleService(",
    "SimulationEngine(",
    "DiscreteSimulationEngine(",
    "RuntimeSession(",
)


def _api_tree() -> ast.Module:
    return ast.parse(API_SOURCE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("needle", FORBIDDEN_API_CONSTRUCTIONS)
def test_active_product_api_constructs_no_authority(needle: str) -> None:
    source = API_SOURCE.read_text(encoding="utf-8")
    assert needle not in source, f"active product API still constructs {needle!r}"


#: Authority classes the active product API must never reference (AST-level, so
#: comments/docstrings can neither mask nor trigger this check).
FORBIDDEN_API_NAMES = frozenset(
    {
        "RuntimeService",
        "SimulationEngine",
        "DiscreteSimulationEngine",
        "DemoController",
        "DemoRunner",
        "AssyDemoComposition",
        "RunLifecycleService",
        "RuntimeSession",
        "AssyExecutionBridge",
        "ContinuousExecutionBridge",
    }
)

FORBIDDEN_API_MODULES = frozenset(
    {
        "virtual_factory.ui.runtime_service",
        "virtual_factory.assembly.demo_assy_mes.controller",
        "virtual_factory.assembly.demo_assy_mes.runner",
        "virtual_factory.assembly.demo_composition",
        "virtual_factory.runcontrol.lifecycle",
        "virtual_factory.runcontrol.continuous_bridge",
    }
)


def test_active_product_api_references_no_legacy_authority() -> None:
    tree = _api_tree()
    used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    used |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not (used & FORBIDDEN_API_NAMES), sorted(used & FORBIDDEN_API_NAMES)


def test_active_product_api_imports_no_legacy_module() -> None:
    tree = _api_tree()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    assert not (modules & FORBIDDEN_API_MODULES), sorted(modules & FORBIDDEN_API_MODULES)


def test_deauthorized_surfaces_are_declared() -> None:
    assert DEAUTHORIZED_LEGACY_SURFACES == (
        "root_dashboard_runtime_service",
        "legacy_g7_run_control",
        "legacy_demo_assy_mes",
    )
    source = API_SOURCE.read_text(encoding="utf-8")
    for surface in DEAUTHORIZED_LEGACY_SURFACES:
        assert surface in source


def test_workspace_ui_package_has_no_hidden_runtime_cache() -> None:
    """No UI module may CONSTRUCT a simulation authority of any kind.

    This is the 'hidden legacy session/runtime cache' firewall: not just the
    routes, but every module in the UI package must be free of authority
    construction (AST-level check on ``ast.Call`` targets).
    """
    ui_dir = ROOT / "src" / "virtual_factory" / "ui"
    offenders: list[str] = []
    for path in sorted(ui_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in FORBIDDEN_API_NAMES:
                offenders.append(f"{path.name}:{node.lineno}:{name}")
    assert not offenders, f"UI package constructs an authority: {offenders}"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Dynamic firewall: zero construction on app creation + legacy routes
# ═══════════════════════════════════════════════════════════════════════════

LEGACY_ROUTE_FAMILIES = {
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


def test_create_app_constructs_no_runtime_state(probe) -> None:
    probe.reset()
    create_app(auto_start=False)
    assert dict(probe.counts) == {}, f"create_app constructed {dict(probe.counts)}"


def test_lifespan_startup_and_shutdown_construct_no_runtime_state(probe) -> None:
    """The app must START and STOP with zero runtime construction (R5).

    Uses the TestClient as a context manager so the ASGI lifespan actually runs:
    the removed continuous loop authority must not be reachable at startup, and
    the ``auto_start`` compatibility argument must be inert.
    """
    probe.reset()
    app = create_app(
        config_path="configs/plants/continuous_mvp_01.yaml", dt_s=1.0, auto_start=True
    )
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
    assert dict(probe.counts) == {}, f"lifespan constructed {dict(probe.counts)}"


@pytest.mark.parametrize("surface", sorted(LEGACY_ROUTE_FAMILIES))
def test_legacy_route_family_fails_closed_without_construction(probe, surface: str) -> None:
    client = TestClient(create_app(auto_start=False))
    probe.reset()

    for method, path in LEGACY_ROUTE_FAMILIES[surface]:
        request = getattr(client, method)
        response = request(path, json={}) if method in ("post", "patch") else request(path[: path.find("?")] if "?" in path else path, params=(
            dict(p.split("=", 1) for p in path.split("?", 1)[1].split("&")) if "?" in path else None
        ))
        assert response.status_code == 410, (surface, method, path)
        body = response.json()
        assert body["code"] == LEGACY_AUTHORITY_REMOVED_CODE
        assert body["surface"] == surface
        assert body["legacy_runtime_authority"] is False

    assert dict(probe.counts) == {}, f"{surface} constructed {dict(probe.counts)}"


def test_deauthorized_websocket_streams_no_state(probe) -> None:
    client = TestClient(create_app(auto_start=False))
    probe.reset()
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/telemetry") as ws:
            ws.receive_json()
    assert dict(probe.counts) == {}


# ═══════════════════════════════════════════════════════════════════════════
# 3. Canonical product path is the ONE authority
# ═══════════════════════════════════════════════════════════════════════════

CANONICAL_ROUTES = (
    ("get", "/workspaces"),
    ("get", "/vnext/workspaces"),
    ("get", "/vnext/workspaces/TIPA/view"),
    ("get", "/vnext/workspaces/shwtp/view"),
    ("post", "/assy-demo/reset"),
    ("post", "/assy-demo/step"),
    ("get", "/assy-demo/overview"),
    ("get", "/assy-demo/sub-lines"),
    ("get", "/assy-demo/identity"),
    ("get", "/assy-demo/oee"),
    ("post", "/assy-demo/snapshot"),
    ("get", "/assy-demo/mes-messages"),
)


def test_canonical_path_constructs_one_session_per_workspace(probe) -> None:
    client = TestClient(create_app(auto_start=False))
    probe.reset()

    for method, path in CANONICAL_ROUTES:
        request = getattr(client, method)
        response = request(path, json={}) if method == "post" else request(path)
        assert response.status_code == 200, (method, path)

    counts = dict(probe.counts)
    # ONE canonical session per workspace, ONE TIPA federation, no legacy authority.
    assert counts.get("RuntimeSession") == 2, counts
    assert counts.get("RunLifecycleService") == 2, counts
    assert counts.get("TipaAssyFederation") == 1, counts
    assert counts.get("DemoController", 0) == 0, counts
    assert counts.get("DemoRunner", 0) == 0, counts
    assert counts.get("AssyDemoComposition", 0) == 0, counts
    assert counts.get("RuntimeService", 0) == 0, counts

    sub_lines = client.get("/assy-demo/sub-lines").json()
    rows = sub_lines["sub_lines"] if isinstance(sub_lines, dict) else sub_lines
    assert len(rows) == 6


def test_no_second_workspace_lifecycle_authority(probe) -> None:
    """R5: no third workspace and no duplicate lifecycle authority per workspace."""
    from virtual_factory.ui.workspace_monitor import build_platform_registry

    registry = build_platform_registry()
    assert sorted(map(str, registry.workspace_ids())) == ["TIPA", "shwtp"]

    client = TestClient(create_app(auto_start=False))
    probe.reset()
    client.get("/vnext/workspaces/TIPA/view")
    client.get("/vnext/workspaces/TIPA/view")
    client.get("/vnext/workspaces/shwtp/view")
    # exactly one lifecycle service per canonical workspace, no duplicates
    assert probe.counts.get("RunLifecycleService") == 2, dict(probe.counts)


# ═══════════════════════════════════════════════════════════════════════════
# 4. R5a-1 — attempt-bound profiles (no cross-run contamination)
# ═══════════════════════════════════════════════════════════════════════════

class TestAttemptBindingR5a1:
    def _factory(self):
        from virtual_factory.runcontrol.session import build_tipa_scenario_run_factory

        config = str(ROOT / "configs" / "plants" / "tipa_assy_demo.yaml")
        return build_tipa_scenario_run_factory(config)

    def _watch(self, monkeypatch):
        from virtual_factory.federation import TipaAssyFederation

        observed: list[str | None] = []
        original = TipaAssyFederation.initialize

        def patched(self, *args, **kwargs):  # noqa: ANN001
            profile = kwargs.get("run_profile")
            if profile is None and args:
                profile = args[0]
            observed.append(getattr(profile, "profile_id", None))
            return original(self, *args, **kwargs)

        monkeypatch.setattr(TipaAssyFederation, "initialize", patched)
        return observed

    def test_replay_of_older_run_uses_its_own_profile(self, monkeypatch) -> None:
        observed = self._watch(monkeypatch)
        factory = self._factory()
        a = factory("tipa-default")
        a.advance()
        a.stop()
        b = factory("tipa-failed-final")
        b.advance()
        b.stop()

        observed.clear()
        a.replay()
        a.advance()

        assert observed == ["tipa-assy-happy_path"], observed
        assert a.profile_id == "tipa-assy-happy_path"

    def test_new_attempt_of_older_run_uses_its_own_profile(self, monkeypatch) -> None:
        observed = self._watch(monkeypatch)
        factory = self._factory()
        a = factory("tipa-default")
        a.advance()
        a.stop()
        b = factory("tipa-failed-final")
        b.advance()
        b.stop()

        observed.clear()
        a.new_attempt()
        a.advance()

        assert observed == ["tipa-assy-happy_path"], observed

    def test_no_ambient_zero_arg_bridge_factory(self) -> None:
        from virtual_factory.runcontrol.session import (
            _require_attempt_bound_bridge,
            SessionError,
        )

        with pytest.raises(SessionError):
            _require_attempt_bound_bridge()

    def test_scenario_factory_binds_each_attempt_to_its_context(self, monkeypatch) -> None:
        observed = self._watch(monkeypatch)
        factory = self._factory()
        a = factory("tipa-default")
        a.advance()
        a.stop()
        b = factory("tipa-failed-final")
        b.advance()
        assert observed == ["tipa-assy-happy_path", "tipa-assy-failed_final"], observed


# ═══════════════════════════════════════════════════════════════════════════
# 5. Shared shell convergence I1 / I3 / I4 / I5 + I6
# ═══════════════════════════════════════════════════════════════════════════

SHELL_HTML = (UI_STATIC / "workspace_shell.html").read_text(encoding="utf-8")
SHELL_JS = (UI_STATIC / "workspace_shell.js").read_text(encoding="utf-8")
SHELL_CSS = (UI_STATIC / "workspace_shell.css").read_text(encoding="utf-8")


def test_i1_shell_has_scenario_and_new_run_control_on_canonical_seam(probe) -> None:
    assert 'id="ws-scenario-select"' in SHELL_HTML
    assert 'id="ws-ctrl-newrun"' in SHELL_HTML
    assert "/new-run" in SHELL_JS
    assert "scenario_id" in SHELL_JS

    client = TestClient(create_app(auto_start=False))
    probe.reset()
    view = client.get("/vnext/workspaces/TIPA/view").json()
    assert view["scenario_ids"], "the canonical view must expose the scenario ids"
    assert view["default_scenario_id"] in view["scenario_ids"]

    before = client.get("/vnext/workspaces/TIPA/view").json()["identity"]["run_id"]
    response = client.post(
        "/vnext/workspaces/TIPA/new-run", json={"scenario_id": "tipa-failed-final"}
    )
    assert response.status_code == 200
    after = response.json()
    assert after["identity"]["run_id"] != before  # fresh canonical run identity
    assert after["identity"]["scenario_id"] == "tipa-failed-final"
    # the ONE canonical authority: one lifecycle service per workspace, and the
    # fresh run replaced the previous session (no hidden second session cache)
    assert probe.counts.get("RunLifecycleService") == 1, dict(probe.counts)
    assert probe.counts.get("RuntimeSession") == 2, dict(probe.counts)
    assert probe.counts.get("DemoController", 0) == 0


def test_i1_new_run_fails_closed_for_unknown_workspace_and_scenario(probe) -> None:
    client = TestClient(create_app(auto_start=False))
    probe.reset()
    assert (
        client.post("/vnext/workspaces/NOPE/new-run", json={"scenario_id": "x"}).status_code
        == 404
    )
    assert (
        client.post(
            "/vnext/workspaces/shwtp/new-run", json={"scenario_id": "tipa-default"}
        ).status_code
        == 400
    )
    assert probe.counts.get("RuntimeSession", 0) == 0, dict(probe.counts)


def test_i3_scope_tables_are_responsive() -> None:
    assert ".ws-table-scroll" in SHELL_CSS
    assert "overflow-x: auto" in SHELL_CSS
    assert "min-width: 0" in SHELL_CSS
    assert "overflow-wrap: anywhere" in SHELL_CSS
    assert "@media (max-width: 760px)" in SHELL_CSS
    assert SHELL_JS.count('class="ws-table-scroll"') == 3


def test_i4_single_unavailable_action_convention() -> None:
    assert "setActionEnabled" in SHELL_JS
    assert "aria-disabled" in SHELL_JS
    assert SHELL_HTML.count('aria-disabled="true"') >= 7  # 6 buttons + scenario select
    assert "#ws-runbar button:disabled" in SHELL_CSS
    assert "cursor: not-allowed" in SHELL_CSS
    # every unavailable reason is explicit (no silent disable)
    assert "Unavailable:" in SHELL_JS


def test_i5_shared_glossary_present_and_consistent() -> None:
    assert 'class="ws-glossary"' in SHELL_HTML
    for term in ("STEP", "RESET", "NEW ATTEMPT", "NEW RUN", "REPLAY", "HOLD / JAM", "OEE"):
        assert f"<b>{term}</b>" in SHELL_HTML, term
    assert ".ws-glossary" in SHELL_CSS


def test_i6_canonical_assy_page_has_no_legacy_run_control_include() -> None:
    html = (UI_STATIC / "assy_demo.html").read_text(encoding="utf-8")
    assert "run_control_context.js" not in html
    assert "assy_demo.js" in html  # rich 2D domain UI retained
    assert "hierarchy.js" in html and "assy_context.js" in html
    # the legacy client guard file itself is retained (it is the fail-closed
    # client of the de-authorized family and serves the frozen dashboard page)
    assert (UI_STATIC / "run_control_context.js").exists()


def test_rich_assy_domain_ui_is_retained() -> None:
    rich_js = (UI_STATIC / "assy_demo.js").read_text(encoding="utf-8")
    for probe_name in ("uiJam", "uiRecover", "uiRunToTerminal", "uiOee", "/scenario"):
        assert probe_name in rich_js, probe_name
    from virtual_factory.ui.assy_experience import DEFERRED_FEATURES

    assert DEFERRED_FEATURES == {}
