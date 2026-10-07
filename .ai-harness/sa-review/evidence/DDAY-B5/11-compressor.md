# DDAY-B5 — compressor secondary scenario

| t | compressor phase | highlight | air_pressure | total | good | fg | capper |
|---|---|---|---|---|---|---|---|
| 1 | NORMAL | normal | 6.98 | 0 | 0 | 0 | NORMAL |
| 240 | DEGRADING | warn | 6.4 | 9 | 2 | 2 | RECOVERY |
| 264 | LOW_PRESSURE_WARNING | warn | 6.1 | 10 | 3 | 3 | RECOVERY |
| 284 | UNDERSUPPLY | fault | 5.8 | 11 | 4 | 4 | RECOVERY |
| 304 | RECOVERY | recover | 5.6 | 11 | 4 | 4 | RECOVERY |

Default demo is non-overlapping: compressor DEGRADING begins only after Capper RECOVERY. UNDERSUPPLY inhibits production (totals freeze from t=284 to t=304); FG receipts follow actual good output.
