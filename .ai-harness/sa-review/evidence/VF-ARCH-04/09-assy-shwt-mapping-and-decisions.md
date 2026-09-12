# VF-ARCH-04 · Evidence 09 — Decisions K, L: ASSY/SH WTP mapping + STOP assessment + non-decisions

## 1. Decision K — ASSY preservation mapping (no loss / no rewrite assumption)

The accepted ASSY UX is the **reference Discrete Experience**. It maps onto the
shared architecture **without loss and without assuming a rewrite**. Concrete
mapping of the accepted UX:

| Accepted ASSY UX | Maps to | Preservation rule |
|---|---|---|
| `vf-topbar` logo + brand | **Shell** chrome | survives as Shell branding region |
| Scenario badge (Frame A) / sub-line id + variant + scenario (Frame B) | **Shell** context strip | survives as generic run/scenario/object context strip (values remain domain content) |
| Live status + demo step | **Shell** run/scenario visibility | survives as context strip run state (demo step is demo-only value) |
| Overview/Settings/Help buttons | **Shell** global nav | survives as Shell nav |
| Frame A overview (sub-line cards, hydraulic/thermal groups) | **Monitoring** (Discrete pattern scope view) | preserved as Discrete scope overview; unchanged until ARCH-05 |
| Frame B per-sub-line detail (line layout, status cards) | **Monitoring** + **content region** | preserved as Discrete scope detail; unchanged until ARCH-05 |
| Context Inspector (`ctrlB`) on station/WIP/offline | **Context Inspector** (reference impl) | preserved as the reference object-centric Inspector; unchanged until ARCH-05 |
| `_subLineId` / `_selectedStation` / `_selectedWipId` / `_contextType` | **Context model** (scope + object axes) | survives as structural context identity |
| reset/step/run-to-terminal buttons | **Floating Control** (run) + **domain UX** (run-to-terminal) | run controls = platform primitive; run-to-terminal = domain action |
| jam/recover/station-action/operation-command | **Domain UX** (runtime-model actions) | stay in Discrete content region; authority-labeled |
| MES messages / trace panel | **Monitoring** (MES projection, Discrete pattern) | preserved as Discrete MES projection |
| OPS-03 capability-driven operation inspector | **Capability-driven UI** (Decision H) | survives as the capability-driven precedent |
| `demo_assy_mes.html` single sub-line page | **demo-only** | not frozen; scaffold only |

**Explicitly NOT rewritten**: `LineRuntime`, `AssyDemoComposition`,
`build_tipa_topology`, and the accepted ASSY frame/inspector DOM are
implementation detail (N). ARCH-04 freezes the *contracts* they already
exemplify; migration/rewrite is deferred to ARCH-05 (not started).

## 2. Decision L — Continuous / SH WTP conceptual mapping (no invented site truth)

SH WTP maps **conceptually** onto the same architecture as an illustrative
Continuous workspace — no site topology, no site-verified values, no invented
plant truth.

| Shared concept | SH WTP illustrative mapping |
|---|---|
| Workspace / Scope | plant site → process areas (e.g., intake, treatment, dosing, storage) |
| Hierarchy | area → equipment → instrument |
| Connectivity graph | process-flow / P&ID-style view |
| Context Inspector (object) | pump/valve/sensor/equipment → Overview/State/Signals/Live Trend/Events-Alarms/Process/Control/Balance/Quality/Parameters |
| Monitoring (scope) | process overview, trend/analysis views, threshold alarms, balance/quality summary |
| Capability state | water-quality/control/balance capabilities declared by provider; `not_ready` shown with blocker |
| Readiness | ARCH-03 aggregation per scope; no invented score |
| Alarms | threshold alarms = Alarm ⊂ Event projections (ARCH-03) |
| Action authority | simulation + runtime-model only; no plant-control implied |
| Evidence | PIM `evidence_policy.yaml` statuses (SiteVerified etc.) projected as Evidence/Provenance — VF never upgrades |

All SH WTP statements are **illustrative patterns**, not site truth. No
`Song Hong`-specific values are asserted.

## 3. STOP-condition assessment

| STOP condition | Assessment |
|---|---|
| Preserving ASSY UX conflicts with shared shell/context | **Not triggered** — ASSY maps onto Shell + content region + Inspector without loss (§1) |
| One shell cannot support Continuous/Discrete/Batch without a breaking decision | **Not triggered** — three archetype *patterns* share one frame (evidence 07) |
| Existing UI routing/context forces workspace-name hard-coding | **Not triggered** — ASSY already uses capability-driven dispatch (OPS-03); context uses structural ids, not names |
| Capability/readiness presentation needs a second authority | **Not triggered** — authority stays with ARCH-03 provider + aggregation (evidence 08) |
| Requires selecting a new frontend framework | **Not triggered** — explicitly a non-decision |
| Safe action semantics require deciding real plant-control authority | **Not triggered** — plant-operational is deferred as a non-decision; simulation vs runtime-model already distinguishable |
| Correct UI architecture requires ARCH-05 migration prematurely | **Not triggered** — ARCH-05 NOT started; migration deferred |

**Conclusion: no STOP condition triggered.**

## 4. Non-decisions (deferred, explicitly not frozen here)

1. Frontend component code.
2. CSS/theme implementation.
3. React/Vue/Angular or other framework migration.
4. Final dashboard persistence / layout engine.
5. Final widget schemas.
6. Real Historian implementation.
7. Production alarm workflow engine.
8. TIPA/ASSY runtime migration.
9. SH WTP runtime/domain models.
10. Semantic loader/binding implementation.
11. Real plant-control authorization.
12. Snapshot/checkpoint/replay editor.
13. Advanced RBAC.
14. Production provenance storage.

## 5. Critical risks addressed

| Risk | How frozen decision neutralizes it |
|---|---|
| One giant generic screen degrading all archetypes | archetype *patterns* + 0..N views; no identical layout (evidence 07) |
| Forcing ASSY UX onto Continuous/Batch | Continuous favors process/monitoring/analysis; Batch extends with recipe/phase/material (evidence 07) |
| Replacing ASSY accepted UX unnecessarily | ASSY preserved as reference Discrete Experience, unchanged until ARCH-05 (§1) |
| UI routes/labels becoming structural identity | context identity = structural ids + capability state, not names (evidence 03/08) |
| Shell becoming a God UI owning domain state | Shell anti-responsibilities explicit (evidence 02) |
| Monitoring and Inspector duplicating truth | same facts, different perspective; projection-only (evidence 06) |
| Capability behavior hard-coded by workspace name | state → UI matrix, no name conditionals (evidence 08) |
| Hiding not_ready/required-missing | explicit blocker, never silently omitted (evidence 08) |
| Misleading simulation actions as plant control | authority labels; no plant control (evidence 08) |
| Treating Live Series as Historian | bounded current-run Live Series ≠ Historian (evidence 06) |
| Alarm List becoming independent store | Alarm List = projection, same authority as Inspector (evidence 06) |
| Container-only scope shown as executable | container shows `not_applicable` execution readiness (evidence 03/08) |
| Designing ARCH-05 migration prematurely | ARCH-05 NOT started; migration deferred (§4) |

## 6. Frozen Owner/SA intent (verbatim preservation check)

- Unified architecture ≠ identical layout → honored (evidence 07).
- One platform, many workspaces/nested scopes → honored (evidence 03).
- Navigation tree-like; connectivity graph-based → honored (evidence 03).
- Current context always explicit → honored (evidence 03).
- Platform Shell shared; domain content differs by archetype/capability → honored (evidence 02/07).
- Floating Simulation Control = minimal run control; no editor/domain/plant controls → honored (evidence 04).
- Context Inspector object-centric, projection-only → honored (evidence 05).
- Monitoring scope-centric, projection-only → honored (evidence 06).
- Capability state drives visibility/enablement/transparency; never hard-coded by workspace name → honored (evidence 08).
- ASSY existing UX = reference Discrete Experience, preserved → honored (§1).
- UI/API clients don't directly mutate another scope/runtime state → honored (evidence 08).
- Action authority distinction → honored (evidence 08).
- No frontend framework migration decided → honored (§4).
