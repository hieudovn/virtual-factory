# 08 — Visualization Snapshot and Command Contracts

**Date:** 2026-08-05

---

## 1. VisualizationSnapshot

```python
@dataclass(frozen=True)
class VisualizationSnapshot:
    """Immutable projection of DM state for UI rendering."""

    # Run identity
    run_id: str
    status: str                         # created|initialized|running|stepping|paused|completed|stopped|failed
    simulation_time_s: float
    snapshot_version: int               # monotonic, increments each mutation

    # Model identity
    model_id: str
    model_version: str | None
    layout_id: str
    layout_version: str | None

    # Node states (for rendering)
    nodes: list[NodeSnapshot]

    # Entity positions (for token layer)
    entities: list[EntitySnapshot]

    # Route states (for edge styling)
    routes: list[RouteSnapshot]

    # Counters / KPIs
    counters: dict[str, int]

    # Alerts / recent events
    recent_events: list[EventSummary]   # last 20 events

    # Allowed actions (for UI controls)
    allowed_actions: list[str]          # ["step", "pause", "stop", "reset", ...]
```

### NodeSnapshot

```python
@dataclass(frozen=True)
class NodeSnapshot:
    node_id: str
    node_type: str
    display_name: str
    status: str
    queue_count: int
    queue_capacity: int
    current_entity_id: str | None
    progress: float
    active_fault: str | None
    active_hold: bool
    counters: dict[str, int]
```

### EntitySnapshot

```python
@dataclass(frozen=True)
class EntitySnapshot:
    entity_id: str
    entity_type: str
    current_node_id: str
    current_route_id: str | None
    quality_status: str
    rework_count: int
```

### RouteSnapshot

```python
@dataclass(frozen=True)
class RouteSnapshot:
    route_id: str
    from_node: str
    to_node: str
    active: bool
    entity_count: int
```

### EventSummary

```python
@dataclass(frozen=True)
class EventSummary:
    event_id: str
    simulation_time_s: float
    event_type: str
    target_id: str
    description: str
```

---

## 2. Snapshot vs Delta — MVP Decision

**Decision: Full snapshots only for MVP.**

| Approach | Pros | Cons |
|----------|------|------|
| Full snapshot | Simple, stateless client, easy resync | Larger payload, more bandwidth |
| Snapshot + delta | Smaller updates, lower bandwidth | Complex client state, resync logic |
| Event stream | Smallest updates, audit-ready | Client must reconstruct state |

**MVP choice:** Full snapshots at 10 Hz. Typical snapshot size: ~5-20 KB (50 nodes, 100 entities). At 10 Hz: 50-200 KB/s — well within budget.

**Future evolution (M6):** Add delta support. Client sends `snapshot_version`, server returns only changed nodes/entities since that version.

---

## 3. Command Envelope

```python
@dataclass(frozen=True)
class DMCommand:
    command_id: str                  # UUID
    run_id: str
    command_type: str                # initialize|step|auto_run|pause|resume|stop|reset|inject|hold|release
    target_id: str | None            # node_id for targeted commands
    parameters: dict[str, Any]       # command-specific params
    correlation_id: str | None       # links to previous command/event
    issued_time_s: float             # wall-clock timestamp
    requested_sim_time_s: float | None  # None = now
```

### CommandResult

```python
@dataclass(frozen=True)
class CommandResult:
    command_id: str
    status: str                      # accepted|rejected|completed|failed
    result_event_id: str | None      # scheduled event ID if accepted
    snapshot_version: int | None     # snapshot after command execution
    error: str | None
    timestamp_s: float
```

---

## 4. Command Types

| Type | Target | Parameters | Expected Result |
|------|--------|-----------|----------------|
| `initialize` | None | `{model_id, scenario_id?}` | Run → `initialized` |
| `step` | None | `{}` | One event dispatched |
| `auto_run` | None | `{speed_factor?}` | Run → `running` |
| `pause` | None | `{}` | Run → `paused` |
| `resume` | None | `{}` | Run → `running` |
| `stop` | None | `{}` | Run → `stopped` |
| `reset` | None | `{}` | Reinitialize |
| `inject_line_in` | node_id | `{entity_type}` | Entity enters at node |
| `inject_line_out` | node_id | `{entity_id}` | Entity exits from node |
| `hold` | node_id | `{reason}` | Node status → `held` |
| `release` | node_id | `{}` | Node status restored |
| `force_fail` | node_id | `{}` | Next quality check fails |
| `inject_breakdown` | node_id | `{duration_s?}` | Node status → `faulted` |
| `clear_breakdown` | node_id | `{}` | Node status restored |
| `operator_unavailable` | node_id | `{resource_id}` | Resource marked unavailable |
| `operator_available` | node_id | `{resource_id}` | Resource marked available |

---

## 5. WebSocket Transport

```
ws://host/ws/discrete/{run_id}
```

### Server → Client (SnapshotMessage)

```json
{
  "type": "snapshot",
  "run_id": "...",
  "snapshot_version": 42,
  "snapshot": { ... }
}
```

### Client → Server (CommandMessage)

```json
{
  "type": "command",
  "command": { ... }
}
```

### Server → Client (CommandAck)

```json
{
  "type": "command_result",
  "result": { ... }
}
```

### Reconnection

- Client stores `last_snapshot_version`.
- On reconnect, client sends `{"type": "resync", "last_version": 42}`.
- Server sends full snapshot at current version.
