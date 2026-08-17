# AUTO-TIME-01D-C02 — Demo Environment RCA Correction

## 1. Baseline / Head

| Field | Value |
|---|---|
| Task ID | `AUTO-TIME-01D-C02` (correction within AUTO-TIME-01D) |
| Repository | `hieudovn/virtual-factory` |
| Branch | `docs/m6-s01-tipa-baseline` |
| Baseline (prior correction head) | `32c53259d6d4d991aaa5d06796ad653c66699c1b` |
| Head (this correction) | `<exact SHA>` (descends from C01 commit `3410fd4`, which descends from `32c5325`) |
| Local HEAD at execution | `3410fd4556cf6c4071b5a9cd1ce68fc8e09ac227` |
| `origin/main` at execution | `17a1d9ecafb170fa94e8d01a1f12d84e79982773` (unchanged by this gate) |

Baseline verified: `32c5325` is an ancestor of the execution HEAD; local HEAD
equals `origin/docs/m6-s01-tipa-baseline`.

## 2. Production code changed

**NO.** This correction touches documentation / evidence only.

## 3. Corrected primary RCA

The prior C01 report (`AUTO-TIME-01D-C01.md`) remains as historical evidence
(not deleted). Its earlier framing — `RC-A — wrong URL / entrypoint`,
`RC-B — view nuance` — is **amended** by the confirmed operational root cause:

```text
PRIMARY ROOT CAUSE:
Execution environment was not reproduced in a new PM/session context.

Required S04B feature flag was not restored:
VF_ENABLE_S04B_OVERVIEW=1

Effect:
ASSY application ran in fallback/alternate S04 view and therefore looked
materially different from the approved 14-Aug Frame A/B UI.

Recovery:
restore required environment flag
→ restart application
→ serve on port 8000
→ open /assy-demo
→ canonical approved ASSY UI restored.
```

Confirmed operational sequence (session evidence, 2026-08-17):

1. AUTO-TIME prompts were executed in a new session where the required UI
   feature environment flag was not restored.
2. Without `VF_ENABLE_S04B_OVERVIEW=1`, `GET /assy-demo/overview`,
   `GET /assy-demo/sub-lines`, `GET /assy-demo/sub-line/{id}` returned 404 and
   the ASSY UI rendered the alternate/fallback S04 single-line view.
3. After restoring the flag and restarting the application on port 8000, the
   approved ASSY UI (Frame A — 6 parallel sub-lines; Frame B — sub-line detail
   with Simulation panel and AUTO/MANUAL/ASSISTED mode; Inspector with
   Overview/Quality/History/Genealogy) appeared correctly.

Repository behavior is consistent: the S04B endpoints are gated in
`src/virtual_factory/ui/api.py` by
`os.environ.get("VF_ENABLE_S04B_OVERVIEW", "0") == "1"`.

## 4. Secondary provenance risks

Wrong URL `/` versus `/assy-demo` remains a valid general provenance risk — `/`
serves the generic Virtual Factory SCADA dashboard (`index.html`), which is a
different UI surface from the TIPA ASSY UI (`assy_demo.html`). It is
**not** the primary cause of this incident, but should still be avoided when
validating the ASSY demo.

## 5. Demo Environment Contract

Created:

```text
.ai-harness/sa-review/evidence/AUTO-TIME-01D/demo-environment-contract.md
```

Records: repository, branch, required feature flag `VF_ENABLE_S04B_OVERVIEW=1`,
expected port `8000`, canonical route `/assy-demo`, generic route `/`, canonical
ASSY assets, expected ASSY behavior, failure mode, recovery steps, flag gate
source (`api.py`), observed endpoint behavior with/without the flag, the
session-derived launch command, and the harness lesson.

## 6. Timing / runtime evidence unchanged

No timing/runtime evidence was modified by this correction. The AUTO-TIME-01D
timing evidence set is unchanged:

- `evidence/AUTO-TIME-01D/timing-validation.md`
- `evidence/AUTO-TIME-01D/ui-validation.md`
- `evidence/AUTO-TIME-01D/validate_timing_01d.py`
- `evidence/AUTO-TIME-01D/ui/`

This gate adds only `demo-environment-contract.md` under the same evidence
directory, plus the C02 report and the SA Review Inbox update. No test rerun
was required by the task scope; no timing/runtime behavior was asserted or
changed.

## 7. Working-tree note (pre-existing, untouched)

A single pre-existing untracked file existed at execution start and is not part
of this gate: `docs/ui/evidence/i09-p02-c03r/EV1_frame_b_clean.png`. It is not
touched, staged, or committed by this correction.

## 8. Recommendation

```text
AUTO-TIME-01D READY FOR SA CLOSURE
```
