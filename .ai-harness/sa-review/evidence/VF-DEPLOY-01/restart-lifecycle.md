# VF-DEPLOY-01 — restart-lifecycle.md

## Test 1 — `docker restart` (§10)

```text
observations_before_restart = 16749     (accumulated in-memory P0 trace)
docker restart vf-assy-vf-assy-1
container becomes healthy               (health: starting -> healthy)
observations_after_restart  = 0         (in-memory runtime reset cleanly)
health=200  overview=200  sublines=200  (ASSY endpoints still work)
```

## Test 2 — `docker compose down` + `docker compose up` (§10)

```text
[+] down 2/2
 ✔ Container vf-assy-vf-assy-1 Removed
 ✔ Network vf-assy_default     Removed
[+] up 2/2
 ✔ Network vf-assy_default     Created
 ✔ Container vf-assy-vf-assy-1 Started
healthy_after_down_up = True
health=200  demo=200  obs=200
sub_lines_count = 6
```

## State model

| Item | Behavior |
|---|---|
| Simulation runtime state (WIP, quality, genealogy, release, observations) | **Intentionally ephemeral** — lives in the container process memory |
| On restart | Clean, valid HAPPY_PATH runtime at t≈0; observation trace empty |
| On `down` | Container and its default network removed |
| Persisted volumes | **None** for simulation state |
| Persisted data | None (no credentials, no state carryover) |

Decision: clean deterministic restart is preferred over hidden state
carryover — matches the accepted runtime's own behavior (a fresh process
starts a fresh demo). No persistence was added (not required by the gate).
