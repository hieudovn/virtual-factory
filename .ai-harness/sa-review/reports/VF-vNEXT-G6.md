# VF-vNEXT-G6 — Implement Shared Hierarchical UI Primitives

| Field | Value |
|---|---|
| Task ID | `VF-vNEXT-G6` (GitHub Issue #51) + C01 |
| Program | Implementation phase (G6; only authorized implementation gate after G5) |
| Required base (branch) | `d1419cec3bd87d283ee9dcb03c412479a794359d` (accepted G5-C01 head) |
| Branch | `feature/vf-vnext-g6` |
| Production base (`origin/main`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| Model | Flash |
| G7+ started | **NO** |

## 1. Objective

Implement shared hierarchical UI primitives — a read-only UI context model
derived from the accepted G1 Workspace/StructuralPath authority, a reusable
plain-JS hierarchy navigator + context breadcrumb, and additive integration
seams for the TIPA ASSY view and the continuous dashboard — preserving
ASSY/continuous domain rendering and behavior and implementing NO G7
run-control/replay.

## 2. Implementation (additive, inside `src/virtual_factory/ui/`)

- `hierarchy.py` — pure read-only projection/serialization of the G1
  Workspace/Scope tree (`workspace_to_dict`, `simulation_scope_to_dict`) and
  path-qualified selection context (`structural_context`, `root_only_context`);
  canonical `StructuralPath` preserved; no second model; no runtime mutation.
- `api.py` (additive) — three read-only GET endpoints:
  `/api/ui/hierarchy`, `/api/ui/context`, `/api/ui/context/continuous`.
- `static/hierarchy.js` — shared, domain-agnostic primitives
  (`renderNavigator`, `renderBreadcrumb`); container vs executable from G1
  capability booleans; path-qualified selection; expand/collapse.
- `static/assy_context.js` — additive ASSY seam: renders the canonical
  hierarchy and, for an executable `ASSY-SLxx` selection, forwards to the
  EXISTING backend authority `POST /assy-demo/select` (then updates breadcrumb
  + existing card selection only after backend acceptance — fail-safe). Never
  resets/reconstructs/steps a runtime. Workspace/container selection is
  structural-context-only and never calls `/assy-demo/select`. (C01)
- `static/continuous_context.js` — additive continuous seam: renders the
  truthful ROOT-ONLY context (no invented hierarchy).
- `index.html` / `assy_demo.html` — additive context mounts + script tags;
  `styles.css` / `assy_demo.css` — additive styles. `app.js` and `assy_demo.js`
  are NOT modified (ASSY/continuous domain rendering preserved).

## 3. Inspector vs Monitoring + capability

- Inspector = object-centric (object appended only when actually selected and
  resolvable in the selected scope); Monitoring = scope-centric (no fabricated
  object). Container-only scopes are selectable for context but never imply
  execution (`executable_controls_implied=False`).

## 4. Compatibility / no redesign

Existing dashboard routes/APIs, ASSY routes/behavior, and static references are
preserved. No frontend framework migration. No G7 run-control/replay API.

## 5. Test / regression results (evidence 07)

| Suite | Result |
|---|---|
| New G6 tests | **31 passed** (incl. C01) |
| Existing UI/API + S04B gating tests | **134 passed** |
| G5 federation tests | **26 passed** |
| G4 composition tests | **56 passed** |
| G1 workspace | **32 passed** |
| G2 provenance | **36 passed** |
| G3 Observation/Event/Alarm (+ M5 + alarm) | **328 passed** |
| Complete ASSY regression oracle | **354 passed** |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1906 passed** (0 failures) |
| Compile check | PASS (no configured ruff/mypy/black) |

## 6. STOP-condition assessment (evidence 06)

None triggered. No new UX/navigation model; continuous hierarchy is truthful
root-only (no invented plant structure); ASSY UI additively adapted (not
rewritten); G1 structural identity intact; no new run/scenario lifecycle
semantics; no G7/G8+; no framework migration.

## 7. Acceptance (Issue #51 criteria)

| Criterion | Result |
|---|---|
| Recursive hierarchy serialization preserves canonical StructuralPath | PASS |
| Deterministic hierarchy order from G1 | PASS |
| Container-only vs executable capability correct | PASS |
| Path-qualified selection; no ambiguous bare-id authority | PASS |
| TIPA hierarchy exactly TIPA -> ASSY -> six sub-lines | PASS |
| ASSY-SLxx selection maps to same existing sub-line context (no runtime reconstruct) | PASS |
| Structural selection does not change ASSY domain semantics | PASS |
| Continuous retains behavior; no invented hierarchy | PASS |
| Inspector object vs Monitoring scope context distinct | PASS |
| No G7 run-control/replay/orchestration API | PASS |
| No G8+/G9/G10 scope | PASS |
| G1–G5 + ASSY oracle + continuous baselines green | PASS |
| Working tree clean and branch/head pushed | PASS (after push) |

## 8. Evidence

`.ai-harness/sa-review/evidence/VF-vNEXT-G6/` — 8 files (01…08; 08 = C01
corrections: hierarchy ASSY-SLxx selection bound to existing /assy-demo/select
authority).

## 9. Final status

```text
VF-vNEXT-G6-C01 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. G7 is NOT started.
