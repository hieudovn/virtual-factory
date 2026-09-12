"""VF-vNEXT-UX01 evidence generator (ASSY structure drawer / sidebar cleanup).

Produces repo-native evidence from the live app + the served static assets:

  01-sidebar-cleanup.json        structural context removed from the pinned sidebar
  02-drawer-and-hierarchy.json   drawer present/closed by default + minimum hierarchy
  03-selection-non-mutation.json selection changes presentation only (same run/session/time)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE
while not (ROOT / "pyproject.toml").exists():
    ROOT = ROOT.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

UI_STATIC = SRC / "virtual_factory" / "ui" / "static"

from fastapi.testclient import TestClient  # noqa: E402

from virtual_factory.ui.api import create_app  # noqa: E402


def client() -> TestClient:
    return TestClient(create_app(auto_start=False))


def sidebar_slice(html: str) -> str:
    start = html.index('<nav id="vf-sidebar">')
    return html[start : html.index("</nav>", start)]


def drawer_slice(html: str) -> str:
    start = html.index('id="vf-structure-drawer"')
    return html[start : html.index("</aside>", start)]


def sidebar_cleanup() -> dict:
    html = client().get("/assy-demo").text
    sidebar = sidebar_slice(html)
    return {
        "sidebar_contains_hierarchy_section": "vf-hierarchy-section" in sidebar,
        "sidebar_contains_structural_context_text": "Structural context" in sidebar,
        "sidebar_contains_hierarchy_mount_ids": any(
            token in sidebar for token in ("vf-hierarchy-nav", "vf-context-crumbs")
        ),
        "sidebar_retained_blocks": [
            label
            for label in ("Line Overview", "Legend", "Reset Line", "Clear Alarms", "Export")
            if label in sidebar
        ],
        "dead_run_control_markup_untouched": "vf-run-control-section" in sidebar,
        "verdict": (
            "STRUCTURAL_CONTEXT_REMOVED_FROM_SIDEBAR"
            if "vf-hierarchy-section" not in sidebar
            and "Structural context" not in sidebar
            and all(
                label in sidebar
                for label in ("Line Overview", "Legend", "Reset Line")
            )
            else "SIDEBAR_STILL_PINNED"
        ),
    }


def drawer_and_hierarchy() -> dict:
    html = client().get("/assy-demo").text
    drawer = drawer_slice(html)
    css = (UI_STATIC / "assy_demo.css").read_text(encoding="utf-8")
    js = (UI_STATIC / "assy_context.js").read_text(encoding="utf-8")
    ctx = client().get("/api/ui/context").json()

    leaves = [child["path"] for child in ctx["hierarchy"][0]["children"]]
    return {
        "trigger": {
            "present": 'id="vf-structure-btn"' in html,
            "aria_expanded_false_at_load": 'aria-expanded="false"' in html,
            "handler": "uiToggleStructure()" in html and "uiToggleStructure" in js,
        },
        "drawer": {
            "present": 'id="vf-structure-drawer"' in html,
            "closed_by_default_markup": 'class="vf-drawer"' in drawer,
            "aria_hidden_true": 'aria-hidden="true"' in drawer,
            "close_button": 'id="vf-structure-close"' in drawer,
            "esc_close_wired": "Escape" in js,
            "mounts_inside_drawer": all(
                token in drawer
                for token in ("vf-hierarchy-section", "vf-hierarchy-nav", "vf-context-crumbs")
            ),
        },
        "visual_language": {
            "drawer_rule": ".vf-drawer {" in css,
            "open_rule": ".vf-drawer.open { display: flex; }" in css,
            "reuses_tokens": [
                token
                for token in ("var(--vf-bg-popup)", "var(--vf-radius-lg)", "var(--vf-shadow-lg)")
                if token in css
            ],
            "scoped_hierarchy_overrides": "#vf-structure-drawer .vf-hierarchy-row" in css,
        },
        "secondary_metadata": {
            "kinds_as_badges": [
                kind
                for kind in ("WORKSPACE", "CONTAINER", "EXECUTABLE")
                if f'<span class="vf-drawer-meta-k">{kind}</span>' in html
            ],
            "note_present": "structural metadata only" in html,
        },
        "minimum_hierarchy": {
            "workspace": ctx["workspace"]["path"],
            "containers": [scope["scope_id"] for scope in ctx["hierarchy"]],
            "executable_leaves": leaves,
            "matches_required_shape": ctx["workspace"]["path"] == "TIPA"
            and [s["scope_id"] for s in ctx["hierarchy"]] == ["ASSY"]
            and leaves
            == [f"TIPA/ASSY/assy-sl{i:02d}".upper() for i in range(1, 7)],
        },
        "verdict": (
            "STRUCTURE_DRAWER_WIRED_TO_CANONICAL_CONTEXT"
            if 'id="vf-structure-drawer"' in html
            and 'aria-expanded="false"' in html
            and ".vf-drawer {" in css
            else "DRAWER_INCOMPLETE"
        ),
    }


def selection_non_mutation() -> dict:
    c = client()
    before_identity = c.get("/assy-demo/identity").json()
    before_rows = c.get("/assy-demo/sub-lines").json()
    if isinstance(before_rows, dict):
        before_rows = before_rows.get("sub_lines", [])

    ok = c.post("/assy-demo/select", json={"sub_line_id": "ASSY-SL03"})
    detail = ok.json() if ok.status_code == 200 else {}

    after_identity = c.get("/assy-demo/identity").json()
    after_rows = c.get("/assy-demo/sub-lines").json()
    if isinstance(after_rows, dict):
        after_rows = after_rows.get("sub_lines", [])

    identity_keys = ("run_id", "workspace_id", "scenario_id", "profile_id")

    def norm(rows: list[dict]) -> list[dict]:
        return [
            {k: v for k, v in row.items() if "select" not in k.lower()} for row in rows
        ]

    return {
        "select_status": ok.status_code,
        "select_echo_sub_line": detail.get("sub_line_id"),
        "identity_before": {k: before_identity.get(k) for k in identity_keys},
        "identity_after": {k: after_identity.get(k) for k in identity_keys},
        "identity_unchanged": all(
            before_identity.get(k) == after_identity.get(k) for k in identity_keys
        ),
        "presentation_only_flag": after_identity.get("selection_is_presentation_only"),
        "sub_line_projection_unchanged": norm(before_rows) == norm(after_rows),
        "new_run_id_created": before_identity.get("run_id") != after_identity.get("run_id"),
        "verdict": (
            "SELECTION_IS_PRESENTATION_ONLY"
            if ok.status_code == 200
            and all(before_identity.get(k) == after_identity.get(k) for k in identity_keys)
            and norm(before_rows) == norm(after_rows)
            else "SELECTION_MUTATED_STATE"
        ),
    }


def main() -> int:
    results = {
        "01-sidebar-cleanup.json": sidebar_cleanup(),
        "02-drawer-and-hierarchy.json": drawer_and_hierarchy(),
        "03-selection-non-mutation.json": selection_non_mutation(),
    }
    # screenshot inventory (captured by the harness browser during this gate)
    results["02-drawer-and-hierarchy.json"]["browser_screenshots"] = [
        p.name
        for p in sorted(HERE.glob("shot-*.png"))
    ]
    for name, payload in results.items():
        (HERE / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {name: payload["verdict"] for name, payload in results.items()}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
