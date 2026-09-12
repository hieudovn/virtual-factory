Validation head: (final commit on this branch)
Base (technical branch point): `4fc81e72780fe14ba5532407fdc8113b44385617`
Branch: `feature/vf-vnext-r2v`
Verdict: PASS

# 02 — Frame A: six live sub-lines (V02)

Method: canonical overview projection after 5 canonical steps
(`canonical_step=5`).

`exactly_six_canonical=True`,
`all_six_live=True`, `one_parent_run=True`
(parent run `TIPA-0001`), pinned scenario `tipa-default`,
sub-lines ['ASSY-SL01', 'ASSY-SL02', 'ASSY-SL03', 'ASSY-SL04', 'ASSY-SL05', 'ASSY-SL06'].

| sub-line | variant | time (s) | WIP on line | motors created | line state | effective scenario | run state |
|---|---|---|---|---|---|---|---|
| ASSY-SL01 | hydraulic | 600.0 | 6 | 1 | stopped | HAPPY_PATH | running |
| ASSY-SL02 | hydraulic | 600.0 | 6 | 1 | stopped | HAPPY_PATH | running |
| ASSY-SL03 | hydraulic | 600.0 | 6 | 1 | stopped | HAPPY_PATH | running |
| ASSY-SL04 | thermal | 600.0 | 6 | 1 | stopped | HAPPY_PATH | running |
| ASSY-SL05 | thermal | 600.0 | 6 | 1 | stopped | HAPPY_PATH | running |
| ASSY-SL06 | thermal | 600.0 | 6 | 1 | stopped | HAPPY_PATH | running |

**V02 = PASS** (exactly six canonical ASSY sub-lines, all live, independent state,
one parent run).
