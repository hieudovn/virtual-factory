# 07 — Final Authoritative Branch + SHA

## Reconciliation result

- **Reconciliation merge commit:** `43365214144cbf623252158cbbb7ff0dc3ef59ae`
- **Parents:** `fda1db44b17a7f61da2393e00cdf20bb7998b7ea` (canonical `main`) +
  `240d8db5eff481f1d4d8810d275214077031e72a` (accepted ASSY lineage)
- **Branch:** `feature/vf-repo-lineage-01` (pushed to origin for PR review)

## Post-reconciliation authoritative state

| Item | Value |
|---|---|
| Canonical integration target | `main` (to be advanced by normal non-force merge of this PR) |
| Reconciled candidate head | `43365214144cbf623252158cbbb7ff0dc3ef59ae` |
| Accepted ASSY lineage | fully contained in the candidate head (six-sub-line + MES v1.1) |
| Single-sub-line MES-01 demo | preserved (`assembly/demo_assy_mes/`, `/demo-assy-mes/*`) |
| Regression | 1647 passed / 0 failed on the candidate head |

## What remains for canonical integration

The candidate head is proven safe. Advancing canonical `main` is performed via a
normal PR merge (base `main`, head `feature/vf-repo-lineage-01`) — no force-push,
no history rewrite. That merge is the SA/operator-authorized step that makes
`main` authoritative again.

## Legacy branches (NOT deleted, per governance)

- `docs/m6-s01-tipa-baseline` — retained (SA-accepted ASSY lineage provenance).
- `feature/dm-demo-assy-mes-01/02/03-evidence` — retained.
- `feature/shw-vf-ph00` — retained (SHW-VF-PH00 remains BLOCKED pending this gate).
