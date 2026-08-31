# VF-CONTRACT-FINALITY-01 — six-line-isolation.md

Verified: the terminal marker appears ONLY on the FAILED_FINAL target sub-line
(ASSY-SL03); the other five sub-lines emit quality results but none terminal.

`test_terminal_only_on_target_sub_line` drives all six contexts of the
FAILED_FINAL composition and asserts:

- exactly one terminal `mes.quality_result` fact in the entire trace;
- its `run_id` starts with `ASSY-SL03:` (the scenario target);
- for `ASSY-SL01`, `ASSY-SL02`, `ASSY-SL04`, `ASSY-SL05`, `ASSY-SL06`:
  zero terminal facts.

No terminal marker leaks across sub-lines or WIPs.
