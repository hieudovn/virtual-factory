# VF-OC-SA-GOV-01 — SA governance handoff

**Date:** 2026-11-03. **Update:** Capacity OS current guidance at `86e2602a903d5110ec50d073b3c657fe84f5e41a` is advisory for implementation tasks; SA chooses a lighter format for governance/design/research/audit. **Approval:** [VF #139](https://github.com/hieudovn/virtual-factory/issues/139). **Base:** #131 `6ca569b4362235edd4d05e61feccba7ddadcbb4b` (stacked, unmerged). **Current main:** `04fb9413bd5af3c4f0457047267a60b3ea4e94fe`.

## Deliverable
Additive VF OpenCode/VPS issue guidance documented in `docs/governance/VF_OPENCODE_VPS_TASK_AUTHORING_ADDENDUM_v1.md`, preserving VF harness P01–P24, exact-head and evidence contracts. No executable/config/test/runtime changes.

## Compatibility decisions

Existing VF task contract and P01–P24 remain mandatory for PM implementation tasks. OpenCode additional metadata is optional, not a global requirement for design, feasibility or governance Issues. Issue #138 is narrowed to optional schema/preflight metadata guards, without changing task gate, CI, derived status or PR readiness. Issue #133 is no longer dependent on #138.

## Known gaps
Current VF `required_branch` vs reference `work_branch`; resume and budget only manual; draft PR is explicitly NOT READY by present harness; CI harness self-tests have `|| true`. Implementation and tests delegated to [#138](https://github.com/hieudovn/virtual-factory/issues/138); **BLOCKED** until preconditions. Contract QA [#133](https://github.com/hieudovn/virtual-factory/issues/133) remains BLOCKED pending G1A design baseline and correct task JSON.

## Evidence and status
SA remote preflight recorded on #139 before mutation. GitHub exact-head PR and CI results are tracked on its PR/issue comments **after** the commit; no assertion of tests/merge in this report. No production changes; no deployments or edits to external repositories.

## Post-design merged baseline reconciliation — 2026-11-03

PR #131 governance and PR #132 G1A Design have been merged into `main`. Current baseline for PR #140 is `848eb1c11bd305a98877573fabeff64350a885e4`; this branch includes that main commit as a parent (no history rewrite) and SA task expected_base_sha has been repinned accordingly. PR #140 now targets `main`. The older stacked-base CI cannot count for this new base; repeat exact-head SA Design Gate and full VF CI before merge. Scope remains three governance docs/SA task paths, with no executable harness changes.
