# VF-vNEXT-G2 — Implement Runtime Context + Provenance v2

| Field | Value |
|---|---|
| Task ID | `VF-vNEXT-G2` (GitHub Issue #47) |
| Program | Implementation phase (G2; only authorized implementation gate) |
| G1 base (required) | `ac329fbd7f96614be9f09e8037a3e10cfabaf1dd` |
| Branch | `feature/vf-vnext-g2` |
| Production base (`origin/main`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| G3+ started | **NO** |

## 1. Objective

Implement the smallest reusable, immutable, mechanism-neutral runtime/run context
+ provenance v2 foundation, reconciling the existing `discrete.RunContext`
without duplicate authority, threading provenance additively into the shared
telemetry/output seam, and preserving simulation-truth labels and identity
separation.

## 2. Implementation (production)

New package `src/virtual_factory/provenance/`:
- `enums.py` — `OriginKind`/`DataStatus`/`Fidelity` (frozen truth labels);
- `context.py` — generic immutable `RunContextV2` (mechanism-neutral);
- `envelope.py` — immutable `ProvenanceV2` (origin_kind/data_status/fidelity +
  semantic pins, no canonical field; no frame-level runtime_signal_id);
- `namespace.py` — deterministic `derive_output_namespace`;
- `adapter.py` — `from_discrete_run_context` + `to_provenance_v2`.

`telemetry/telemetry_frame.py` — **additive** `ProvenancedFrame` +
`build_provenanced_frame` (legacy `build_publishable_frame` unchanged).

No `discrete/`, `assembly/`, `observation/`, `ui/`, `integration/`, `core/`, or
`equipment/` production file modified. `AssyLineRuntime` untouched.

## 3. Key decisions (evidence 02–05)

- **Reconciliation:** thin adapter — `discrete.RunContext` stays backward
  compatible and converts losslessly into the single platform authority
  `RunContextV2` (its `engine_kind` becomes the informational `profile`).
- **Identity separation:** workspace/scope/run/scenario/model/namespace/runtime
  signal are distinct; no PIM canonical id field exists or is fabricated.
- **Truth labels fail-closed:** `origin_kind=simulation`; `data_status` ∈
  {synthetic, simulated_ground_truth}; `fidelity` frozen; plain measured/truth
  rejected.
- **Telemetry threading additive:** same policy filtering/coercion; provenance
  lives beside `SignalValue`, never inside it; legacy seam unchanged.
- **Namespace:** deterministic, distinct from `workspace_id`, no registry.
- **C01-1 workspace/scope consistency:** a present `scope_path` must root in
  `workspace_id` (`scope_path.workspace_id == workspace_id`) — fail closed in
  `RunContextV2`, `ProvenanceV2`, and via the discrete adapter.
- **C01-2 per-signal runtime identity:** `runtime_signal_id` is per-signal,
  derived at record construction (never one frame-level value stamped on all
  signals); run/frame provenance stays shared; no PIM canonical id fabricated.

## 4. Test / regression results (evidence 06)

| Suite | Result |
|---|---|
| New G2 tests | **36 passed** (incl. C01) |
| G1 + discrete + telemetry/observation targeted | **415 passed** |
| ASSY regression oracle | **354 passed** |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1715 passed** (0 failures) |
| Compile check | PASS (no configured ruff/mypy/black) |

## 5. STOP-condition assessment (evidence 07 §2)

None triggered.

## 6. Non-decisions / deferred (evidence 07)

G3 Observation/Event/Alarm, G4 Coordinator/Ports, G5 ASSY federation, G6 UI,
G7 run-control/replay, G8, G9 PIM binding, G10 SH WTP runtime, protocol
propagation of `ProvenancedFrame`, namespace consumption — all deferred.

## 7. Acceptance

| Criterion | Result |
|---|---|
| One generic mechanism-neutral runtime context/provenance seam | PASS |
| discrete run context reconciled without duplicate authority | PASS |
| G1 workspace/scope identity carried without semantic collapse | PASS |
| Shared telemetry/output carry deterministic provenance additively | PASS |
| Simulation truth labels fail-closed | PASS |
| Namespace and identity separation explicit | PASS |
| No PIM semantic identity fabricated | PASS |
| No G3+ implementation | PASS |
| Mandatory regressions pass | PASS (36 + 415 + 354 + 61 + full 1715) |
| Working tree clean and branch/head pushed | PASS (after push) |

## 8. Evidence

`.ai-harness/sa-review/evidence/VF-vNEXT-G2/` — 8 files (01…08; 08 = C01
corrections).

## 9. Final status

```text
VF-vNEXT-G2-C01 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. G3 is NOT started.
