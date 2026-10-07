# DDAY-VF-UAT-03 scope — cross-track UAT closeout

## Authorized

1. Reconcile VF evidence with PlantOS SA-accepted coordinated UAT.
2. Keep UAT-02 Run A inspect as historical.
3. Record Run B completed. Remove `run_b_started is False` as a live invariant.

## Not authorized

- VF product / timestamp / contract / scenario change
- UAT redeploy or VF restart
- PlantOS code change
- Merge of PR #101
