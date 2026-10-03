# DDAY-B2 — 07. Deterministic replay proof

**Claim:** same configuration + same seed + same initial state ⇒ identical
execution, bit for bit, on the reused runtime.

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) → `determinism`

## Method

The full production trace (event type, station, unit, detail, simulation time,
dwell number — control-plane events excluded as they record operator actions) is
serialised and SHA-256 hashed. Two independent runtime instances were driven
through 12 cycles and compared, then one instance was reset and replayed.

## Results

| Check | Result |
|---|---|
| Seed / timing behaviour | `random_seed: 42`, `timing_behavior: DETERMINISTIC` |
| Instance A digest (12 cycles) | `6d968db7c70d20daf15e6b9be8fbe986c85c75f4d70bee1b89493623d696fd34` |
| Instance B digest (12 cycles) | `6d968db7c70d20daf15e6b9be8fbe986c85c75f4d70bee1b89493623d696fd34` |
| Identical across independent instances | **PASS** |
| Digest after RESET + replay of the same instance | `6d968db7c70d20daf15e6b9be8fbe986c85c75f4d70bee1b89493623d696fd34` |
| Identical after RESET replay | **PASS** |
| Raw facts identical across instances | **PASS** |
| Reject path digest (×2) | `8688874ed734eff667f9332ae377000dbd5438cc7044b9a677987b52e5936dc7` (identical) |

## Why it is deterministic by construction

- No wall-clock is read anywhere in the generic profile: the controller is
  step-driven and the runtime advances simulation time by dwell/index duration.
- No global `random` is used. `TimingResolver` is seeded per instance, and the
  Bottled Water configuration defines no timing profiles, so every station uses
  its configured fixed duration.
- Station execution order is the configured position order, and tie-breaking for
  the dwell driver scans that same order.
- Unit identity is a monotonic sequence (`BTL-000001`, …), so identity is
  reproducible for a given initial state.

Asserted by `test_t03_deterministic_replay_same_config_seed_initial_state` and
`test_t11_reset_restores_initial_state_and_deterministic_rerun`, and by section
`[7]` of the live smoke.
