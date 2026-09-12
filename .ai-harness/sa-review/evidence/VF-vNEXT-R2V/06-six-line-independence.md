Validation head: (final commit on this branch)
Base (technical branch point): `4fc81e72780fe14ba5532407fdc8113b44385617`
Branch: `feature/vf-vnext-r2v`
Verdict: PASS

# 06 — Six-line independence: hold one, five continue, release resumes (V06)

Method: advance all six lines, hold `ASSY-SL03`, keep advancing the canonical window,
read Frame A + Frame B, then release.

Observed (source `06-six-line-independence.json`):
- Before hold (all six): `{"ASSY-SL01": 120.0, "ASSY-SL02": 120.0, "ASSY-SL03": 120.0, "ASSY-SL04": 120.0, "ASSY-SL05": 120.0, "ASSY-SL06": 120.0}`.
- Held sub-line ids while held: `['ASSY-SL03']`; after release: `[]`.
- **Frame A while held**: SL03 frozen (time 120.0 s, WIP 2, motors 0,
  state `stopped`) — `sl03_frozen_in_frame_a=True`; the
  other five keep producing — `five_continue_in_frame_a=True`:
  ASSY-SL01: t=720.0 s, motors=2 ; ASSY-SL02: t=720.0 s, motors=2 ; ASSY-SL04: t=720.0 s, motors=2 ; ASSY-SL05: t=720.0 s, motors=2 ; ASSY-SL06: t=720.0 s, motors=2.
- Projection frames while held (last): `{"ASSY-SL01": [720.0, 2], "ASSY-SL02": [720.0, 2], "ASSY-SL03": [120.0, 0], "ASSY-SL04": [720.0, 2], "ASSY-SL05": [720.0, 2], "ASSY-SL06": [720.0, 2]}`.
- **Frame B**: SL03 detail frozen — `{"frozen_at_120": true, "occupied": {"AP01": "SSO2-0001", "PRE-ASSY": "SSO2-0002"}, "simulation_time_s": 120.0}`;
  another line advanced — `{"advanced": true, "motors_created": 2, "occupied": {"AP01": "SSO2-0006", "AP02": "SSO2-0005", "AP03": "SSO2-0004", "AP04": "SSO2-0003", "AP05": "MTR-0002", "AP06": "MTR-0001", "PRE-ASSY": "SSO2-0007"}, "simulation_time_s": 720.0, "sub_line": "ASSY-SL01"}`.
- Release: `{"resumed": true, "sl03_time_after_release": 840.0}`.

**V06 = PASS.**
