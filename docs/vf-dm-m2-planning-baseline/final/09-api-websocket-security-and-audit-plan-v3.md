# 09-v3 — API, WebSocket, Security, Audit (Final)

**Date:** 2026-08-05  
**Replaces:** `09-...-v2.md`  
**Corrections:** V2-F08, V2-F09, V2-F10

---

## 1. Run Ownership (unchanged)
One active DM run per process for M2–M5.

## 2. Page Separation (unchanged)
`/` = continuous dashboard. `/discrete` = DM page. No renames of continuous files.

## 3. REST Endpoints (unchanged)
`POST /api/discrete/runs/{run_id}/commands` = canonical write path. REST only.

## 4. WebSocket (unchanged)
`/ws/discrete/{run_id}` = snapshots, status, resync. Read-only from client.

## 5. Security (unchanged)
`--unsafe-demo` flag. No auth until M6.

## 6. Snapshot Size (C02-10)

| Level | Value | Action |
|-------|-------|--------|
| Target | < 100 KB | Normal |
| Hard limit | 200 KB | Send error envelope, never truncate |

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
    received_wall_clock: str          # ISO-8601 UTC
    accepted_simulation_time_s: float
    command_type: str
    target_id: str | None
    result_status: str
    rejection_code: str | None
    result_event_id: str | None
    snapshot_sequence: int
```

Hybrid replay requires this ordered audit log. In-memory for MVP; persistence at M6.

---

## 8. Limits

| Resource | Limit |
|----------|-------|
| Active runs | 1 |
| Max events/run | 1,000,000 |
| Event summary ring buffer | 1,000 |
| Command rate | 10/sec |
| Snapshot target | < 100 KB |
| WS envelope hard limit | 200 KB |
