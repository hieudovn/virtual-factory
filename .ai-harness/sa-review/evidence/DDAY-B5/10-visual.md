# DDAY-B5 — B3 visual evidence

Headless Chrome captures of `/bottled-water-demo` against the live factory
runtime. Factory `run_state` stays RUNNING; Capper highlight and the event
strip carry the abnormal story.

| File | Phase | Visible facts |
|---|---|---|
| `10-visual-warning.png` | WARNING | Capper mark `warn`; event strip `Alarm raised` + scenario phase |
| `10-visual-fault.png` | INTERMITTENT_STOP | Capper mark `fault`; CAP01 station dot red; `Downtime start` |
| `10-visual-recovery.png` | RECOVERY | Capper mark `recover`; `Alarm cleared` + `Downtime end` |

Operator STOP was not used for these frames, so STOPPED ≠ FAULT remains
visible: the plant is RUNNING while the Capper is in a machine-fault highlight.
