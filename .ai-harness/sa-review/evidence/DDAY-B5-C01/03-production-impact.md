# DDAY-B5-C01 — UNDERSUPPLY production / FG impact

- Bottles at UNDERSUPPLY entry: `1`
- Bottles at RECOVERY entry: `1`
- Bottles after isolated run: `2`
- FG receipts: `0`
- Good count: `0`
- FG follows good: **True**
- Compressor downtime events: `0`
- Low-pressure alarms: `1`

UNDERSUPPLY inhibits `_produce_one_cycle()` at the composition layer. No compressor downtime pair. Capper remains the hero downtime story.

Default demo compressor windows:

| t | phase | air_pressure | total | good | fg | capper |
|---|---|---|---|---|---|---|
| 1 | NORMAL | 6.98 | 0 | 0 | 0 | NORMAL |
| 240 | DEGRADING | 6.4 | 9 | 2 | 2 | RECOVERY |
| 264 | LOW_PRESSURE_WARNING | 6.1 | 10 | 3 | 3 | RECOVERY |
| 284 | UNDERSUPPLY | 5.8 | 11 | 4 | 4 | RECOVERY |
| 304 | RECOVERY | 5.6 | 11 | 4 | 4 | RECOVERY |
