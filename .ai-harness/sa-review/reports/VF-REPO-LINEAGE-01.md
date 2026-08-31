# VF-REPO-LINEAGE-01 — Reconcile accepted ASSY lineage back to canonical main

| Field | Value |
|---|---|
| Task ID | `VF-REPO-LINEAGE-01` (GitHub Issue #25) |
| Repository | `hieudovn/virtual-factory` |
| Gate | repository-integrity reconciliation (one gate only) |
| Reconciliation branch | `feature/vf-repo-lineage-01` |
| Reconciliation merge commit | `43365214144cbf623252158cbbb7ff0dc3ef59ae` |
| Parents | `fda1db44…` (main) + `240d8db…` (accepted ASSY lineage) |
| Merge method | normal non-force 3-way merge (no rebase/squash/force-push) |
| Full regression | 1647 passed / 0 failed |

## 1. Objective

Reconcile the accepted six-sub-line ASSY + MES v1.1 lineage
(`docs/m6-s01-tipa-baseline`) back into canonical `main`, which currently only
carries the MES-01 single-sub-line `demo_assy_mes` demo. Preserve BOTH lineages;
no accepted behavior may be dropped.

## 2. Lineage (verified)

- current `main`: `fda1db44b17a7f61da2393e00cdf20bb7998b7ea`
- accepted ASSY lineage: `240d8db5eff481f1d4d8810d275214077031e72a`
- merge-base: `17a1d9ecafb170fa94e8d01a1f12d84e79982773`
- `main` after merge-base = exactly one commit: `fda1db44` (MES-01, PR #22).
- baseline after merge-base = the full six-sub-line TIPA ASSY lineage
  (OPS-01→OPS-04, M6-INT-01, DEMO-CANDIDATE-01, VF-DEPLOY-01,
  VF-CONTRACT-FINALITY-01, TIPA-DEMO-LIVE-01, MES-02 PR #23, MES-03 PR #24).

## 3. Conflict classification (3-way merge)

Only 3 files conflicted; all **mechanical** (no semantic conflict):

| File | Nature | Resolution |
|---|---|---|
| `observation/projections/mes.py` | baseline is strict superset of MES-01 mappings | take baseline |
| `ui/api.py` | disjoint endpoint blocks | union: keep `/demo-assy-mes/*` AND `/assy-demo/*` |
| `.ai-harness/sa-review/CURRENT.md` | add/add governance artifact | combined inbox |

All other differences were unique-to-main (preserved) or unique-to-ASSY
(preserved), or unchanged. Full classification in evidence §02.

## 4. Safety proof

- **No STOP condition triggered** (evidence §04): no semantic conflict; no
  uncertain provenance (PR #22/#23/#24 merge SHAs verified); no accepted feature
  dropped (`demo_assy_mes` and six-sub-line both retained); regression green
  with no unrelated production change; no force-push; no SA-acceptance ambiguity.
- **Tree verification** (evidence §07): `git ls-tree HEAD` shows
  `assembly/demo_assy_mes/` (9 files) AND the six-sub-line modules,
  `configs/plants/tipa_assy_demo.yaml`, `docker-compose.assy.yml`, and the
  MES v1.1 `mes.py` mappings all present.
- **Targeted tests:** 96 passed (MES-01 + six-sub-line MES + ASSY runtime).
- **Full regression:** 1647 passed / 0 failed on the reconciled head.

## 5. Reconciliation outcome

The candidate head `4336521` on branch `feature/vf-repo-lineage-01` is proven
safe and is ready to advance canonical `main` via a **normal non-force PR merge**
(base `main`, head `feature/vf-repo-lineage-01`). This satisfies Issue #25
acceptance criterion A.

## 6. Governance compliance

- One gate only: YES.
- SHW-VF-PH00 not modified (remains BLOCKED); SHW-VF-PH01 not started: YES.
- No runtime architecture redesign: YES.
- No legacy branch deletion: YES (`docs/m6-s01-tipa-baseline` and feature
  branches retained).
- No force-update of `main`: YES (normal merge commit; canonical integration via PR).
- No silent semantic resolution: YES (all conflicts documented + classified).

## 7. Evidence

`.ai-harness/sa-review/evidence/VF-REPO-LINEAGE-01/`:
`01-ancestry-commit-graph.md`, `02-changed-file-classification.md`,
`03-reconciliation-strategy.md`, `04-conflict-analysis.md`,
`05-targeted-test-results.md`, `06-full-regression.md`,
`07-final-authoritative-state.md`.

## 8. Final status

```text
VF-REPO-LINEAGE-01 — READY FOR SA REVIEW
```

Candidate head: `43365214144cbf623252158cbbb7ff0dc3ef59ae`
Branch: `feature/vf-repo-lineage-01` (base `main`)
Regression: 1647 passed / 0 failed

The PM does not self-certify COMPLETE/CLOSED. Advancing canonical `main` is the
SA-authorized PR merge; SHW-VF-PH01 is not started.
