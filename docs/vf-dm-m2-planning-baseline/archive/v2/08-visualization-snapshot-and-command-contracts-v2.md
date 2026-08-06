# 08-v2 — Visualization Snapshot and Command Contracts (Corrected)

**Date:** 2026-08-05  
**Replaces:** `08-visualization-snapshot-and-command-contracts.md`  
**Corrections:** F-010 (incomplete contracts), F-011 (command channels), F-012 (snapshot policy)

---

## 1. RuntimeSnapshot (M2 — domain-neutral) (C-010)

```python
@dataclass(frozen=True)
class RuntimeSnapshot:
    """M2: immutable domain-neutral engine lifecycle projection."""
    schema_version: str = "1.0.0"

    # Identity
    run_id: str
    model_id: str
    model_version: str | None
    scenario_id: str | None
    scenario_version: str | None

    # Lifecycle
    status: str
    simulation_time_s: float
    stop_reason: str | None
    failure_error: str | None

    # Diagnostics
    processed_events: int
    pending_events: int
    last_event_id: str | None
    snapshot_sequence: int              # increments per committed transition
    message_sequence: int               # increments per WS message sent

    # Allowed actions (for UI controls)
    allowed_actions: list[str]
```

---

## 2. DMVisualizationSnapshot (M4 — full UI)

```python
@dataclass(frozen=True)
class DMVisualizationSnapshot:
    """M4: full projection including assembly domain state."""
    # ... all RuntimeSnapshot fields ...

    # Topology/routing/layout identity
    topology_id: str
    topology_version: str | None
    routing_id: str
    routing_version: str | None
    layout_id: str
    layout_version: str | None
    topology_checksum: str | None       # for integrity verification
    routing_checksum: str | None

    # Assembly domain projection
    nodes: list[NodeSnapshot]
    routes: list[RouteSnapshot]
    entities: list[EntitySnapshot]
    resources: list[ResourceSnapshot]   # operators, equipment

    # Per-object allowed actions
    # node_actions: dict[node_id, list[str]]

    # Counters / KPIs (provisional)
    counters: dict[str, int]

    # Recent events
    recent_events: list[EventSummary]
```

---

## 3. Snapshot Versioning (C-010)

- `snapshot_sequence`: increments once per committed event/command transition. Not per field mutation.
- `message_sequence`: increments once per WebSocket message sent. Used for gap detection.
- `topology_checksum` / `routing_checksum`: optional integrity hashes for client-side verification.

---

## 4. Adaptive Publication (C-010, C-012)

| Condition | Behavior |
|-----------|----------|
| State changed (event dispatched) | Publish snapshot |
| State changed (command applied) | Publish snapshot |
| Idle (no events, auto mode) | Heartbeat every 5s |
| Max broadcast rate | 10 Hz cap (configurable) |
| Client reconnects | Full snapshot on resync |
| UI animation | Independent of snapshot frequency (CSS transitions) |

**Not:** unconditional 10 Hz publication.

---

## 5. Command Envelope (C-011)

```python
@dataclass(frozen=True)
class DMCommand:
    command_id: str                    # UUID from client
    command_sequence: int | None       # Assigned by SERVER on acceptance
    run_id: str
    command_type: str
    target_id: str | None
    parameters: dict[str, Any]
    correlation_id: str | None
    source: str                        # "rest", channel identifier
    actor: str                         # "demo-user" or authenticated identity
    issued_wall_clock: str             # ISO-8601 UTC from server on receipt
    expected_snapshot_version: int | None  # Optimistic concurrency (M6)
```

### CommandResult

```python
@dataclass(frozen=True)
class CommandResult:
    command_id: str
    command_sequence: int              # Server-assigned
    status: str                        # accepted | rejected | applied | failed
    accepted_simulation_time_s: float | None
    result_event_id: str | None
    snapshot_sequence: int | None
    rejection_code: str | None         # e.g. "invalid_state", "target_not_found"
    rejection_detail: str | None
    server_wall_clock: str             # ISO-8601 UTC
```

---

## 6. Transport Separation (C-011)

```
REST POST /api/discrete/runs/{run_id}/commands  → canonical command write path
WebSocket /ws/discrete/{run_id}                  → snapshots, status, events, resync
```

No client-to-server commands over WebSocket for MVP. Future versions may add idempotent WS commands through the same command service.

---

## 7. WebSocket Protocol

### Server → Client

```json
{"type": "snapshot", "message_sequence": 42, "snapshot": {...}}
{"type": "heartbeat", "message_sequence": 43}
{"type": "status", "status": "completed", "stop_reason": "scheduler empty"}
```

### Client → Server

```json
{"type": "resync", "last_message_sequence": 41}
```

Server responds with full snapshot at current version.
