# 09-v2 — API, WebSocket, Security, and Audit Plan (Corrected)

**Date:** 2026-08-05  
**Replaces:** `09-api-websocket-security-and-audit-plan.md`  
**Corrections:** F-009, F-011

---

## 1. Run Ownership (C-009)

**M2–M5: One active DM run per application process.**

- `DiscreteRunService` owns one `DiscreteRunController` / `RunSession`.
- API paths remain run-scoped (`/api/discrete/runs/{run_id}/...`) for future multi-run.
- Attempting to create a second run while one is active returns `409 Conflict`.
- Stopped/completed/failed runs may be deleted before creating a new one.

---

## 2. Page Separation (C-008)

```
/                  → existing continuous dashboard (unchanged)
/discrete          → new DM page (separate module, separate globals)
```

Continuous files (`app.js`, `editor.js`, `builder.js`, `settings.js`) are NOT renamed or moved. DM modules live in `ui/static/discrete/`.

---

## 3. REST Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/discrete/runs` | Create run (rejects if active run exists) |
| `GET` | `/api/discrete/runs/{run_id}` | Get run status |
| `POST` | `/api/discrete/runs/{run_id}/commands` | Send command (canonical write path) |
| `GET` | `/api/discrete/runs/{run_id}/snapshots/latest` | Latest snapshot |
| `DELETE` | `/api/discrete/runs/{run_id}` | Delete completed/stopped/failed run |
| `WS` | `/ws/discrete/{run_id}` | Snapshots + status + resync (read-only from client) |

---

## 4. Security (unchanged policy)

**M2–M5:** No authentication. `--unsafe-demo` flag required. Localhost/controlled network only. Command audit records actor = "demo-user".

**M6:** API key authentication. Roles: viewer, operator, controller, admin.

---

## 5. Limits (M2–M5)

| Resource | Limit |
|----------|-------|
| Active runs | 1 per process |
| Max events per run | 1,000,000 (hard limit) |
| Event summary ring buffer | 1,000 (for WS broadcast) |
| Audit retention | All commands in memory (resets on run delete) |
| Snapshot max size | 100 KB |
| Command rate | 10/sec |
| WS message rate | Capped at 10 Hz |

---

## 6. Shared UI Extraction (C-008)

For the first DM demo:
- Extract only: `icons.js`, `widgets.js`, CSS variables (`tokens.css`), `resizer.js` → `shared/`.
- Add characterization tests before extraction.
- Do NOT rename or move `app.js`, `editor.js`, `builder.js`, `settings.js`.
- DM uses separate `/discrete` page with its own entry point.
- No "version pinning" — use stable interfaces and characterization tests instead.
