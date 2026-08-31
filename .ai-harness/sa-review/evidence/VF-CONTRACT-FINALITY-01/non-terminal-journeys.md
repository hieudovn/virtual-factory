# VF-CONTRACT-FINALITY-01 — non-terminal-journeys.md

Machine-generated verification that the enrichment does NOT mark terminal
state for non-terminal journeys. Raw JSON: `non-terminal-journeys.json`.

| Journey | terminal facts | release present | detail |
|---|---|---|---|
| AP06 FAIL1 → PASS2 (ASSY-SL03) | 0 | yes | `MTR-0002`: attempt 1 FAIL `is_terminal=false`, attempt 2 PASS `is_terminal=false` |
| AP08 NG1 → PASS2 (ASSY-SL02) | 0 | yes | attempt 1 NG `is_terminal=false`, attempt 2 PASS `is_terminal=false` |
| HAPPY_PATH | 0 | yes | no `is_terminal=true` across quality messages |

No terminal marker leaks across sub-lines or WIPs (see `six-line-isolation.md`).
