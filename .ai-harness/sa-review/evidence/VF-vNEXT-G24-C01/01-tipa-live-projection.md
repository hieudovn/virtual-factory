# VF-vNEXT-G24-C01 — Shell reflects selected G22 TIPA RuntimeSession — Evidence

Gate: `VF-vNEXT-G24-C01` · Correction gate on the G24 head
`899e851167de768669769dfe650bb46e011024d7`.
Model: Pro.

## 1. What was corrected

- `src/virtual_factory/runcontrol/assy_bridge.py` — added READ-ONLY
  `AssyExecutionBridge.sub_line_views()`: one detached dict per TIPA ASSY
  sub-line (sub_line_id, scope, variant, simulation_time_s, conveyor_state,
  wip_count, motor_count, rso2_buffer_size), read only from the public runtime
  read surface. Never mutates the federation/runtime/sub-line.
- `src/virtual_factory/ui/workspace_monitor.py` — the TIPA monitor view now:
  - projects live per-sub-line values from the SELECTED G22 `RuntimeSession`'s
    own execution bridge (`session.record.bridge`, built lazily on first step);
    no second runtime is ever created by the shell;
  - carries `runtime_kind: "selected_g22_session"` and the session identity;
  - labels `/assy-demo` as a SEPARATE legacy demo runtime
    (`legacy_demo: {shares_session: false, shares_identity: false, ...}`) with
    an explicit note that identity/state are NOT shared.
- `src/virtual_factory/ui/static/workspace_shell.js` — renders a live per-sub-line
  table (sim time / conveyor / WIP / motors / RSO2 buffer) and labels the
  `/assy-demo` link "separate legacy ASSY demo UI (NOT this session)".

## 2. Required semantics coverage

| Requirement | Proof |
|---|---|
| step changes per-sub-line values/status | before step `sub_lines == []`; after step 6 rows with `simulation_time_s > 0` |
| 6 sub-lines | `sub_lines` ids == `SUB_LINE_IDS` (ASSY-SL01..SL06); structure len 6 |
| shell runtime identity = selected G22 session | `runtime_kind == "selected_g22_session"`; `identity.run_id == session.run_id`; scenario `tipa-default` |
| no second runtime | shell reads only the session's own bridge; `sub_lines` empty until step; no federation built by the shell |
| /assy-demo not presented as same-session | `legacy_demo.shares_session is False`, `shares_identity is False`, note states "SEPARATE"/"not shared"; JS link label says "(NOT this session)" |
| ASSY oracle + regression | ASSY oracle (`tests/test_assy_demo.py`, `test_auto_equiv_01.py`) and full suite green |

## 3. Preserved / unchanged

No ASSY runtime/UI rewrite; no legacy-controller unification; no G22/G23
semantics change; runcontrol still SH-WTP-free; G21 slice untouched; no G25.

## 4. Test evidence

- `tests/test_vnext_g24_workspace_ui.py` — 37 tests PASS (30 G24 + 7 C01).
- Complete canonical vNext baseline (see report `VF-vNEXT-G24-C01.md`).
