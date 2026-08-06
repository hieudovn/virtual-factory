# 09 — API, WebSocket, Security, and Audit Plan

**Date:** 2026-08-05

---

## 1. REST Endpoints

All DM endpoints under `/api/discrete/`. Existing endpoints unchanged.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/discrete/runs` | Create a new run |
| `GET` | `/api/discrete/runs` | List active runs |
| `GET` | `/api/discrete/runs/{run_id}` | Get run status |
| `POST` | `/api/discrete/runs/{run_id}/commands` | Send a command |
| `GET` | `/api/discrete/runs/{run_id}/snapshots/latest` | Get latest snapshot |
| `GET` | `/api/discrete/runs/{run_id}/snapshots?version=N` | Get specific snapshot |
| `GET` | `/api/discrete/runs/{run_id}/events` | Get event history |
| `DELETE` | `/api/discrete/runs/{run_id}` | Delete a completed run |
| `WS` | `/ws/discrete/{run_id}` | WebSocket for live snapshots + commands |

---

## 2. Run Creation

```
POST /api/discrete/runs
{
  "model_id": "tipa_final_assembly_v1",
  "model_version": "1.0.0",
  "scenario_id": "baseline_001",
  "environment": "demo",
  "random_seed": 42
}

→ 201
{
  "run_id": "run-abc123",
  "status": "created"
}
```

---

## 3. Command Endpoint

```
POST /api/discrete/runs/{run_id}/commands
{
  "command_type": "step",
  "target_id": null,
  "parameters": {}
}

→ 200
{
  "command_id": "cmd-xyz",
  "status": "accepted",
  "result_event_id": "evt-001",
  "snapshot_version": 5
}
```

---

## 4. Security — Incremental Policy

### Demo/Local Mode (M2–M5)

- No authentication required.
- Explicit `--unsafe-demo` flag on server startup.
- Localhost or controlled network only.
- Command audit still recorded (actor = "demo-user").

### Protected Mode (M6+)

| Role | Permissions |
|------|-------------|
| `viewer` | GET snapshots, events, run status |
| `operator` | viewer + `step`, `pause`, `hold`, `release`, inject commands |
| `controller` | operator + `auto_run`, `stop`, `reset`, fault injection |
| `admin` | controller + delete runs, manage scenarios |

**Implementation:** Simple API key or token header. Defer OAuth/OIDC to M7.

---

## 5. Command Validation

| Check | Rejection Reason |
|-------|-----------------|
| Run exists | `run_not_found` |
| Command valid for current state | `invalid_state_transition` |
| Target exists (if specified) | `target_not_found` |
| Parameters valid | `invalid_parameters` |
| Rate limit exceeded | `rate_limited` |

---

## 6. Audit Trail

Every command and its result is recorded:

```python
@dataclass
class AuditEntry:
    timestamp_s: float              # wall-clock
    simulation_time_s: float        # simulation time
    actor: str                      # "demo-user" or authenticated identity
    command: DMCommand
    result: CommandResult
    snapshot_version: int
```

Audit log is in-memory for MVP. M6 adds file/DB persistence.

---

## 7. Limits (MVP)

| Resource | Limit |
|----------|-------|
| Max concurrent runs | 5 |
| Max snapshot size | 100 KB |
| Max events per run | 1,000,000 |
| Max command rate | 10/sec per run |
| WebSocket message rate | 10/sec |
