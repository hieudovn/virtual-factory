# DDAY-VF-UAT-01 — source time / TDengine

## Blocker C

Accepted formula (unchanged):

```text
timestamp = 2026-10-03T00:00:00.000Z + simulation_time_s
```

`RESET` / new process restarts `simulation_time_s` at 0.

## Measured maximum in TDengine

**UNKNOWN** from this agent. Historian was not queried and not modified.

SA deployment review states existing UAT evidence already contains source times from t=0 through **at least t=610 s** (`2026-10-03T00:10:10.000Z`). That is a **lower bound**, not a measured max. A deploy slice must read the actual max before first publish.

## Hero-scenario collision if warmup steps past 610 s

| Scenario | Window (RUNNING simulated s) |
|---|---|
| Capper BW-CAP-DEG-01 RECOVERY completes | 210 |
| Compressor BW-CMP-SAG-01 stays NORMAL until | 240 |
| Compressor recovery completes | 328 |

Warming by actually stepping ≥610 s **without publishing** preserves the timestamp contract, but both hero stories will already have completed unpublished. Live D-Day then starts in a post-recovery plant state.

Do **not** silently add a timestamp offset or change `UTC_EPOCH`. If D-Day must show Capper/Compressor live after existing historian coverage, SA must authorize that separately.
