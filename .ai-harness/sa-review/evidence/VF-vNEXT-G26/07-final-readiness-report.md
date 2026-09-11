# VF-vNEXT-G26 — Final Readiness Report

Gate: `VF-vNEXT-G26` — Comprehensive Validation & UAT Readiness (Issue #77)
Branch: `feature/vf-vnext-g26`
Base: G25 head `3c83176ce2a8a504637dfe674ea30b2332bc7968`
Production base: canonical `origin/main` @ `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (inspected, not merged)

## Verdict

**UAT_DEMO_READY**

The accepted integrated multi-workspace MVP is demonstrable to a UAT audience on
the accepted architecture. No BLOCKER remains. The single MAJOR UX defect found
during this gate (no in-UI recovery/replay exposure after `STOP`) was fixed
inside G26. All eight UAT scenarios pass. The demo-scale stability smoke is
green. The complete canonical regression baseline is green at the pushed head
(see `06-regression-summary.md`).

## What was validated

| Dimension | Deliverable | Result |
|---|---|---|
| Test plan / coverage | `01-test-plan-coverage-matrix.md` | complete (no G1–G25 duplication) |
| Browser functional | `02-browser-functional-results.md` | PASS (A1–A18) |
| Compact UAT | `03-uat-checklist-results.md` | PASS (UAT-01..UAT-08) |
| UX sanity | `04-ux-issue-list.md` | 0 BLOCKER; 1 MAJOR fixed; 1 MINOR fixed; 1 MINOR + 4 OBSERVATION recorded |
| Stability / readiness | `05-stability-readiness.md`, `stability-smoke.out`, `stability-results.json` | PASS (all_ok true, 17/17, 270 steps, 20 switches) |
| Regression | `06-regression-summary.md` | full canonical vNext baseline PASS at head |

## Scope discipline

- Production Python was **not** modified. The only `src/` changes are the two
  static shell assets (`workspace_shell.js`, `workspace_shell.html`), within the
  G26 allowlist.
- No new pytest module was added; G26 deliberately does not duplicate G1–G25
  coverage. The canonical baseline (including the full suite) is the technical
  safety net, and the manifest gate context now points at the G26 task contract.
- Frozen boundaries unchanged: no gateway routing / production export /
  multi-gateway / store-and-forward; no SH-WTP whole-plant or site-faithful work;
  no T110/Line2; no `/assy-demo` unification; no G4/G19/coupling redesign; no
  distributed execution; no broad UI redesign; no PIM/MES change.

## Authority (unchanged, restated for the record)

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

VF remains a simulation/observer platform. SH-WTP assumed/scenario topology and
fidelity labels are **not** site truth; PIM remains authoritative.

## Residual items for SA awareness (non-blocking)

1. MINOR-2: "Key current values / status" table overflows ~38 px below ~700 px
   viewport width (0 px at 1024/1280/1440). Demo target is desktop; not fixed.
2. OBSERVATION-1: TIPA structure rows show empty fidelity/status cells
   (structural sub-lines have no fidelity tags) — cosmetic.
3. OBSERVATION-4: static JS/CSS are browser-cached; after editing them a hard
   reload is required (existing repo convention, documented).
4. `/assy-demo` remains a separate legacy demo runtime and is never re-pointed by
   the shell.

## Gate status

`VF-vNEXT-G26 — READY FOR SA REVIEW` (verdict `UAT_DEMO_READY`). No PR opened,
nothing merged, no next gate started. Awaiting SA disposition.
