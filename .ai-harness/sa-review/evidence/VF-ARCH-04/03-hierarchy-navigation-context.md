# VF-ARCH-04 · Evidence 03 — Decision B: Hierarchical navigation and context model

## 1. Decision statement

**Navigation is hierarchical (tree-like) for structure and graph-based for
connectivity; the current context (workspace/scope/object/run/scenario) is
always explicit and never inferred from layout or route strings.**

## 2. Context model (consistent with ARCH-01)

```
Workspace
 └─ Scope
     ├─ Scope (nested, federated)
     │   ├─ Object (device/equipment/station/asset)
     │   └─ ...
     └─ Object
```

Frozen rules:

1. **Structural current context** is a path: `workspace` → `scope` → … →
   `object`, plus optionally the **selected run** and **selected scenario**.
   All five are shown explicitly; none may be implicit.
2. **Tree vs graph**:
   - The **hierarchy tree** (breadcrumb + scope tree) answers *structure*:
     containment, ownership, scope nesting.
   - The **connectivity graph** (process-flow / line layout / P&ID-style) answers
     *dependency*: flows, boundaries, cross-scope links. It is a view over the
     graph model, not the navigation authority.
   - Drill-through from graph → object is allowed and must preserve the
     structural context of the origin (i.e., navigating to a connected object
     still lands with an explicit scope/object context).
3. **Container-only vs executable scope** (from ARCH-01/ARCH-03): a container
   scope (structure-only, no runtime) must be presented as a container — it has
   structural/composition readiness, but its **execution readiness is
   `not_applicable`**. The UI must never show a container scope as if it had an
   executable runtime (no fake start/step).
4. **Federated child, independently addressable**: a child scope that is
   federated into a parent remains independently addressable; selecting the
   child switches context into that child (with parent breadcrumb retained).
5. **Selected object vs selected scope**: selecting an object does not change
   the active scope; it sets the `object` axis of context. The Inspector
   (evidence 05) opens for the object; Monitoring (evidence 06) remains
   scope-scoped.
6. **Unavailable / not-ready siblings**: sibling scopes that are not ready or
   not applicable remain navigable (visible) with honest capability state; the
   UI never fabricates simulation capability for them (evidence 08).
7. **No TIPA/SHW name hard-coding**: context identity uses structural
   identifiers + capability state, never `if workspace_name == "TIPA"`.

## 3. Navigation controls and their roles

| Control | Role | Answering |
|---|---|---|
| Breadcrumb | show + jump along current structural path | "Where am I, and how did I get here?" |
| Scope tree | navigate containment hierarchy | "What is inside this workspace?" |
| Connectivity graph | drill-through by dependency/flow | "What is this connected to?" |
| Context selector | switch workspace/scope/run/scenario explicitly | "Which context do I want?" |
| Back/up | return to parent scope or previous frame | "Take me up a level" |

## 4. Mapping to current repo

| Frozen concept | Current precedent |
|---|---|
| Explicit context strip | `assy_demo.html` `vf-topbar` Frame B: `ASSY-SL01` + `HYDRAULIC` + `HAPPY_PATH` (sub-line / variant / scenario) |
| Drill-down preserving structural context | `assy_demo.js` `openFrameB(subLineId)` (Frame A → Frame B with `_subLineId`); `backToFrameA()` |
| Graph as connectivity view | `editor.js` process-flow graph; `assy_demo.js` line layout canvas |
| Scope tree | `index.html` sidebar (legacy panes) → generalized to hierarchy tree |
| Context switching | `/assy-demo/select`, `/api/config/switch` |
| Object vs scope | `assy_demo.js` `_selectedStation` / `_selectedWipId` (object axis) vs `_subLineId` (scope axis) |

The ASSY Frame A/B model is a **presentation precedent** for hierarchy
navigation, not a structural re-typing. The frozen ARCH-01 structural mapping is
lossless and unchanged: **TIPA = Workspace; ASSY = child Simulation Scope;
ASSY-SL01..06 = child Simulation Scopes of ASSY; station / AP / WIP / carrier =
Simulation Objects**. ASSY is not retyped as Workspace merely because the current
demo is standalone, and a sub-line is not downgraded from Scope to Object. ARCH-04
generalizes the navigation *form* (drill-down, context strip) — it does not change
the ARCH-01 structure.

## 5. Consistency check with ARCH-01

- ARCH-01 hierarchy (Workspace → Scope → nested → Object) — respected, with the
  lossless TIPA/ASSY mapping preserved verbatim: TIPA = Workspace, ASSY = child
  Simulation Scope, ASSY-SL01..06 = child Simulation Scopes, station/AP/WIP/
  carrier = Simulation Objects. The standalone ASSY demo UI is only a
  presentation precedent; it never re-types ASSY as Workspace or a sub-line as
  Object.
- ARCH-01 container vs executable scope — respected (container shows
  `not_applicable` execution readiness).
- ARCH-01 federated child independently addressable — respected (child selection
  switches into child).
- ARCH-02 scope-scoped commands — respected (no cross-scope direct mutation;
  context switch ≠ state mutation).

**Decision B is explicit and consistent with ARCH-01.**
