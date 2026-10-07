# DDAY-VF-UAT-03 — cross-track closeout (canonical current)

This file is the current VF UAT closeout. The Run A host inspect in [09-uat-host.md](09-uat-host.md) is historical.

## SHA distinction

| Kind | SHA |
|---|---|
| Deployed VF executable | `d7db6d0909da968c2b4a4ea2cdb712e5d7601282` |
| PlantOS accepted UAT merge | `a1695c5457515e2b565a5f9fe107c1e18b3e0879` |
| UAT-02 historical PR head | `a8d5ecba1b0794251fd9c618c338de449263a0b0` |

## Coordinated UAT (PlantOS SA ACCEPTED)

1. Run A reached Center / TDengine / Live UI.
2. `reset_dday_receive_epoch` succeeded on the same Edge process.
3. VF restarted as deterministic Run B (same CLI / workspace / profile / contract).
4. Run B reused VF source timestamps (`2026-10-03T00:00:00Z + simulation_time_s`).
5. PlantOS accepted those rows at a later Edge receipt timestamp.
6. TDengine/latest and Live UI advanced.

**`Run B HOLD` is obsolete.** Current state: Run B completed.

No VF product change. No redeploy from this slice. PR #101 is not merged here.
