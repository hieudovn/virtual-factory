# VF-vNEXT-G26 — UX Issue List

Classification: BLOCKER / MAJOR / MINOR / OBSERVATION.
Only BLOCKER/MAJOR must be fixed before PASS. G26 allowed only small fixes.

---

## MAJOR-1 — Backend lifecycle actions `new_attempt` / `replay` not exposed in the shell UI  → FIXED

- Symptom: The run-control bar offered only `STEP / RESET / STOP`. The backend
  supports `new_attempt` and `replay`. After pressing `STOP` the session became
  terminal and the UI disabled STEP/RESET, leaving **no in-UI recovery path**;
  deterministic replay could not be demonstrated in the browser.
- Impact: A UAT operator could press STOP and be stuck; UAT-02/UAT-06/UAT-08
  could not be completed in the UI.
- Fix (small): added `♻ NEW ATTEMPT` and `⟲ REPLAY` buttons wired to the existing
  `POST /vnext/workspaces/{id}/control` actions; enablement: both enabled when a
  workspace is selected.
- Verified: STOP -> `stopped`; NEW ATTEMPT -> fresh `created` run, STEP
  re-enabled; REPLAY -> fresh run identity.
- Files: `src/virtual_factory/ui/static/workspace_shell.html`,
  `src/virtual_factory/ui/static/workspace_shell.js`.

## MINOR-1 — Initial load did not select a workspace  → FIXED

- Symptom: On first load/reload the code read `selectEl.value` *after* rebuilding
  the option list, so the browser's auto-selected first option made the
  "no selection" branch unreachable. The monitor view was only populated by the
  3s poll, and the run-control target stayed `no workspace` until the operator
  changed the selector.
- Impact: up to ~3s blank monitor; misleading "no workspace" label.
- Fix (small): capture the previous selection before rebuilding, then always call
  `select(preferred)` (previous if still valid, else first workspace).
- Verified (after clearing the browser cache): on load the view renders
  immediately and the run-control target shows `TIPA`.
- Files: `src/virtual_factory/ui/static/workspace_shell.js`.

## MINOR-2 — Horizontal overflow on narrow viewports (not fixed)

- Symptom: below ~700px viewport width the "Key current values / status" table
  overflows by ~38px (wide scope paths + long keys).
- Impact: narrow-window/demo-on-small-screen cosmetics only. At desktop widths
  1024 / 1280 / 1440 there is **0 px** horizontal overflow.
- Decision: not fixed (avoid broad CSS redesign; desktop demo target).

## OBSERVATION-1 — Empty fidelity/status cells for TIPA structure rows

- TIPA sub-line structure rows have no fidelity/status (they are structural
  sub-lines, not fidelity-tagged scopes), so those two columns render empty.
- Suggestion (not done): render an explicit `—` placeholder. Cosmetic only.

## OBSERVATION-2 — Native `<select>` truncates long option text at narrow widths

- Standard native-select behaviour; the full text is visible at desktop widths.
  No action.

## OBSERVATION-3 — `/assy-demo` separation is clear

- Both the inline structure note and the link label state that `/assy-demo` is a
  separate legacy demo runtime ("NOT this session"; identity/state not shared).
  No action.

## OBSERVATION-4 — Browser cache for static JS/CSS

- The shell serves `workspace_shell.js/css` via direct routes (no server-side
  caching) but the **browser** caches them; after editing JS a hard reload (or
  cache clear) is required. This is an existing repo convention (same as
  `assy_demo.js`), documented for operators. No product change.

---

## Summary

| ID | Class | Fixed? |
|---|---|---|
| MAJOR-1 lifecycle actions not exposed | MAJOR | YES (small fix) |
| MINOR-1 initial load no selection | MINOR | YES (small fix) |
| MINOR-2 narrow-viewport overflow | MINOR | No (desktop target) |
| OBSERVATION-1 empty fidelity/status cells | OBSERVATION | No |
| OBSERVATION-2 native select truncation | OBSERVATION | No |
| OBSERVATION-3 /assy-demo separation clear | OBSERVATION | n/a |
| OBSERVATION-4 browser cache after JS edit | OBSERVATION | No (documented) |

No BLOCKER. The one MAJOR was fixed; all UAT scenarios pass.
