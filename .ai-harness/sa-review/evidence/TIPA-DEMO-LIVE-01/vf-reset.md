# VF-S11 — Reset / recovery proof

## Scenario reset

- command: `POST /assy-demo/reset` `{"scenario": "HAPPY_PATH"}`
- elapsed: **93.5 ms**
- health recheck after reset: `GET /health` → 200 `ok` in **3.1 ms**

## Generation change (verified)

```text
before reset generations: ['R1', 'R2', 'R3', 'R4', 'R5']
new generation after reset: R6
```

A scenario reset bumps the run generation exactly once (per the accepted
run-identity contract: time regression → one generation transition).

## Message-key non-reuse

- messages before reset: 1915
- messages after reset (new run): 6
- reused keys (new messages colliding with old): **0**

New-run messages do NOT reuse prior message keys.

## Container restart (measured)

```text
docker restart vf-assy-vf-assy-1 → healthy
elapsed: 6.0 s
health after restart: GET /health → 200
```

## VF recovery timing summary (for MES-S11)

| Operation | Measured |
|---|---|
| Scenario reset (`POST /assy-demo/reset`) | 93.5 ms |
| Health recheck (`GET /health`) | 3.1 ms |
| Container restart → healthy | 6.0 s |

All well within the `< 5 min` full-system-ready target.
