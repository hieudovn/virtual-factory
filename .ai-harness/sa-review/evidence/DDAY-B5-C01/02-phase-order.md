# DDAY-B5-C01 — compressor phase order

Observed: `NORMAL → DEGRADING → LOW_PRESSURE_WARNING → UNDERSUPPLY → RECOVERY`

Required: `NORMAL → DEGRADING → LOW_PRESSURE_WARNING → UNDERSUPPLY → RECOVERY`

Match: **True**

| t | phase | highlight | air_pressure | power | total | fg |
|---|---|---|---|---|---|---|
| 1 | NORMAL | normal | 6.98 | 2.0 | 0 | 0 |
| 22 | DEGRADING | warn | 6.56 | 15.337 | 1 | 0 |
| 30 | LOW_PRESSURE_WARNING | warn | 6.24 | 16.125 | 1 | 0 |
| 38 | UNDERSUPPLY | fault | 5.92 | 17.25 | 1 | 0 |
| 60 | RECOVERY | recover | 5.6 | 17.25 | 1 | 0 |
