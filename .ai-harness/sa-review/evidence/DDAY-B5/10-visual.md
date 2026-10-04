# DDAY-B5 — B3 visual evidence

Headless Chrome captures of `/bottled-water-demo` against the live factory
runtime. Frames were PAUSED only to freeze the story for capture; operator
STOP was not used, so STOPPED ≠ FAULT remains visible.

| File | Phase | Visible facts |
|---|---|---|
| `10-visual-warning.png` | Capper WARNING | Capper mark `warn`; compressor still `normal`; event strip `Alarm raised` on Capper |
| `10-visual-fault.png` | Capper INTERMITTENT_STOP | Capper mark `fault`; CAP01 station tinted; `Downtime start`; compressor still `normal` |
| `10-visual-recovery.png` | Capper RECOVERY | Capper mark `recover`; compressor still `normal` |
| `10-visual-compressor-sag.png` | Compressor PRESSURE_SAG | Compressor mark `warn`; air pressure below the 6.4 bar production sag; Capper already `recover`; CMP01 `Alarm raised` at t=240 |
| `10-visual-compressor-recover.png` | Compressor RECOVERY | Compressor mark `recover`; CMP01 `Alarm cleared`; Capper remains `recover` |

Default demo story is sequential: Capper hero first, compressor sag only after
Capper recovery.
