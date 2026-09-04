# VF-vNEXT-G5 — Migrate TIPA Workspace / ASSY Federation onto G1–G4

| Field | Value |
|---|---|
| Task ID | `VF-vNEXT-G5` (GitHub Issue #50) |
| Program | Implementation phase (G5; only authorized implementation gate after G4) |
| Required base (branch) | `ae0a86e4ad8add77c731fbd597534f24a2f7b575` (accepted G4 final head) |
| Branch | `feature/vf-vnext-g5` |
| Production base (`origin/main`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| Model | Flash |
| G6+ started | **NO** |

## 1. Objective

Migrate the existing TIPA ASSY multi-context runtime into the vNext
structural/composition foundation (G1 Workspace/Scope + G4 participant/
coordinator seams) while preserving all existing ASSY domain behavior, proving
the same existing `AssyLineRuntime` is the runtime truth in both standalone and
federated hosting — without forking/rewriting domain logic and without a new
synchronization policy.

## 2. Implementation (production — new additive `federation/` package)

- `tipa_workspace.py` — canonical `Workspace "TIPA"` → container-only `Scope
  "ASSY"` → six executable-capable `ASSY-SL01..SL06`; deterministic structural
  paths `TIPA/ASSY/ASSY-SLxx`; `sub_line_path`/`assy_scope_path` fail closed on
  non-canonical ids.
- `assy_participant.py` — `AssySubLineAdapter`: G4 `ExecutableParticipant` over
  one existing `AssyLineRuntime` (fixed G1 scope_path; `current_time_s`
  delegates; advancement uses only public ASSY runtime ops in the oracle-driver
  order). Natural-boundary rule: only EXACT reachable boundaries succeed;
  overshooting/fractional targets fail closed — no ASSY rewrite.
- `assy_host.py` — `TipaAssyFederation`: owns the TIPA Workspace, builds six
  isolated runtimes via the existing demo construction/config-isolation pattern
  (deepcopy + ordinal seed), binds each to its executable G1 scope, exposes
  adapters and a G4 `Coordinator` seam; never makes ASSY executable; never
  replaces domain truth.

No forbidden file modified; `assembly/`, `workspace/`, `composition/`, and all
other existing packages are untouched.

## 3. Standalone / federated parity

- Fast-config representative runs (16-cycle release; 7-cycle AP04 JOIN):
  standalone vs federated produce identical canonical domain state, identical
  RELEASED set, exact-equal simulation time.
- Real demo-config host federates all six sub-lines at the shared natural 120s
  boundary; each federated runtime equals its standalone replica (evidence 05).
- Full ASSY regression oracle stays green (354) — domain semantics (conveyor
  literals PRE-ASSY..AP11, SSO2/RSO2, AP04 genealogy, AP06 retest, AP08
  reinspect, AP11 QC, failed_final, RELEASED/LINE_OUT, evidence, deterministic
  timestamps) unchanged.

## 4. Identity / isolation

- G1 structural paths resolve through `Workspace.resolve_scope`; adapter
  identity equals its registered structural scope; registration order is the
  deterministic canonical scope order.
- Six runtimes/configs/RNG seeds isolated; no direct cross-scope mutation
  (advancing one sub-line leaves the others untouched).
- Structural identity remains distinct from PIM canonical identity; no PIM
  fabrication; demo metadata stays deployment metadata.
- Identity drift/mismatch (incl. drift during `advance_to`) fails closed through
  the existing G4 C01/C02/C03 rules.

## 5. Test / regression results (evidence 07)

| Suite | Result |
|---|---|
| New G5 tests | **24 passed** |
| G4 composition tests | **56 passed** |
| G1 workspace | **32 passed** |
| G2 provenance | **36 passed** |
| G3 Observation/Event/Alarm (+ M5 + alarm) | **328 passed** |
| Core graph/port/runtime | **21 passed** |
| Discrete runtime/scheduler | **279 passed** |
| Complete ASSY regression oracle | **354 passed** |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1873 passed** (0 failures) |
| Compile check | PASS (no configured ruff/mypy/black) |

## 6. STOP-condition assessment (evidence 06)

None triggered. No AssyLineRuntime rewrite; no fractional dwell/hidden time
rewrite; no new synchronization policy; ASSY stays container-only; G1–G4
contracts intact; no demo-policy-to-plant-truth leakage; no G6+.

## 7. Acceptance (Issue #50 criteria)

| Criterion | Result |
|---|---|
| Exact TIPA → ASSY → six sub-line hierarchy (G1 authority) | PASS |
| ASSY container-only, cannot register as participant | PASS |
| Six sub-lines executable-capable with canonical structural paths | PASS |
| Six adapters wrap six existing runtimes (no rewrite) | PASS |
| Adapter current_time_s == wrapped runtime time | PASS |
| Representative standalone vs federated parity at supported boundaries | PASS |
| Runtime/config/feed/RNG isolation across sub-lines | PASS |
| No direct cross-scope mutation | PASS |
| Identity drift/mismatch fails closed via existing G4 rules | PASS |
| Full ASSY regression oracle green | PASS (354) |
| No G6+; no AssyLineRuntime rewrite | PASS |
| G1/G2/G3/G4 + continuous baselines green | PASS (32/36/328/56/61) |
| Working tree clean and branch/head pushed | PASS (after push) |

## 8. Evidence

`.ai-harness/sa-review/evidence/VF-vNEXT-G5/` — 7 files (01…07).

## 9. Final status

```text
VF-vNEXT-G5 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. G6 is NOT started.
