Validation head: (final commit on this branch)
Base (technical branch point): `4fc81e72780fe14ba5532407fdc8113b44385617`
Branch: `feature/vf-vnext-r2v`
Verdict: PASS

# 03 — Frame B: 2D parity, WIP motion, AP04 join (V03)

Method: successive canonical steps on `ASSY-SL01`; each frame compares the
canonical runtime truth with the Frame B 2D rendering derived from `positions[]`
(`truth_pairs_rendered_vs_runtime`, last pairs `[['AP09', None, None], ['AP10', None, None], ['AP11', None, None]]`).

Accepted positions per frame: **12**
(['PRE-ASSY', 'AP01', 'AP02', 'AP03', 'AP04', 'AP05', 'AP06', 'AP07', 'AP08', 'AP09', 'AP10', 'AP11']); `positions_match_accepted=True`.

| step | time (s) | motors created | canonical positions (occupied) |
|---|---|---|---|
| 1 | 120.0 | 0 | AP01=SSO2-0001, PRE-ASSY=SSO2-0002 |
| 2 | 240.0 | 0 | AP01=SSO2-0002, AP02=SSO2-0001, PRE-ASSY=SSO2-0003 |
| 3 | 360.0 | 0 | AP01=SSO2-0003, AP02=SSO2-0002, AP03=SSO2-0001, PRE-ASSY=SSO2-0004 |
| 4 | 480.0 | 0 | AP01=SSO2-0004, AP02=SSO2-0003, AP03=SSO2-0002, AP04=SSO2-0001, PRE-ASSY=SSO2-0005 |
| 5 | 600.0 | 1 | AP01=SSO2-0005, AP02=SSO2-0004, AP03=SSO2-0003, AP04=SSO2-0002, AP05=MTR-0001, PRE-ASSY=SSO2-0006 |
| 6 | 720.0 | 2 | AP01=SSO2-0006, AP02=SSO2-0005, AP03=SSO2-0004, AP04=SSO2-0003, AP05=MTR-0002, AP06=MTR-0001, PRE-ASSY=SSO2-0007 |
| 7 | 840.0 | 3 | AP01=SSO2-0007, AP02=SSO2-0006, AP03=SSO2-0005, AP04=SSO2-0004, AP05=MTR-0003, AP06=MTR-0002, AP07=MTR-0001, PRE-ASSY=SSO2-0008 |
| 8 | 960.0 | 4 | AP01=SSO2-0008, AP02=SSO2-0007, AP03=SSO2-0006, AP04=SSO2-0005, AP05=MTR-0004, AP06=MTR-0003, AP07=MTR-0002, AP08=MTR-0001, PRE-ASSY=SSO2-0009 |

- `first_position_of_sso2_0001=AP01` — SSO2-0001 enters at
  the first machine and advances one station per step
  (`wip_moves=True`).
- AP04 JOIN: `{"at_ap05": true, "genealogy": [["MTR-0001", ["SSO2-0001", "RSO2-0001"]]], "motor": "MTR-0001", "step": 5, "visible_in_frame": [["MTR-0001", ["SSO2-0001", "RSO2-0001"]]]}` — the joined motor
  `MTR-0001` is created at step 5 and then travels downstream
  (`motor_moves_downstream={"step5": "MTR-0001", "step6": "MTR-0001", "step7": "MTR-0001", "step8": "MTR-0001"}`).
- `rendered_matches_positions_truth=True` — the
  rendered Frame B state equals the canonical `positions[]` truth in every frame.

**V03 = PASS.**
