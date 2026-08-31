# VF-DEPLOY-01 — six-sub-lines.md

## Sub-line list from the Docker runtime (§7)

`GET /assy-demo/sub-lines` returns exactly **6** sub-lines (no missing, no
alias):

| sub_line_id | variant | label |
|---|---|---|
| `ASSY-SL01` | hydraulic | ASSY-SL01 — Hydraulic |
| `ASSY-SL02` | hydraulic | ASSY-SL02 — Hydraulic |
| `ASSY-SL03` | hydraulic | ASSY-SL03 — Hydraulic |
| `ASSY-SL04` | thermal | ASSY-SL04 — Thermal |
| `ASSY-SL05` | thermal | ASSY-SL05 — Thermal |
| `ASSY-SL06` | thermal | ASSY-SL06 — Thermal |

Each entry also carries (verified for all 6):

```json
{
  "plant_id": "TIPA",
  "production_line_id": "ASSY",
  "sub_line_id": "ASSY-SL0x",
  "variant": "hydraulic" | "thermal",
  "effective_scenario": "HAPPY_PATH",
  "line_state": "stopped",
  "simulation_time_s": 120.0,
  "wips_on_line": 2,
  "motors_created": 0,
  "motors_released": 0
}
```

All six are distinct sub-lines on the same `TIPA`/`ASSY` production line; none
is aliased or dropped due to container config/path issues.

`GET /assy-demo/sub-line/ASSY-SL01` returns the detail snapshot (HTTP 200);
an unknown id returns 404 (e.g. `ASSY-SL99`).
