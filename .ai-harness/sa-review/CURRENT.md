# SA REVIEW INBOX

Task: DDAY-VF-UI-DEPLOY — FactoriX Sim UI on UAT
Status: SA asked for evidence refresh only on PR #122 (comments 6050598056 / 6050598477). Product/UX at 2a50760 already PASS. Machine status is derived by `run_task_gate.py`.

Authority:
SA Issue #121
PR: https://github.com/hieudovn/virtual-factory/pull/122

SHA distinction:
- canonical main / Issue #121 baseline: ee838b0b00704e8f0ed7cd965ac48440cca2b26e
- product / UX SHA: 2a507606bd63fbc7a27ef543cbaaf54469cc631b
- deployed VF executable: 2a507606bd63fbc7a27ef543cbaaf54469cc631b
- previous deployed MQTT executable: d7db6d0909da968c2b4a4ea2cdb712e5d7601282
- PlantOS accepted UAT merge: a1695c5457515e2b565a5f9fe107c1e18b3e0879

Public: http://157.10.52.54/factorix-sim

Historical: Run B completed per PlantOS SA-accepted coordinated UAT. UAT-02 inspect remains historical_run_a only.

Conservative interpretation: FactoriX Sim HTTP observes the same `dday-bw-runtime` factory. Recreating `virtual-factory-dday` is required to load the listener. MQTT IDs unchanged. Overview source stays C01-frozen; FactoriX chrome is applied at serve time. Operator surface is START/PAUSE/STOP primary with Advanced Resume/Reset. This pass is evidence-only. No Issue #91.

The PM does not self-certify COMPLETE / CLOSED / SA APPROVED / NEXT SLICE AUTHORIZED.
