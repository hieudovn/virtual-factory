# 01 — Ancestry / Commit Graph Summary

## Lineage topology

```
17a1d9ecafb170fa94e8d01a1f12d84e79982773   ← merge-base (chore/ai-pm-execution-harness, "Merge docs/tipa-demo-timeline-2026-08")
        │
        ├──────────────────────────────────────────────┐
        │                                              │
        ▼                                              ▼
  fda1db44b17a7f61da2393e00cdf20bb7998b7ea       240d8db5eff481f1d4d8810d275214077031e72a
  origin/main (canonical)                        origin/docs/m6-s01-tipa-baseline (accepted ASSY lineage)
        │                                              │
        └───────────── reconciliation ─────────────────┘
                       │
                       ▼
              43365214144cbf623252158cbbb7ff0dc3ef59ae   ← VF-REPO-LINEAGE-01 merge commit
```

## Verified ancestry facts (git, machine-derived)

| Fact | Command | Result |
|---|---|---|
| current `main` HEAD | `git rev-parse origin/main` | `fda1db44b17a7f61da2393e00cdf20bb7998b7ea` |
| accepted ASSY lineage HEAD | `git rev-parse origin/docs/m6-s01-tipa-baseline` | `240d8db5eff481f1d4d8810d275214077031e72a` |
| merge-base | `git merge-base main docs/m6-s01-tipa-baseline` | `17a1d9ecafb170fa94e8d01a1f12d84e79982773` |
| `main` ancestor of baseline? | `git merge-base --is-ancestor main baseline` | NO (exit 1) |
| baseline ancestor of `main`? | `git merge-base --is-ancestor baseline main` | NO (exit 1) |
| reconciliation merge parents | `git log -1 --format=%P 4336521` | `fda1db44… 240d8db…` |

## Unique commits on each side after merge-base

### `main` (17a1d9e..fda1db44) — exactly ONE commit
- `fda1db44` — `VF-DM-DEMO-ASSY-MES-01: deterministic ASSY customer demo for MES (#22)`
  (squash-merge of PR #22; adds the single-sub-line `assembly/demo_assy_mes/`
  package + `/demo-assy-mes/*` API + `demo_assy_mes.html` + MES-01 evidence).

### accepted ASSY lineage (17a1d9e..240d8db) — the full six-sub-line TIPA ASSY lineage
Key accepted gates (in order): I09-* (UI), OPS-01 → OPS-04-C01-R2 (operation
execution + quality decision semantics), MANUAL-E2E-01, AUTO-EQUIV-01(+R1),
AUTO-TIME-01A/B/C/D(+C01/C02), M6-INT-01(+C01), DEMO-CANDIDATE-01(+P1),
MES-INT-02/02A-VF, VF-DEPLOY-01, VF-CONTRACT-FINALITY-01, TIPA-DEMO-LIVE-01,
and finally MES-02 (PR #23 → `c3c8bb6`) and MES-03 (PR #24 → `240d8db`,
six-sub-line ASSY + MES contract `tipa-assy-demo-v1.1`).

## PR merge provenance (verified)

| PR | Title | Merged into | Merge commit |
|---|---|---|---|
| #22 | VF-DM-DEMO-ASSY-MES-01 (single-sub-line customer demo) | `main` | `fda1db44` (squash) |
| #23 | VF-DM-DEMO-ASSY-MES-02 (six-sub-line MES bridge) | `docs/m6-s01-tipa-baseline` | `c3c8bb6` |
| #24 | VF-DM-DEMO-ASSY-MES-03 (evidence contract v1.1) | `docs/m6-s01-tipa-baseline` | `240d8db` |

## Why the two lineages diverged

The six-sub-line TIPA ASSY work (M6-S04B/OPS/MES-02/MES-03) was merged into the
SA-authorized integration branch `docs/m6-s01-tipa-baseline`, while MES-01's
single-sub-line customer demo (PR #22) was merged directly into `main`. Neither
was reconciled into the other — producing two equally-authoritative ASSY
implementations (Issue #25's exact concern).
