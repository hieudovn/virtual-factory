# DDAY-B5 / DDAY-B5-C01 — B3 visual evidence

Headless Chrome captures of `/bottled-water-demo` against the live factory
runtime. Frames were PAUSED only to freeze the story for capture; operator
STOP was not used, so STOPPED ≠ FAULT remains visible.

| File | Phase | Visible facts |
|---|---|---|
| `10-visual-warning.png` | Capper WARNING | Capper mark `warn`; compressor still `normal`; event strip `Alarm raised` on Capper |
| `10-visual-fault.png` | Capper INTERMITTENT_STOP | Capper mark `fault`; CAP01 station tinted; `Downtime start`; compressor still `normal` |
| `10-visual-recovery.png` | Capper RECOVERY | Capper mark `recover`; compressor still `normal` |
| `10-visual-compressor-warning.png` | Compressor LOW_PRESSURE_WARNING | Compressor mark `warn`; air pressure falling; Capper already `recover`; CMP01 `Alarm raised` |
| `10-visual-compressor-undersupply.png` | Compressor UNDERSUPPLY | Compressor mark `fault`; air pressure at/near floor; production inhibited |
| `10-visual-compressor-recover.png` | Compressor RECOVERY | Compressor mark `recover`; CMP01 `Alarm cleared`; production resumes |

Default demo story is sequential: Capper hero first, then compressor
`NORMAL → DEGRADING → LOW_PRESSURE_WARNING → UNDERSUPPLY → RECOVERY`
after Capper recovery.
