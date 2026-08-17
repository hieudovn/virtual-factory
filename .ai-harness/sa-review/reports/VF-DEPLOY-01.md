# VF-DEPLOY-01 — ASSY Docker Runtime

## 1. Baseline / Head

| Field | Value |
|---|---|
| Task ID | `VF-DEPLOY-01` (deployment implementation + runtime equivalence) |
| Repository | `hieudovn/virtual-factory` |
| Branch | `docs/m6-s01-tipa-baseline` |
| Accepted VF contract/documentation tip | `f72cc9564b251c3812c2b6070bddd37e479d5ea5` |
| Accepted VF production/demo build | `494c12e265d297a389e4463848b9c0b6aafed0b1` |
| Baseline (branch tip before deployment) | `18d253d632ee9c939a206e28c27fcebdea61af50` |
| Head (this deployment) | `f1493e6` |
| Production code changed | **NO** |
| Simulation semantics changed | **NO** |
| VF producer contract changed | **NO** |
| MES integration added | **NO** |
| Docker result | **PASS** |

## 2. Design decision (§3)

**Option A — separate `docker-compose.assy.yml`** (preferred by the gate).

- The generic root `Dockerfile` is reused **unchanged** (generic VF runtime
  image). No TIPA-specific image was created.
- ASSY-specific launch behavior lives entirely in `docker-compose.assy.yml`
  (compose service `vf-assy`).
- Existing compose services (`mqtt`, `virtual-factory-api`, `vf2-simulator`)
  are untouched; the existing `docker-compose.yml` still validates
  (`config --services` returns all three).
- ASSY starts independently (`name: vf-assy` project; only port 8000).
- Future MES E2E joins via a documented one-line external-network change.

Why not profile/extend existing compose: a separate file preserves the existing
continuous/MQTT/OPC-UA/VF2 stack with zero risk, keeps the ASSY service
dependency-light (no MQTT/OPC UA), and gives MES E2E a clean join point.

## 3. `vf-assy` service behavior (§4)

```text
virtual-factory serve --host 0.0.0.0 --port 8000
```

Environment: `VF_ENABLE_S04B_OVERVIEW=1`,
`TIPA_ASSY_CONFIG=/app/configs/plants/tipa_assy_demo.yaml` (container path, no
host path). Ports: `8000:8000` only (no MQTT/OPC UA exposed). No credentials.

## 4. Healthcheck (§5)

Real container healthcheck polling `GET /health` (stdlib `urllib`; no extra
dependency):

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request, json; s=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)); raise SystemExit(0 if s.get('status')=='ok' else 1)"]
  interval: 10s
  timeout: 3s
  retries: 5
  start_period: 10s
```

Container reaches `healthy` (verified: `Up 33 seconds (healthy)`).

## 5. Endpoint validation (§6) — all HTTP 200

`/health`, `/assy-demo`, `/assy-demo/overview`, `/assy-demo/sub-lines`,
`/assy-demo/sub-line/ASSY-SL01`, `/assy-demo/observations` — all **200**.
Static assets (`assy_demo.html`, `assy_demo.js`, `assy_demo.css`) all 200,
non-empty.

## 6. Six sub-lines (§7)

`/assy-demo/sub-lines` returns exactly 6: `ASSY-SL01..SL03` (hydraulic),
`ASSY-SL04..SL06` (thermal). No missing/aliased sub-line. Unknown id → 404.

## 7. Runtime control (§8)

Reset / Step / run-mode (AUTO/MANUAL/ASSISTED) / select / scenario selection
(`HAPPY_PATH`, `AP06_FAIL_RETEST_PASS`, `AP08_NG_REINSPECT_PASS`,
`FAILED_FINAL`) — all HTTP 200. Session/reload behavior unchanged (accepted).

## 8. Native ↔ Docker equivalence (§9) — **PASS**

Both runtimes started fresh (bridge at generation R1), driven identically, and
the P0 observation trace fingerprinted and diffed. **Result: EQUIVALENT (all
PASS)** for every field, including the full ordered `message_keys` lists
(HAPPY 1254, AP06 2335, AP08 3494 messages — byte-identical).

- **E1 HAPPY_PATH**: WIP route, AP04 genealogy, AP06/AP08 quality, AP11 final
  QC + release, deterministic release — identical.
- **E2 AP06 FAIL→PASS**: FAIL attempt 1 (`QR-0002`) and PASS attempt 2
  (`QR-0003`) distinct — identical.
- **E3 AP08 NG→PASS**: NG attempt 1 (`QR-0006`) and PASS attempt 2 (`QR-0007`)
  distinct — identical.
- **E4 observation contract**: message types, `message_key` behavior, `run_id`
  behavior, station identity, AP04 cardinality, quality attempt identity,
  AP11 final-QC vs release distinction — unchanged.

## 9. Restart / lifecycle (§10) — **PASS**

- `docker restart`: healthy again, observations reset 16749 → 0, endpoints 200.
- `docker compose down` + `up`: container + network recreated, healthy, 6
  sub-lines, endpoints 200.
- State is **intentionally ephemeral** (in-memory only, no volume). Restart
  returns to a clean valid HAPPY_PATH runtime. Clean deterministic restart
  preferred over hidden state carryover.

## 10. Network plan (§11)

`vf-assy` runs on `vf-assy_default` (port 8000 only). Future MES E2E joins
external `manufacturing-demo` network via a documented one-line change
(uncomment `networks.default.name=manufacturing-demo, external: true` after
`docker network create manufacturing-demo`). No MES connection/auth added.

## 11. Image/config neutrality (§12)

No hardcoded MES URL/credentials/Odoo IDs, no Windows host paths, no
developer usernames, no TIPA-specific behavior in generic core code. TIPA ASSY
config is selected by environment/compose only.

## 12. Debuggability (§13)

Documented in `docs/deployment/assy-docker.md`: build, start, stop, restart,
logs, health, debug shell (`docker exec`), env inspect, endpoint queries.
No secrets in docs/evidence.

## 13. Build reproducibility (§14)

Clean `--no-cache` build succeeded. Base `python:3.11-slim`, Python 3.11.16,
image `vf-assy:latest` (ID `e0ded2accbf5`), built from committed repo HEAD
`18d253d`. Build depends only on committed files.

## 14. Minimal production changes (§15)

Only added:
- `docker-compose.assy.yml` (new; preferred)
- `docs/deployment/assy-docker.md` (new; allowed)
- `.ai-harness/sa-review/**` (report + evidence)

The root `Dockerfile` was **not** modified. No assembly runtime / timing /
quality / genealogy / observation / `MESProjection` change. No STOP condition
was hit.

## 15. Regression (§16) — **green**

Full suite: **1554 passed, 2 failed** — the same two documented pre-existing
failures (`TestVScenarioSwitch`, `TestSelectEndpointNonMutation`), unchanged
from baseline. Targeted ASSY/observation/timing set: **496 passed, 1 failed**
(same pre-existing `TestVScenarioSwitch`). No new failures. Existing
continuous/VF2 compose still validates (3 services intact).

## 16. Acceptance criteria (§19)

| # | Criterion | Result |
|---|---|---|
| 1 | Image builds from committed repo | ✅ |
| 2 | `vf-assy` starts independently | ✅ |
| 3 | Container becomes healthy | ✅ |
| 4 | ASSY UI/API reachable | ✅ |
| 5 | Six sub-lines available | ✅ |
| 6 | Reset/Step/Auto behavior works | ✅ |
| 7 | HAPPY_PATH native ≡ Docker | ✅ |
| 8 | AP06 exception native ≡ Docker | ✅ |
| 9 | AP08 exception native ≡ Docker | ✅ |
| 10 | Observation contract unchanged | ✅ |
| 11 | Restart returns to clean valid runtime | ✅ |
| 12 | No host-specific path dependency | ✅ |
| 13 | No secret embedded | ✅ |
| 14 | Existing continuous/VF2 deployment not broken | ✅ |
| 15 | Relevant VF regression green | ✅ |
| 16 | Future MES shared-network path documented | ✅ |
| 17 | No MES integration added yet | ✅ |

## 17. STOP conditions (§20)

None triggered. Docker reproduces accepted ASSY behavior exactly; packaging
does not alter observation/message semantics; TIPA config loads without core
change; no destructive redesign; no host-only files; no MES-specific code; no
regression; no secrets hardcoded.

## 18. Evidence

`.ai-harness/sa-review/evidence/VF-DEPLOY-01/`:

`environment.md`, `docker-build.md`, `docker-run.md`, `health-endpoints.md`,
`six-sub-lines.md`, `runtime-control.md`, `native-vs-docker.md`,
`restart-lifecycle.md`, `observation-equivalence.md`, `network-plan.md`,
`regression-tests.md` + machine outputs (`docker-fingerprint.json`,
`native-fingerprint.json`, `*-observation-evidence.json`, `regression-*.txt`)
and reproducible scripts (`equivalence_check.py`, `diff_fingerprints.py`,
`observation_evidence.py`).

## 19. Recommendation

```text
VF-DEPLOY-01 — READY FOR SA REVIEW
Docker result: PASS
```

`MES-INT-E2E-01` remains HOLD pending SA review of this gate, per governance.
