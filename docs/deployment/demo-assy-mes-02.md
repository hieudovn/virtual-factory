# VF-DM-DEMO-ASSY-MES-02 — Six-Sub-line MES Contract Bridge

`tipa-assy-demo-v1` · authoritative six-sub-line TIPA ASSY Docker runtime
(`/assy-demo`) projected to MES-compatible messages via the existing M5
observation pipeline. No parallel simulation; the six-sub-line topology and
runtime are unchanged.

## What it does

The bridge (`src/virtual_factory/assembly/assy_mes_bridge.py`) reads the
authoritative runtime truth and emits, idempotently, per sub-line/run:

- `mes.run_status` — **operational** line state (`running|fault|stopped`),
  separate from the raw `conveyor_state` (`indexing|stopped|operating|ready_to_index`).
  Conveyor `stopped` is never projected as production STOPPED.
- `mes.issue` — deterministic `AP05_JAM`: `EXCEPTION_RAISED` /
  `EXCEPTION_RESOLVED` with shared correlation (run, subline, station, reason).
- `mes.execution_event` — `WIP_ENTERED`, `OPERATION_COMPLETED`, `LINE_OUT`
  (`GOOD|REJECT`), `DOWNTIME_START`, `DOWNTIME_END`.
- `mes.quality_result` — AP06/AP08/AP11 per attempt (+ `is_terminal`,
  `terminal_state`).
- `mes.genealogy_relationship` — AP04 join.
- `mes.release` — AP11 RELEASE (distinct from final QC and LINE_OUT).
- `mes.oee_summary` — per sub-line/run, reconciled
  (`planned = run + downtime`, `actual = good + reject`, A/P/Q/OEE recomputable).

Every message carries `message_key` (= `payload.idempotency_key`),
`contract_version`, `run_id=ASSY-SLxx:R<n>`, explicit `subline_id`,
`station_id` where applicable, `simulation_time_s`, and a deterministic
ISO-8601 `occurred_at`.

## Demo sequence (target sub-line ASSY-SL03, FAILED_FINAL)

```
reset → healthy production → jam → recover → run-to-terminal
        RUNNING              FAULT→STOPPED   RUNNING      OEE per sub-line
```

- `jam` raises a deterministic `AP05_JAM` on the exception target sub-line:
  operational `FAULT` → `STOPPED`, `EXCEPTION_RAISED`, `DOWNTIME_START`.
- `recover` resolves after the deterministic 120 s downtime:
  `EXCEPTION_RESOLVED`, operational `RUNNING`, `DOWNTIME_END` (120 s).
- A quality HOLD / retest / reinspection never becomes a line fault or downtime.

## Run locally

```bash
python -m virtual_factory.assembly.assy_mes_bridge        # smoke (JSON counts)
python -m pytest tests/test_assy_mes_bridge_v1.py -q
```

## Docker (reproducibility)

Rebuild on the exact source SHA:

```powershell
$env:SOURCE_SHA = (git rev-parse HEAD)
docker compose -f docker-compose.assy.yml up --build -d
```

The image bakes `SOURCE_SHA` (default `unknown`) as `VF_SOURCE_SHA`, exposed by:

- `GET /assy-demo/version` → `{ "source_sha": "...", ... }`

Prove the runtime endpoints:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/assy-demo/overview
curl http://127.0.0.1:8000/assy-demo/sub-lines
curl http://127.0.0.1:8000/assy-demo/sub-line/ASSY-SL03
curl http://127.0.0.1:8000/assy-demo/observations
curl http://127.0.0.1:8000/assy-demo/mes-messages
curl http://127.0.0.1:8000/assy-demo/version
```

Control endpoints (MES contract bridge):

- `POST /assy-demo/jam` (`{ "sub_line_id": "ASSY-SL03" }` optional)
- `POST /assy-demo/recover`
- `POST /assy-demo/run-to-terminal`
- `POST /assy-demo/reset` (bumps run generation; no idempotency-key reuse)

## Scope

No MQTT/broker, no MES→VF, no robot/line control, no full rework routing,
no measurement/checklist outbound contract, no UI redesign, no rewrite of the
six-sub-line runtime, no merge/consolidation into `main` in this gate.
