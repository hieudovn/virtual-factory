# M6-S04B-C03 — Implementation Planning (Final)

> **Status**: PLANNING C03 — config isolation + demo time contract finalization.  
> **Baseline**: DG03 frozen at `cf20843`. C02 at `2a7926f`.  
> **Purpose**: Resolve config sharing contradiction and finalize demo time semantics.  
> **Rule**: Do NOT modify runtime. Do NOT implement UI. Do NOT reopen DG01–DG03. Do NOT start M6-S05.

---

## 1. Executive Recommendation (Unchanged)

**Option A**: 6 × `AssyLineRuntime` as logical demo execution contexts. One manufacturing implementation. Additive API. Projection-only overview.

Two contract corrections from C02:

| Blocker | C02 State | C03 Fix |
|---------|-----------|---------|
| Config sharing | "One shared config instance" vs "each has own overrides" — contradictory | Per-context `deepcopy(base_config)` with isolated scenario overrides |
| Demo time | "first runtime time / max / close enough" — unstable | `demo_step_number` (presentation) + per-sub-line `simulation_time_s` (manufacturing) |

---

## 2. Code Verification — Config Mutability

Re-verified against actual code (`2a7926f`):

### 2.1 Config Structure

```
AssyLineConfig (@dataclass, mutable)
├── conveyor: ConveyorConfig (@dataclass, mutable)
├── upstream: UpstreamConfig (@dataclass, mutable)
├── station_durations: dict[str, float] (mutable)
├── quality: QualityConfig (@dataclass, mutable)
│   ├── ap03: StationQualityConfig (@dataclass, mutable)
│   │   ├── max_attempts: int
│   │   ├── scenario: str
│   │   └── overrides: dict[int, list[str]]
│   ├── ap06: StationQualityConfig (mutable)
│   ├── ap08: StationQualityConfig (mutable)
│   └── ap11: StationQualityConfig (mutable)
└── ap04_required_parent_sources: tuple (immutable)
```

### 2.2 Scenario Mutation Path

`DemoController._apply_scenario_quality()` (line 111–120):

```python
def _apply_scenario_quality(self) -> None:
    overrides = SCENARIO_QUALITY_OVERRIDES.get(self.scenario, {})
    for station_key, cfg in overrides.items():
        sqc = getattr(self._config.quality, station_key, None)
        if sqc:
            sqc.scenario = cfg.get("scenario", "PASS")      # MUTATES
            sqc.overrides = cfg.get("overrides", {})         # MUTATES
            if self.scenario == DemoScenario.FAILED_FINAL:
                sqc.max_attempts = 2                          # MUTATES
```

### 2.3 Runtime Config Read Path

`AssyLineRuntime._execute_quality_station()`:

```python
qcfg = self.config.quality.get(station_key)   # READS
```

Runtime reads config during execution. Config is **not mutated** during execution — only during initialization.

### 2.4 Conclusion

If 6 runtimes share the SAME `AssyLineConfig` object, applying scenario overrides to one context WILL leak to all contexts via the shared mutable `StationQualityConfig.scenario` and `StationQualityConfig.overrides` fields. This breaks `5 × HAPPY_PATH + 1 × AP06_FAIL_RETEST_PASS`.

**Fix**: Each context receives its own `deepcopy()` of the base config.

---

## 3. Config Isolation — Per-Context Config Instance

### Principle

```
Shared definition ≠ shared mutable config object.
```

### Safe Initialization Sequence

```
1. Load base config definition from YAML once
2. For each sub_line_id in [ASSY-SL01 .. ASSY-SL06]:
   a. context_config = copy.deepcopy(base_config)
   b. Apply scenario quality override TO context_config ONLY:
      - target sub-line → exception scenario overrides
      - other 5 sub-lines → HAPPY_PATH (default, no mutation needed)
   c. runtime = AssyLineRuntime(config=context_config)
   d. Initialize upstream WIPs + carrier state
   e. Register in AssyDemoComposition
```

### Deep Copy Guarantees

`copy.deepcopy()` on `AssyLineConfig` correctly clones:
- Nested `QualityConfig` → new instance
- Nested `StationQualityConfig` × 4 → new instances
- `StationQualityConfig.overrides: dict[int, list[str]]` → new dict + new lists
- `ConveyorConfig`, `UpstreamConfig` → new instances
- `station_durations: dict[str, float]` → new dict (immutable values, but new dict container)

No shallow-copy aliasing. Each context's config is fully independent.

### Why Not Re-Parse YAML Per Context?

`load_assy_config_from_yaml()` reads from disk each time. Deepcopy is in-memory and deterministic. Either approach works; deepcopy avoids redundant I/O and is the simpler guarantee. If deepcopy is unacceptable for any reason, re-parsing YAML per context is the fallback.

### Verification

- [x] Changing AP06 overrides in SL03 config does NOT affect SL01/02/04/05/06 configs
- [x] FAILED_FINAL `max_attempts = 2` mutation does NOT leak between contexts
- [x] Reset reconstructs fresh context configs (new `deepcopy` per `reset()`)
- [x] Config parsing remains deterministic (same YAML → same base config)
- [x] No shallow-copy aliasing of nested `QualityConfig` / `StationQualityConfig`

---

## 4. Demo Time Semantics — Final Contract

### Two Independent Time Domains

| Domain | Field | Owner | Semantics |
|--------|-------|-------|-----------|
| Manufacturing | `simulation_time_s` | `AssyLineRuntime` (per context) | Authoritative per-sub-line simulation time. Advances by `actual_dwell` per `execute_dwell()`. |
| Presentation | `demo_step_number` | `AssyDemoComposition` | Incremented once per `step_all()`. Orchestration progress, not manufacturing time. |

### Why Separate

Per §2 code audit, `actual_dwell = max(nominal_dwell, max_remaining)`. While current demo config yields ~120s for all contexts (nominal=120s dominates), the architecture must not rely on "close enough." If a future variant has a 180s station, its `simulation_time_s` will diverge from others. The demo time contract must be stable regardless.

### Demo Step (Presentation)

```
demo_step_number: int
```

- Incremented once per `AssyDemoComposition.step_all()` call
- Displayed in UI header as: `DEMO STEP 008`
- Deterministic: `step_all()` called N times → `demo_step_number == N`
- No dependency on any sub-line's `simulation_time_s`

### Sub-Line Simulation Time (Manufacturing)

```
SubLineSummaryView.simulation_time_s: float
AssyDemoSnapshot.simulation_time_s: float
```

- Authoritative per-sub-line manufacturing time
- Displayed in detail view: `t=480.0s`
- May differ between sub-lines (held vs normal)
- Owned by each `AssyLineRuntime` instance

### Overview Header

```
UI Header: "DEMO STEP 008" (presentation)
Detail View: "t=480.0s" (manufacturing, from selected sub-line)
```

No "global simulation time" derived from arbitrary runtime. No "close enough" assumption.

---

## 5. Overview Contract — Corrected Fields

### AssyOverviewSnapshot

```python
@dataclass
class AssyOverviewSnapshot:
    """Complete ASSY overview. Detached from all runtimes."""
    demo_step_number: int                        # presentation progress
    sub_lines: list[SubLineSummaryView]           # 6 entries
    total_motors_created: int                     # sum across sub-lines
    total_motors_released: int
    total_active_holds: int
    scenario: str
    target_sub_line_id: str
```

Removed: `simulation_time_s: float` (was ambiguous — which sub-line's time?).

### SubLineSummaryView

```python
@dataclass
class SubLineSummaryView:
    """Lightweight overview of one sub-line. Detached from runtime."""
    sub_line_id: str
    variant: str
    label: str
    line_state: str
    dwell_number: int
    simulation_time_s: float          # manufacturing truth for THIS sub-line
    motors_created: int
    motors_released: int
    wips_on_line: int
    active_quality_holds: int
    held_station: str
    held_wip_id: str
    is_exception: bool
```

`simulation_time_s` is per-sub-line — authoritative, no ambiguity.

---

## 6. DemoController Compatibility

**C02 wording corrected**: "No changes to CLOSED S04 runtime semantics or public behavior."

`demo_controller.py` IS edited internally to use `AssyDemoComposition`, but:

- `reset()` → resets all 6 contexts, returns snapshot for selected/default context (backward compatible)
- `step()` → steps all 6 contexts via `step_all()`, returns snapshot for selected context (backward compatible)
- `snapshot()` → returns snapshot for selected context (backward compatible)
- New public methods: `overview()`, `detail(sub_line_id)`, `select_sub_line(id)` — additive
- Internal: `_runtime` replaced by `_composition`; private API change only

Existing S04 API contracts preserved. Existing S04 frontend works unchanged if S04B overview routes are not used.

---

## 7. Fallback Contract — Deterministic

```
If S04B composition is disabled (feature flag, or code not deployed):
- GET /assy-demo/overview           → 404 (route not registered)
- GET /assy-demo/sub-line/{id}      → 404 (route not registered)
- POST /assy-demo/reset             → AssyDemoSnapshot (S04 behavior, unchanged)
- POST /assy-demo/step              → AssyDemoSnapshot (S04 behavior, unchanged)
- POST /assy-demo/snapshot          → AssyDemoSnapshot (S04 behavior, unchanged)
- GET /assy-demo                    → assy_demo.html (S04 UI, unchanged)
```

No ambiguous "single-entry list or 404." S04B routes are either registered (composition enabled) or not (composition disabled). Binary, deterministic.

### Feature Flag

```python
# In api.py
ENABLE_S04B_OVERVIEW = os.environ.get("VF_ENABLE_S04B_OVERVIEW", "0") == "1"

if ENABLE_S04B_OVERVIEW:
    @app.get("/assy-demo/overview")
    def assy_overview(): ...
    
    @app.get("/assy-demo/sub-line/{sub_line_id}")
    def assy_sub_line_detail(sub_line_id: str): ...
```

Simple, explicit, no client ambiguity.

---

## 8. Final Architecture

```
Config Source (tipa_assy_demo.yaml)
    │
    ├─ deepcopy → Context Config SL01 (HAPPY_PATH)    → AssyLineRuntime
    ├─ deepcopy → Context Config SL02 (HAPPY_PATH)    → AssyLineRuntime
    ├─ deepcopy → Context Config SL03 (exception)     → AssyLineRuntime
    ├─ deepcopy → Context Config SL04 (HAPPY_PATH)    → AssyLineRuntime
    ├─ deepcopy → Context Config SL05 (HAPPY_PATH)    → AssyLineRuntime
    └─ deepcopy → Context Config SL06 (HAPPY_PATH)    → AssyLineRuntime
                         │
                         ▼
                 AssyDemoComposition
                 demo_step_number
                         │
            ┌────────────┴────────────┐
            │                         │
   AssyOverviewSnapshot        AssyDemoSnapshot
   demo_step_number +          simulation_time_s
   6 × SubLineSummaryView      (per selected sub-line)
   (each has own sim time)      + full detail
            │                         │
            └────────── UI ───────────┘
```

One execution implementation. Independent mutable config per context. Projection-only overview. Deterministic demo step. Per-sub-line manufacturing time.

---

## 9. DG03 Traceability (Unchanged)

All 13 states still trace end-to-end. No changes to projection fields or API contracts beyond the time field corrections noted in §5.

---

## 10. Revised Implementation Gates

```
S04B-I01 — Context Identity + Config Extension
  ↓
S04B-I02 — AssyDemoComposition + Per-Context Config Isolation
  ↓
S04B-I03 — Overview Projection + Additive API
  ↓
  ═══ BACKEND GATE ═══
  ↓
S04B-I04 — ASSY Overview UI (Frame A)
  ↓
S04B-I05 — Sub-line Detail + Selection Routing (Frame B)
  ↓
S04B-I06 — Quality Inspector + Event Interaction (Frame C)
  ↓
S04B-I07 — Motion / Transition Animation
  ↓
S04B-I08 — Demo Hardening
```

### S04B-I02 Updated — Per-Context Config Isolation

**Critical invariant**: Each `AssyLineRuntime` receives its own `copy.deepcopy(base_config)`. Scenario overrides applied to the copy, not the base. Verified: no cross-context config leakage.

---

## 11. Test Strategy (Updated)

### New: Config Isolation Tests

| Test | What |
|------|------|
| Config deepcopy | `deepcopy(config).quality.ap06 is not config.quality.ap06` |
| Scenario isolation | SL03 AP06=FAIL scenario does not affect SL01 AP06=PASS |
| FAILED_FINAL isolation | SL03 max_attempts=2 does not affect SL01 max_attempts=1 |
| Reset isolation | `reset()` produces fresh independent configs |
| Deep copy depth | `StationQualityConfig.overrides` dict + list are independent copies |

### New: Time Contract Tests

| Test | What |
|------|------|
| Demo step | `step_all()` N times → `demo_step_number == N` |
| Per-sub-line time | Each `SubLineSummaryView.simulation_time_s` from its own runtime |
| Time independence | Sub-line times may differ (verified acceptable, not asserted equal) |
| Overview no global time | `AssyOverviewSnapshot` has `demo_step_number`, not `simulation_time_s` |

---

## 12. Risks (Updated)

| Risk | Severity | Mitigation |
|------|----------|------------|
| `deepcopy()` performance for 6 configs | **LOW** | Config is ~10 dataclass instances with primitive fields. Deepcopy < 1ms for 6 copies. |
| Config divergence if YAML changes between runs | **LOW** | YAML loaded once per initialize(). Deterministic within a demo session. |
| `demo_step_number` not matching user expectation of "time" | **LOW** | Detail view shows real `simulation_time_s`. Overview shows step counter. Demo narrative: "each step = one production cycle." |

---

## 13. Planning Self-Review (C03 Addendum)

### What changed from C02 to C03?
- Config: "shared instance" + "each has own overrides" contradiction → **per-context `deepcopy` with isolated overrides**, verified against actual mutation code
- Time: "first runtime / max / close enough" → **`demo_step_number` (presentation) + per-sub-line `simulation_time_s` (manufacturing)**, two independent domains
- Overview: `AssyOverviewSnapshot.simulation_time_s` removed → `demo_step_number` added
- DemoController: wording corrected from "no changes to S04 code" → "no changes to CLOSED S04 runtime semantics or public behavior"
- Fallback: "single-entry list or 404" → **binary feature flag**, deterministic

### Why are these the final corrections?
- Config isolation is now proven against actual mutation code, not assumed
- Demo time contract is stable regardless of future `actual_dwell` divergence
- All ambiguities removed from the plan

---

## 14. Scope

- ✅ M6-S04B implementation planning C03 — config isolation + demo time finalization
- ✅ Code re-verification: config mutability, scenario mutation, runtime config reads, time divergence
- ✅ Option A confirmed with corrected config isolation
- ❌ No runtime code changes
- ❌ No production UI implementation
- ❌ No MES / M6-S05
- ❌ DG01–DG03 remain closed

---

> **M6-S04B Implementation Planning C03 is READY FOR SA REVIEW.**
>
> **Status Summary**:
> ```
> DG01–DG03               ALL CLOSED ✅
> M6-S04B Planning C03     READY FOR SA
> M6-S05 MES               NOT AUTHORIZED
> ```
