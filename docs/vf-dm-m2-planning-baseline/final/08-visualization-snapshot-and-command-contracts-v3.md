# 08-v3 — Snapshot and Command Contracts (Final)

**Date:** 2026-08-05  
**Replaces:** `08-...-v2.md`  
**Corrections:** V2-F04, V2-F08, V2-F10

---

## 1. RuntimeSnapshot (M2-S01 — transport-free)

```python
@dataclass(frozen=True)
class RuntimeSnapshot:
    schema_version: str = "1.0.0"
    run_id: str
    model_id: str
    model_version: str | None
    scenario_id: str | None
    scenario_version: str | None
    status: str
    simulation_time_s: float
    stop_reason: str | None
    failure_error: str | None
    processed_events: int
    pending_events: int
    last_event_id: str | None
    snapshot_sequence: int          # per committed transition
```

`message_sequence` is NOT here — it belongs in the M4 transport envelope.

---

## 2. SnapshotMessage (M4 transport envelope) (C02-05)

```python
@dataclass(frozen=True)
class SnapshotMessage:
    schema_version: str = "1.0.0"
    message_sequence: int           # per WS message sent
    run_id: str
    snapshot: RuntimeSnapshot       # or DMVisualizationSnapshot in M4
```

---

## 3. Snapshot Versioning

- `snapshot_sequence`: increments once per committed event/command transition (or failure). Engine-owned.
- `message_sequence`: increments once per WebSocket message sent. Transport-owned.

---

## 4. Adaptive Publication

| Condition | Behavior |
|-----------|----------|
| State changed | Publish snapshot |
| Idle (auto mode, no events) | Heartbeat every 5s |
| Max broadcast rate | 10 Hz cap |
| Client reconnects | Full snapshot via resync |

---

## 5. Snapshot Size Policy (C02-10)

| Level | Value | Action |
|-------|-------|--------|
| Target | < 100 KB | Normal operation |
| Hard limit | 200 KB | Do NOT truncate JSON |

On exceeding hard limit:
- Do NOT transmit truncated/invalid JSON.
- Send a valid error envelope: `{"type": "snapshot_too_large", "size": N}`.
- Preserve the last valid snapshot.
- Fail the performance gate or switch to reduced/delta projection.

---

## 6. Command Envelope

```python
@dataclass(frozen=True)
class DMCommand:
    command_id: str                  # UUID from client
    command_sequence: int | None     # SERVER-assigned on acceptance
    run_id: str
    command_type: str
    target_id: str | None
    parameters: dict[str, Any]
    correlation_id: str | None
    source: str                      # "rest"
    actor: str
    issued_wall_clock: str           # ISO-8601 UTC (server receipt time)
    expected_snapshot_version: int | None  # M6 optimistic concurrency
```

### CommandResult

```python
@dataclass(frozen=True)
class CommandResult:
    command_id: str
    command_sequence: int
    status: str                      # accepted | rejected | applied | failed
    accepted_simulation_time_s: float | None
    result_event_id: str | None
    snapshot_sequence: int | None
    rejection_code: str | None
    rejection_detail: str | None
    server_wall_clock: str           # ISO-8601 UTC
```

---

## 7. CommandAuditEntry (C02-09)

```python
@dataclass(frozen=True)
class CommandAuditEntry:
    command_id: str
    command_sequence: int
    run_id: str
    actor: str
    source: str
    received_wall_clock: str         # ISO-8601 UTC
    accepted_simulation_time_s: float
    command_type: str
    target_id: str | None
    result_status: str
    rejection_code: str | None
    result_event_id: str | None
    snapshot_sequence: int
```

**Hybrid replay consumes this ordered command/audit log.** Without it, hybrid runs are not reproducible.

---

## 8. Transport (unchanged)

```
REST POST /api/discrete/runs/{run_id}/commands  → canonical write path
WebSocket /ws/discrete/{run_id}                  → snapshots, status, resync (read-only from client)
```
