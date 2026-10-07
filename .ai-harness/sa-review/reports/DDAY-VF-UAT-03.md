# DDAY-VF-UAT-03 — cross-track UAT closeout

## Status

Machine status is derived by the full canonical task gate.

The PM does not self-certify `COMPLETE`, `CLOSED`, `SA APPROVED`, or `NEXT SLICE AUTHORIZED`.

**Run B is completed.** `Run B HOLD` is not current authoritative state.

## Task interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-VF-UAT-03` |
| Authority | SA Issue `#120` + PlantOS SA-accepted coordinated UAT |
| PR | `#101` |
| Scope | Evidence/governance only |

## SHA distinction

| Kind | SHA |
|---|---|
| Deployed VF runtime | `d7db6d0909da968c2b4a4ea2cdb712e5d7601282` |
| PlantOS accepted UAT merge | `a1695c5457515e2b565a5f9fe107c1e18b3e0879` |
| UAT-02 historical evidence head | `a8d5ecba1b0794251fd9c618c338de449263a0b0` |

## Cross-track facts recorded

- Run A reached Center / TDengine / Live UI
- `reset_dday_receive_epoch` succeeded on the same Edge process
- VF restarted as deterministic Run B
- Run B reused VF source timestamps
- PlantOS accepted them at a later Edge receipt timestamp
- TDengine/latest and Live UI advanced

UAT-02 `09-uat-host.md` / `machine-evidence.json` remain the Run A inspect snapshot (`evidence_role=historical_run_a`).

`tests/test_dday_vf_uat_02_host_hold.py` is removed. Historical snapshot tests live in `tests/test_dday_vf_uat_02_run_a_historical.py`.

NOT authorized: VF product change, redeploy, merge of PR #101.
