# VF-ARCH-06 — Freeze SH WTP target mapping and vNext implementation roadmap

> **C01 revision (Issue #45 SA review):** removed the universal
> `1 executable scope = 1 SimulationEngine` assumption. Frozen instead: an
> executable Simulation Scope owns an **execution/runtime boundary** (one or more
> execution mechanisms per scope contract — continuous / state-machine /
> discrete / hybrid); `SimulationEngine` and `runtime.engine: continuous_process`
> are the **current continuous implementation/profile precedent** (PH00
> compatibility/default/profile descriptor), NOT a universal engine-cardinality
> rule; engine cardinality/type is an implementation/profile concern; SH WTP
> stays compatible with hybrid scopes and ARCH-02 composition semantics. G1–G10
> roadmap, legacy WTP disposition, fidelity/evidence constraints, and the
> architecture-closure conclusion are unchanged.

| Field | Value |
|---|---|
| Task ID | `VF-ARCH-06` (GitHub Issue #45) |
| Parent | Issue #39 `VF-vNEXT-ARCH` (umbrella architecture program) |
| Prerequisite | ARCH-05 / Issue #44 CLOSED by SA as `completed` |
| Repository | `hieudovn/virtual-factory` |
| Gate type | Architecture / design / roadmap gate — documentation & evidence only (no production implementation) |
| Architecture baseline | ARCH-01 `41903e18…` + ARCH-02 `40454487…` + ARCH-03 `392401bd…` + ARCH-04 `d5c155b6…` + ARCH-05 `8fafa119…` |
| Production baseline | canonical `main` lineage (`f5261c8…`; unchanged) |
| Production code changed | **NO** (only `.ai-harness/`) |
| Implementation started | **NO** |

## 1. Objective

Freeze the SH WTP target mapping onto the completed vNext architecture and
produce the ordered implementation roadmap. Two questions answered: (1) can the
frozen architecture represent SH WTP without a new platform decision? (2) what
implementation gates follow, in what order, with what acceptance evidence?

## 2. Repo-first discovery (evidence 01)

- Two standalone WTP mini-engines: `simulators/wtp` (8 engines, hard-coded 92
  signals, own OPC UA/ingest/dashboard, 8 scenarios) and `simulators/vf2`
  (PIM-package-driven, dual VF-local/canonical IDs) — both frozen LEGACY/REFERENCE
  (PH00 B7).
- Shared core `src/virtual_factory` is **water-treatment-free**: generic
  `SimulationEngine`, `process_dynamics`, balance, PID, operating-state machine,
  telemetry/observation; continuous behavior proven by existing tests.
- `configs/workspaces/` does not exist (B9 planned target `configs/workspaces/shw-wtp/`).

## 3. Frozen decisions (evidence 02–10)

| Decision | Frozen contract |
|---|---|
| **A — Inventory** | WTP artifacts classified: reusable shared-core / SH-WTP-specific domain (future) / standalone mini-engine legacy / semantic-binding dependency / UI capability / implementation gap. |
| **B — Hierarchy** | SH-WTP = Workspace → process-area/unit Scopes → equipment/instrument Objects; illustrative scope names only (no site truth). |
| **C — Runtime** | an executable scope owns an execution/runtime boundary (one or more execution mechanisms per scope contract — continuous/state-machine/discrete/hybrid); `SimulationEngine`/`runtime.engine: continuous_process` is the current continuous implementation/profile precedent, NOT a universal `1 scope = 1 engine` rule; shared core owns execution/composition; SH-WTP physics is a future domain model. |
| **D — PIM dependency** | PIM = semantic authority; version/hash-pinned, fail-closed (`semantic_binding.mode: required`); fidelity `logical_only` (B1–B10 + ALIGN/COMPAT/EXPORT). |
| **E — Observation/Event/Capability/Readiness** | maps to ARCH-03; `data_status=synthetic`; no fabricated measured/site truth. |
| **F — UI** | maps to ARCH-04 Continuous experience; legacy dashboard/nav link not the target. |
| **G — Legacy disposition** | `simulators/wtp` reference-only → future deprecation; `simulators/vf2` reference binding pattern → candidate for extraction; nothing deleted/refactored now. |
| **H — Roadmap** | ordered G1–G10; one-gate-at-a-time; dependency logic preserved. |
| **I — Per-gate evidence** | minimum acceptance evidence classes per gate; ASSY oracle + cont-baseline on every gate. |
| **J — Closure** | no unresolved platform-level gap remains; umbrella #39 may close after SA accepts ARCH-06. |

## 4. Roadmap (evidence 08–09)

```
G1 Workspace/Scope Foundation          G6 Shared hierarchical UI primitives
G2 Runtime Context + Provenance v2     G7 Hierarchical Scenario / Run Control
G3 Observation/Event/Alarm alignment   G8 VF Platform vNext Regression Baseline
G4 Composition Graph + Coordinator +   G9 Semantic Binding vNext
   Typed Ports                         G10 Resume SH WTP runtime roadmap
G5 TIPA Workspace / ASSY federation
```

Each gate has minimum acceptance evidence (changed-file scope, tests, determinism,
ASSY regression oracle, continuous/compressor baseline, binding fail-closed, UI
projection, no-duplicate-runtime-path) — evidence 09. ASSY regression protection
is explicit on every gate.

## 5. STOP-condition assessment (evidence 10 §2)

None triggered: SH WTP maps without new platform concepts; PIM/VF contracts
reconciled as-is; legacy mini-engines are reference (no competing target); G10
placed last (no premature SH WTP); no unresolved platform-level gap; no invented
site truth.

## 6. Architecture closure (evidence 10 §3)

**No unresolved platform-level architecture gap remains after ARCH-01..06.**
Umbrella #39 may close after SA accepts ARCH-06; the implementation program
(G1–G10) becomes the next phase.

## 7. Non-decisions (deferred)

No Workspace/Scope, coordinator, provenance-v2, semantic binding, ASSY
migration, SH WTP runtime, mini-engine deletion/refactor, frontend changes,
fidelity raise, PIM changes; no implementation gate begun.

## 7.1 C01 corrections applied

1. **Execution boundary, not engine cardinality (C01-1):** removed the universal
   `1 executable scope = 1 SimulationEngine` assumption. An executable scope
   owns an execution/runtime boundary that may host/use one or more execution
   mechanisms per its scope contract (continuous / state-machine / discrete /
   hybrid). `SimulationEngine` / `runtime.engine: continuous_process` are the
   current continuous implementation/profile precedent (PH00 descriptor), not a
   universal engine-cardinality rule. Engine cardinality/type is an
   implementation/profile concern unless frozen later (evidence 03 §1/§4, 02 §4,
   10 §4).
2. **Consistency sweep:** removed residual wording equivalent to "engine at scope
   level" / "exactly one engine per executable scope" across evidence 02, 03,
   09, 10 and this report. G1–G10 roadmap, legacy WTP disposition, fidelity/
   evidence constraints, and the architecture-closure conclusion are unchanged.

## 8. Acceptance

| Criterion | Result |
|---|---|
| SH WTP maps onto frozen architecture without new platform concepts | PASS (02, 03, 05, 06, 10) |
| Continuous/WTP seams + duplicate paths classified with disposition | PASS (01, 07) |
| PIM/semantic-binding dependencies explicit and consistent | PASS (04) |
| Continuous observation/event/capability/UI mappings explicit and evidence-safe | PASS (05, 06) |
| Roadmap ordered, dependency-aware, gate-sized | PASS (08) |
| Each future gate has clear acceptance evidence | PASS (09) |
| ASSY regression protection explicit | PASS (08 §4, 09 §4) |
| Architecture closure assessment explicit | PASS (10 §3) |
| No production code or implementation started | PASS (only `.ai-harness/`) |

## 9. Evidence

`.ai-harness/sa-review/evidence/VF-ARCH-06/` — 10 files (01…10).

## 10. Final status

```text
VF-ARCH-06-C01 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. No implementation gate is started; the
implementation program begins only after SA closes umbrella #39.
