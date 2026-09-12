# VF-ARCH-04 · Evidence 02 — Decision A: Platform Shell

## 1. Decision statement

**One VF Platform hosts many Workspaces, each with nested Scopes. The Platform
Shell is the single shared chrome that frames every workspace/scope/archetype,
but it owns no domain state and does not impose one identical layout.**

Unified architecture ≠ identical layout. The Shell is *the container of
context*, never *the owner of domain truth*.

## 2. Shell responsibilities (explicit, bounded)

The Shell **is** responsible for:

1. **Current-context display** — always shows an explicit, non-ambiguous
   `workspace` → `scope` → (optional) `object` → (optional) `run/scenario`
   breadcrumb/context strip. The user can always answer "where am I?" without
   inferring it from layout.
2. **Global navigation** — workspace switching, scope navigation (tree-like
   hierarchy) and connectivity/graph drill-through entry points.
3. **Breadcrumb / hierarchy nav** — structural path display and back/up
   traversal; the tree answers *structure*, the graph answers *connectivity*.
4. **Run/scenario visibility** — a minimal, read-mostly indicator of the current
   run/scenario context (which run/scenario is selected and its state), not a
   scenario editor.
5. **Shared control placement** — hosts the Floating Simulation Control (evidence
   04) at a fixed, predictable location; hosts no domain process controls.
6. **Health/readiness surface** — displays scope/workspace readiness and
   capability state honestly (evidence 08); never computes an arbitrary score.
7. **Workspace/scope switching** — the only owner of "which workspace/scope is
   currently active"; switching is context navigation, never state mutation of
   the target.
8. **Route/context identity** — the Shell derives *what to show* from the
   current context identity, but does **not** hard-code behavior by workspace
   name (evidence 08).

## 3. Shell anti-responsibilities (what it MUST NOT do)

The Shell **must not**:

1. Own domain runtime truth — runtime state lives in ARCH-01/ARCH-02 runtime
   contracts; the Shell only projects.
2. Duplicate monitoring state — the Shell renders Monitoring projections
   (evidence 06); it keeps no second store of telemetry/alarm/event facts.
3. Become a "God UI" that owns domain state or re-implements runtime logic.
4. Host domain process controls or plant-control actions (evidence 08).
5. Hard-code capability/readiness presentation by workspace name.
6. Require identical domain layouts — domain content is supplied by the active
   archetype experience inside the Shell's content region.

## 4. Mapping to current repo

| Shell responsibility | Current precedent | Status |
|---|---|---|
| Current-context display | `assy_demo.html` `vf-topbar`: scenario badge (Frame A) / sub-line id + variant + scenario (Frame B) | **D → R**: generalize to generic context strip; ASSY values become domain content |
| Global navigation | `index.html` sidebar nav; `assy_demo.html` Overview/Settings/Help buttons | **G/D → R** |
| Breadcrumb / hierarchy nav | Frame A → Frame B drill-down (`openFrameB(subLineId)`, `backToFrameA`) | **D → R concept** (drill-down) |
| Run/scenario visibility | `demo-step` counter, `HAPPY_PATH` badge | **X → R concept** (context strip, not demo values) |
| Shared control placement | `index.html` start/stop/step/reset; `assy_demo.html` reset/step | **G/D → R** (see evidence 04) |
| Health/readiness surface | (none today) | **R new** — consumed from ARCH-03 readiness aggregation |
| Workspace/scope switching | sidebar panes (`data-pane`) | **G → R concept** |
| Route/context identity | `/assy-demo/select`, `/api/config/switch` | **D/G → R concept** (context selection) |

## 5. What survives vs what is legacy

- **Survives as platform concept**: shell chrome, context strip, global nav,
  single content region hosting an archetype experience, floating control slot,
  health/readiness surface.
- **Legacy (not frozen)**: the exact `index.html` SCADA sidebar + panes layout;
  the exact `assy_demo.html` top-bar DOM. Both are *evidence of the concept*, not
  the frozen implementation (no frontend code is written in this gate).
- **Two shells today, one Shell in vNext**: the generic SCADA shell and the ASSY
  demo shell are today two separate pages. ARCH-04 freezes the *concept* of one
  shared Shell with a domain-agnostic chrome and an archetype-owned content
  region — not the merging of today's DOM.

## 6. Bounded-ness test

- Does the Shell know the workspace? Yes (context identity).
- Does the Shell know the workspace's *domain behavior*? No — capability state
  drives that (evidence 08).
- Does the Shell mutate any scope/runtime state directly? No — all mutations
  route through ARCH-02 declared interfaces (evidence 08).

**Decision A is explicit and bounded.**
