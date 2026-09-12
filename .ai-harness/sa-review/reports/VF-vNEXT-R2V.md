# VF-vNEXT-R2V — ASSY Functional & UI Validation before R3

Gate type: **VALIDATION ONLY** (no product code change, no redesign, no R3).
Issue: https://github.com/hieudovn/virtual-factory/issues/82

- Repository: `hieudovn/virtual-factory`
- Branch: `feature/vf-vnext-r2v`
- Base (technical branch point / validated source): `4fc81e72780fe14ba5532407fdc8113b44385617`
- Contract commit: `db55c36` (`.ai-harness/tasks/VF-vNEXT-R2V.json`)
- Validation head: 12697dd9462e68e85761bee9fe25bfb68d18ce64
- Authority refs: R0 (Issue #78, CLOSED/frozen) + R2 (Issue #80, accepted at 4fc81e72780fe14ba5532407fdc8113b44385617)

## 1. What was validated

Functional + browser evidence that the rebuilt canonical ASSY experience at the R2
source still preserves the previously accepted rich ASSY simulation configuration and
capabilities and the agreed six-independent-sub-line behaviour, now running on ONE
canonical TIPA `RuntimeSession`.

Validation ran against a live product server
(`python -m virtual_factory.main serve --host 127.0.0.1 --port 8099`) and through the
real product path (`/workspaces` -> `/assy-demo`), plus a deterministic in-process
driver recorded in `evidence/VF-vNEXT-R2V/generate_evidence.py`.

## 2. Changed files (allowed paths only)

- `.ai-harness/tasks/VF-vNEXT-R2V.json` (contract)
- `.ai-harness/sa-review/evidence/VF-vNEXT-R2V/**` (01..06 `{md,json}`,
  `07-visual-sanity.md`, `generate_evidence.py`, `shot-frame-a.png`, `shot-frame-b.png`)
- `.ai-harness/sa-review/reports/VF-vNEXT-R2V.md`
- `.ai-harness/sa-review/CURRENT.md`
- `.ai-harness/regression/vnext_baseline_manifest.json` (gate context only)

`src/`, `tests/`, `configs/`, `docs/`, `deploy/`, `examples/` were **not modified**
(`verify_changed_files.py` PASS).

## 3. Results

| Area | Acceptance | Result | Evidence |
|---|---|---|---|
| V01 launch/navigation/identity | same workspace/run/scenario/profile; no time advance; no second runtime | PASS | `01-launch-identity.md/.json` |
| V02 Frame A six lines | exactly six live sub-lines, independent state, one parent run | PASS | `02-six-line-overview.md/.json` |
| V03 Frame B 2D parity | 12 positions per frame, WIP motion, AP04 join + genealogy, rendered == positions[] | PASS | `03-2d-wip-motion.md/.json` |
| V04 inspector/quality/genealogy | read models + retained OPS-03/OPS-04 thin bindings; selection presentation-only | PASS | `04-inspector-quality-genealogy.md/.json` |
| V05 lifecycle | STEP same session; RESET same run_id baseline; NEW ATTEMPT fresh run_id; REPLAY deterministic; SH-WTP isolation | PASS | `05-lifecycle.md/.json` |
| V06 six-line independence | hold SL03 -> SL03 frozen in Frame A/B, five continue, release resumes | PASS | `06-six-line-independence.md/.json` |
| V07 browser/visual sanity | readable Frame A/B, WIP motion understandable, no major clipping, no severe console errors | PASS (1 MINOR, 3 OBSERVATION) | `07-visual-sanity.md`, `shot-frame-a.png`, `shot-frame-b.png` |

Key facts:
- Opening the rich UI: **0 federations -> 1 federation**, `step_count` unchanged ->
  one run authority, no second runtime, no time advance.
- Frame A: six lines at the same simulation time with independent WIP/motor state.
- Frame B: 12 accepted positions in every frame; SSO2 enters at the first machine and
  advances one station per step; AP04 JOIN creates `MTR-0001` (<- `SSO2-0001` +
  `RSO2-0001`) at step 5, which then moves `AP05 -> AP06 -> AP07 -> AP08`; rendered
  occupancy equals the canonical `positions[]` truth in every frame.
- Lifecycle: shell/rich STEP act on the same session; RESET keeps the run id and
  returns all six lines to the fresh profile baseline; NEW ATTEMPT and REPLAY create
  fresh run ids with equivalent/deterministic state; SH-WTP switching leaves the TIPA
  run untouched.
- Independence: while `ASSY-SL03` is held, Frame A shows SL03 frozen (120 s, 0 motors)
  and the other five at 720 s with motors created; Frame B SL03 frozen vs Frame B SL01
  advanced (720 s, 2 motors, 7 occupied positions); release resumes SL03 (840 s).

## 4. Deferred capabilities (unchanged, fail closed)

- Observation / MES: HTTP 503, `deferred_to: R3`.
- jam / recover / run-to-terminal / scenario-change: HTTP 409, `deferred_to: R4`.

All deferred responses carry `legacy_runtime_authority: false`; no legacy controller
is constructed. Explicitly NOT validated in R2V because they are R3/R4 scope:
observation/MES write paths, jam/recovery/run-to-terminal, OEE and scenario mutation.

## 5. Defects

- BLOCKER: none. MAJOR: none.
- MINOR M1: one unhandled console error `404 GET /vnext/runs/current?workspace=TIPA`
  on rich-page load (optional run-context fetch, no functional impact).
- OBSERVATION O1..O3: viewport-scale pan/zoom need, harness pointer-interception
  artefact, no JS exceptions. Details in `07-visual-sanity.md`.

Per the gate contract, no defect was corrected inside this gate
("No automatic correction of any defect found").

## 6. Regression

- Full suite: `python -m pytest -q -p no:cacheprovider tests`.
- Canonical baseline: `python .ai-harness/regression/run_vnext_baseline.py --json-output
  .ai-harness/traces/vnext_baseline_r2v.json` at the pushed head, with the manifest gate
  context set to `.ai-harness/tasks/VF-vNEXT-R2V.json` + `changed_files_base=4fc81e72780fe14ba5532407fdc8113b44385617` (the baseline also runs
  `checks_preflight` and `checks_changed_files`, i.e. the R2V harness gate).

Regression numbers are machine-derived at the pushed head and recorded in the SA
submission message for this gate.

## 7. Statements

- No product code changed: `src/`, `tests/`, `configs/`, `docs/`, `deploy/`,
  `examples/` untouched.
- No R3 work started; no redesign; no rebase onto `main`; no push to `main`; no merge.
- One product-path TIPA run authority; no legacy runtime authority on the product path;
  no second session/federation/runtime observed.

Authority unchanged: `vf_runtime_authorization = NOT_AUTHORIZED`;
`site_authorized_execution = NOT_AUTHORIZED`;
`whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`.

## 8. Verdict

`ASSY_RICH_SIMULATION_VALIDATED` — the canonical TIPA ASSY rich experience preserves
the accepted Frame A / Frame B behaviour, six-line independence and lifecycle
semantics on one canonical session, with no BLOCKER/MAJOR defect. Ready for SA review;
R3 is NOT started.
