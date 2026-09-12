# VF-vNEXT-G23 — Multi-Workspace Runtime Selection — Evidence

Gate: `VF-vNEXT-G23` · Implementation gate (additive registry module + tests).
Base: `1c076525c62ab5c12e98fe970e035b4921cb62a0` (G22 head).
Model: Pro.

## 1. What was implemented

- `src/virtual_factory/runcontrol/registry.py` — generic, domain-agnostic
  `WorkspaceRuntimeRegistry`:
  - `WorkspaceRuntimeInfo` — deterministic orchestration metadata
    (workspace_id + description).
  - `register(workspace_id, factory, description)` — fail closed on empty id,
    non-callable factory, duplicate id.
  - `workspace_ids()` / `enumerate()` — deterministic (sorted), independent of
    registration order.
  - `select(workspace_id)` — returns a FRESH independent RuntimeSession for that
    Workspace only; unknown id fails closed; a factory returning a session whose
    `workspace_id` differs from the registered key fails closed (identity
    mismatch).
  - `metadata()` — platform orchestration metadata only (no graph/binding/
    runtime coupling).
- `tests/test_vnext_g23_registry.py` — 15 tests.

## 2. Required semantics coverage

| Requirement | Proof |
|---|---|
| deterministic enumeration | `workspace_ids() == ("TIPA", "shwtp")` sorted |
| TIPA → ASSY session factory | `select("TIPA")` returns `RuntimeSession(workspace_id="TIPA")` |
| shwtp → G21/G22 session factory | `select("shwtp")` returns `RuntimeSession(workspace_id="shwtp")` |
| select only that Workspace | `select` routes strictly by registered id |
| isolation | separate sessions/objects/bridges; no shared state/run_id/clock |
| switching no mutate inactive | advancing shwtp leaves TIPA session trace/state untouched |
| fresh independent session | two `select("shwtp")` calls return independent instances |
| unknown/ambiguous fail closed | unknown id + identity-mismatch factory + duplicate registration all raise |
| registry orchestration metadata only | `metadata()` has no graph/binding/coupling |
| no cross-workspace coupling | distinct session objects and bridges |
| open for future Workspaces | a third registered factory (demo-ws) is enumerable + selectable |

## 3. Preserved / unchanged

G22 session semantics; G21/G20/G19/G18/G14/G15; TIPA ASSY; runcontrol frozen G7
boundary (no SH-WTP reference — the generic registry lives in runcontrol and
SH-WTP session factory wiring is done by callers/tests). No UI, no gateway
routing, no MES/PIM change, no G4 redesign, no T110/Line2.

## 4. Test evidence

- `tests/test_vnext_g23_registry.py` — 15 tests PASS.
- Complete canonical vNext baseline (see report `VF-vNEXT-G23.md`).
