# VF-vNEXT-R2 — Canonical Same-Session Rich ASSY 2D Experience

Gate: `VF-vNEXT-R2` (implementation gate)
Issue: #80 (`https://github.com/hieudovn/virtual-factory/issues/80`)
Architecture authority: R0 / Issue #78 (CLOSED — frozen, not reinterpreted)
Status: **BLOCKED FOR SA** (stopped before coding; no product code modified)

---

## 1. Identity / preflight evidence

| Item | Value |
|---|---|
| Repository | `hieudovn/virtual-factory` |
| Branch | `feature/vf-vnext-r2` (local; not pushed) |
| Exact technical base SHA (branch point) | `4f866323fc73a1f73f6d513d5c91220d14a997b3` (R1-C01 accepted head) — verified as local HEAD before branching |
| Harness `expected_base_sha` (origin/main) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (unchanged) |
| Working tree | clean (`git status --porcelain` empty) |
| Task contract | `.ai-harness/tasks/VF-vNEXT-R2.json` (commit `cb8c000`) |
| Harness preflight | **PRECHECK PASSED** (branch + clean tree + origin/main baseline) |
| Product code modified | **NONE** |

Issue #80 was read in full (all 12 752 characters incl. authorization, frozen
architecture, acceptance A–G, required tests, expected change zones, MUST NOT,
STOP-FOR-SA and READY evidence lists).

## 2. Feasibility findings (recorded so the SA has the positive analysis)

The binding work itself is feasible without new architecture — this is **not** a
technical-dead-end blocker:

- `assembly/demo_snapshot.py::build_snapshot(runtime, scenario)` already accepts a
  **bare `AssyLineRuntime`**, so the accepted Frame B 2D payload can be produced
  from a canonical sub-line runtime unchanged (no snapshot rewrite).
- `ui/workspace_monitor.py` already keeps exactly one live `RuntimeSession` per
  workspace in `_sessions`, reachable by a small new public accessor
  (`live_session(workspace_id)`), so `/assy-demo` can bind to the same session
  object with no second session/federation/runtime and no private cache.
- R1 already provides everything Frame B needs from the canonical session:
  prepared six-line production, `positions[]` physical truth, AP04 genealogy,
  quality/operation read models, profile-pinned scenario, and
  `AssyExecutionBridge.hold/release` for freeze evidence.
- `WorkspaceMonitor._tipa_view_extra()` currently states
  `shares_session: false` / `shares_identity: false`; the contract requires
  flipping that metadata, which is a small, additive edit.

## 3. The blocker (regression/scope boundary — requires SA decision)

R2 requires (Issue #80 §1 + §8): `/assy-demo` must **stop** using
`_get_assy_controller()` / legacy `DemoController` as its active simulation
authority, and every legacy capability that cannot be bound to the canonical
session must be **deferred** (fail closed) — explicitly including
`operation-command`, `station-action`, `run-mode`, `jam`, `recover`,
`run-to-terminal`, `/observations`, `/mes-messages`, `/mes-trace`, and the legacy
"change scenario then reset" semantics.

But a large part of the **accepted** regression surface drives its semantics
through exactly those legacy `/assy-demo` **product-path** endpoints. Measured
over `tests/` (HTTP calls to `/assy-demo*`, counted mechanically):

| File | Legacy API calls | Tests in file | Endpoints exercised |
|---|---|---|---|
| `tests/test_ops04_c01.py` | 11 | 49 | `/reset {scenario}`, `/select`, `/step`, `/sub-line/{id}` |
| `tests/test_ops03_interaction.py` | 10 | 36 | `/reset {scenario}`, `/select`, `/operation-command`, `/run-mode` |
| `tests/test_ui_hierarchy.py` | 4 | 31 | `/reset {scenario}`, `/select`, `/step` (plus rich-UI static assertions) |
| `tests/test_demo_overview.py` | 0 (route/flag introspection) | 40 | `/overview`, `/sub-lines`, `/snapshot`, `/step`, `/reset` route registration under `VF_ENABLE_S04B_OVERVIEW` |
| `tests/test_assy_mes_03_evidence.py` | 1 | 16 | `/version` |

Totals: **7 files, 26 `/assy-demo` HTTP calls, 43 path references, ~170 tests in
those files**. `test_ops03_interaction.py` and `test_ops04_c01.py` are the
accepted OPS-03 (station interaction) and OPS-04 (quality decision/HELD/final-QC)
**product-path** suites; they assert legacy controller semantics
(scenario mutation on reset, MANUAL/AUTO run modes, operation/quality commands,
AP05 jam/recover, run-to-terminal).

Consequences of implementing R2 exactly as specified:

1. `/assy-demo/reset {scenario}`, `/operation-command`, `/run-mode`,
   `/station-action`, `/jam`, `/recover`, `/run-to-terminal`, `/observations`,
   `/mes-*` stop serving legacy semantics → those accepted product-path tests
   **fail**.
2. `tests/test_demo_overview.py` additionally asserts that `/assy-demo/overview`
   and `/assy-demo/sub-lines` are registered **only** when
   `VF_ENABLE_S04B_OVERVIEW=1`; R2's Frame A needs the canonical overview on the
   product path, so either the flag contract or that accepted test changes.
3. Keeping those tests green would require either
   (a) retaining the legacy controller as a reachable authority on the product
   path — explicitly forbidden by R2 ("`/assy-demo` must stop using
   `_get_assy_controller()`"), or
   (b) **retiring/migrating ~170 accepted product-path tests** and rewriting the
   OPS-03/OPS-04 API coverage onto the canonical session — a governance decision
   about accepted regression coverage, and a workstream larger than R2 itself.

R2's declared expected change zones are `ui/workspace_monitor.py`, `ui/api.py`,
`ui/static/assy_demo.*`, optional additive `assembly/demo_snapshot.py` fields,
one small new same-session adapter, and "focused tests/evidence/harness". It does
**not** authorize retiring the OPS-03/OPS-04 product-path suites or changing the
`VF_ENABLE_S04B_OVERVIEW` route-registration contract, and the gate requires
"full canonical repository baseline remains green".

**This is a scope/regression-boundary conflict, not an implementation choice.**
Per the PM execution contract (do not silently broaden or narrow scope; STOP when
ambiguity affects milestone/scope boundaries) and the R2 guardrail "stop for SA
before coding further if correct implementation requires touching outside the
declared zones materially", implementation was stopped **before** any product
code change.

## 4. Options for SA disposition (SA/Owner decision requested)

1. **Extend R2 scope** to include migrating the legacy product-path API suites:
   authorize editing `tests/test_ops03_interaction.py`,
   `tests/test_ops04_c01.py`, `tests/test_ui_hierarchy.py`,
   `tests/test_demo_overview.py` (and record OPS-03/OPS-04 command semantics as
   R3/R4-deferred), and decide the `VF_ENABLE_S04B_OVERVIEW` route-registration
   contract (serve `/overview` + `/sub-lines` unconditionally, or keep the flag
   and require the documented demo env contract).
2. **Split the gate**: R2a = canonical same-session rich projection (overview +
   2D + inspector + STEP/RESET) with the legacy OPS endpoints kept temporarily
   behind an explicit, clearly-labelled legacy-compatibility mode; R2b = retire
   the legacy product path once the OPS-03/OPS-04 canonical binding lands in
   R3/R4.
3. **Re-sequence**: move the OPS/observation/MES legacy retirement to R3 (where
   observation/MES is in scope anyway) and keep R2 limited to a *read-rich*
   projection that does not change any existing endpoint's authority.

## 5. Current state / no-work statement

- No product code modified; only the gate task contract was added
  (`.ai-harness/tasks/VF-vNEXT-R2.json`, commit `cb8c000`).
- No tests added/modified; no baseline or full-suite re-run was needed (tree
  contains no behavioural change).
- No PR opened, nothing merged, nothing pushed to `main`; the branch is local.
- **No R3/R4 work started**; no Observation/MES, gateway, SH-WTP or
  legacy-simulator consolidation work started.
- Authority unchanged: `vf_runtime_authorization = NOT_AUTHORIZED`;
  `site_authorized_execution = NOT_AUTHORIZED`;
  `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`.

## 6. Gate status

`VF-vNEXT-R2 — BLOCKED FOR SA` (blocker = scope/regression-boundary decision,
not architecture; binding itself is proven feasible in §2). Awaiting SA
disposition before any code is written.
