# DEMO-CANDIDATE-01 — Demo Environment (recorded)

| Field | Value |
|---|---|
| Repository | `hieudovn/virtual-factory` |
| Branch | `docs/m6-s01-tipa-baseline` |
| Build SHA (gate baseline) | `494c12e265d297a389e4463848b9c0b6aafed0b1` |
| Accepted M6-INT-01-C01 impl | `6ccd6a53970f860c1f2bdc44ed2c8c7b66ed0de6` (ancestor) |
| Required env flag | `VF_ENABLE_S04B_OVERVIEW=1` |
| Port | `8000` |
| Canonical route | `http://127.0.0.1:8000/assy-demo` |
| Generic VF route | `/` (SCADA dashboard — NOT used for ASSY validation) |

## Launch command (Windows / PowerShell)

```powershell
cd d:\Project\Github\virtual-factory
$env:VF_ENABLE_S04B_OVERVIEW = '1'
C:\Users\dotru\AppData\Local\Programs\Python\Python311\python.exe src\virtual_factory\main.py serve --port 8000
```

## Endpoint check (after process restart on current build)

| Endpoint | Status |
|---|---|
| `/health` | 200 |
| `/assy-demo` | 200 |
| `/assy-demo/overview` | 200 |
| `/assy-demo/sub-lines` | 200 |
| `/assy-demo/sub-line/ASSY-SL01` | 200 |
| `/assy-demo/observations` | 200 |

Reference contract:
`.ai-harness/sa-review/evidence/AUTO-TIME-01D/demo-environment-contract.md`

Note: a browser page load of `/assy-demo` calls `/assy-demo/reset` (Frame A
`ctrl.init()`), i.e. each fresh page load starts a clean demo session. This is
consistent with the environment contract (clean initial state on restart).
