# AUTO-TIME-01D — UI Smoke / Rehearsal Validation

Validated against the **canonical 14/8 UI** served from `docs/m6-s01-tipa-baseline`
(`src/virtual_factory/ui/static/assy_demo.html/js/css`, blob `3de7f8ab…`).
UI provenance re-verified: served content === workspace === tipa-baseline; the
unapproved `agent/assy-uiux-improvements` (13/8) version is NOT served.

## UI scenario matrix

| UI Scenario | Runtime truth | Snapshot truth | Observed UI | Result | Notes / Evidence |
|---|---|---|---|---|---|
| UI-S1 Baseline (DETERMINISTIC, AP05=90, dwell 120) | AP05 effective=90, no overrun | actual=120, overrun=0, bottleneck="" | line advances 120s/step, no bottleneck cue, states plausible | PASS | `ui_s1_baseline.png`, `ui_s1_baseline_populated.png` |
| UI-S2 Forced bottleneck (AP05=135) | first dwell=135 | actual=135, overrun=15, bottleneck=AP05, dur=135 | t=1005 @ dwell 8 (vs 960 baseline); genealogy join gaps become 135s (480→600→735→870) | PASS | bottleneck shown indirectly via genealogy cadence; `ui_s2_ap05_135.png` |
| UI-S3 Improved (AP05=65) | AP05 no longer drives dwell | actual=120, overrun=0, bottleneck="" | t=960 @ dwell 8; joins back to 120s cadence | PASS | `ui_s3_ap05_065.png` |
| UI-S4 Presentation speed 1x→5x | work_duration/actual_dwell/bottleneck unchanged | identical before/after (t=1080, dwell 9, actual=120, overrun=0) | speed widget shows 5x; visual pacing only | PASS | `ui_s4_speed5x.png` |
| UI-S5 VARIABLE + reset | sampled effective frozen per op | snapshot polling stable (single sample, same execution_id) | VARIABLE run renders normally; sampled timing not rendered in UI | PASS (API-verified) | `ui_s5_variable.png`; timing fields are API-only |
| UI-S6 MANUAL sanity | legacy fixed duration, timing=null | PRE-ASSY AWAITING_COMPLETION, work_dur=30.0, timing=null | SSO2-0001 sits at PRE-ASSY waiting; line does not index | PASS | `ui_s6_manual.png` |
| UI-S7 AP06/AP08 retry | same op, same sample, no re-sample | V7/V8 backend: same execution_id + same timing | exception scenario targets ASSY-SL03 (SINGLE_TARGET_EXCEPTION); selected SL01 stays HAPPY_PATH → AP06 FAIL not shown on main detail | PASS (API/backend) | documented scenario-targeting limitation |
| UI-S8 AP11 QC/RELEASE | timed final-QC WORKING → CONFIRMED → AWAITING_COMPLETION → RELEASE | AUTO happy path released 1 motor (t=1560, dwell 12) | release reached; no second timing stage for RELEASE | PASS | backend V9 + API |

## What is NOT visible in the UI

Per the UI validation rule, no UI was modified to make validation pass. The
current UI **does not render** the AUTO-TIME-01C snapshot fields:

- `actual_dwell_s`, `dwell_overrun_s`, `bottleneck_station_id`,
  `bottleneck_duration_s`
- per-operation `timing` provenance (profile/effective duration)

These are exposed only through the authoritative API/snapshot (`/assy-demo/snapshot`)
and the `active_operations[].timing` projection. The bottleneck effect is
observable in the UI indirectly via the AP04 genealogy join cadence and the
simulation clock `t` (135s gaps / extra 15s per bottleneck dwell).

## Notes / pre-existing observations

1. **Scenario targeting:** `/assy-demo/reset {scenario}` returns `HAPPY_PATH`
   for the selected context (SL01); the exception scenario is applied to the
   target sub-line (SL03) only — this is the SINGLE_TARGET_EXCEPTION design and
   matches the pre-existing `TestVScenarioSwitch` behavior. Not a 01D regression.
2. **Speed control** is presentation-only (`setSpeed` sets `presentation_speed`);
   no runtime values change (UI-S4).
3. A benign 404 console error occurs on page load (missing auxiliary resource);
   no semantic impact.

## Conclusion

No runtime-vs-UI discrepancy was found. The canonical 14/8 UI presents the same
timing truth as the runtime/snapshot (dwell cadence, genealogy timing, MANUAL
gating, speed neutrality). Timing/bottleneck provenance fields are intentionally
API/snapshot-only in this slice and are reported as not visible in the UI.
