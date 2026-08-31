# TIPA ASSY Demo Environment Contract

Repository:
hieudovn/virtual-factory

Branch:
docs/m6-s01-tipa-baseline

Required feature flag:
VF_ENABLE_S04B_OVERVIEW=1

Expected application port:
8000

Canonical TIPA ASSY route:
/assy-demo

Generic VF route:
/

Canonical ASSY assets:
src/virtual_factory/ui/static/assy_demo.html
src/virtual_factory/ui/static/assy_demo.js
src/virtual_factory/ui/static/assy_demo.css

Expected ASSY behavior:
S04B Frame A/B capability enabled.
Sub-line overview/detail endpoints available.
Approved TIPA ASSY visual composition reproducible.

Failure mode:
If the env flag is missing in a new shell/session/process, the application may
fall back to the alternate S04 ASSY view and visually differ even when source
code/assets are unchanged.

Recovery:
1. set VF_ENABLE_S04B_OVERVIEW=1
2. restart the app/server
3. verify port 8000
4. open /assy-demo
5. verify approved ASSY composition

---

## Flag gate (repository evidence)

The S04B Frame A/B overview / sub-line endpoints are conditionally registered in
`src/virtual_factory/ui/api.py`:

```python
_enable_s04b = os.environ.get("VF_ENABLE_S04B_OVERVIEW", "0") == "1"
```

Without the flag, `GET /assy-demo/overview`, `GET /assy-demo/sub-lines` and
`GET /assy-demo/sub-line/{id}` return 404 and the ASSY frontend renders the
alternate/fallback S04 single-line view.

Observed endpoint behavior (session evidence, port 8000):

| Endpoint | Flag absent | Flag set |
|---|---|---|
| `/health` | 200 | 200 |
| `/assy-demo/overview` | 404 | 200 |
| `/assy-demo/sub-lines` | 404 | 200 |
| `/assy-demo/sub-line/ASSY-SL01` | 404 | 200 |

## Launch command (session-derived evidence, 2026-08-17)

The launch command that reproduces the approved TIPA ASSY demo environment on
this machine (Python 3.11.9):

```powershell
cd d:\Project\Github\virtual-factory
$env:VF_ENABLE_S04B_OVERVIEW = '1'
C:\Users\dotru\AppData\Local\Programs\Python\Python311\python.exe src\virtual_factory\main.py serve --port 8000
```

Then open `http://127.0.0.1:8000/assy-demo`.

## Harness lesson (governance pattern for future UI/demo gates)

> Commit SHA alone is insufficient to reproduce a demo. UI/demo validation must
> also pin execution environment: required env vars, feature flags, launch
> command, port, canonical route, and selected application context.

This contract is the reference artifact for that pattern in the AUTO-TIME-01D
correction series.
