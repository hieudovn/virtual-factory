# DDAY-VF-UAT-01 — proposed restart-safe warmup / window rule (NOT implemented)

Preserve `timestamp = 2026-10-03T00:00:00Z + simulation_time_s`. Do not change epoch. Do not publish from t=0 into TDengine.

## Floor

```text
floor_s = max(
  independently_measured_tdengine_max_simulation_time_s,  # required at deploy
  persisted_last_published_simulation_time_s,             # restart-safe local state
  sa_stated_lower_bound_s                                 # 610 until measured
) + margin_s
```

`margin_s` ≥ 1.0 (one FAST period). Next published source timestamp must be **strictly later** than every existing D-Day VF source timestamp.

## Startup / restart

1. Read-only query TDengine max source timestamp for `BW-DEMO-01` / bottled-water-dday. Do not write.
2. Compute `floor_s`.
3. `RESET` the factory (clears scheduler + export cursor).
4. `START`.
5. **Warmup:** `step()` only, **no** `publish_live_mqtt`, until `simulation_time_s > floor_s`.
6. Then enter the publish loop. First FR1 observation at that clock is allowed to publish (scheduler first-seen rule).
7. Persist last successfully ACKed `simulation_time_s`. Failed ACK does not advance the persisted floor.

After every container restart: repeat RESET + warmup + START publishing. Do not auto-publish from t=0.

## Limitation (must remain visible to SA)

Stepping through `floor_s ≥ 610` unpublished consumes the Capper (t≤210) and Compressor (t≤328) hero windows before live ingest. That is the cost of keeping the frozen timestamp contract against existing historian data. Changing epoch or adding a timestamp offset is a product-semantics change and is **not** proposed as silently in-scope.
