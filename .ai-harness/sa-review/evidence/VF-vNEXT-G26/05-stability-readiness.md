# VF-vNEXT-G26 — Demo Stability / Readiness Results (D)

Not a load/performance benchmark. Demo-scale stability only.

- Script: `stability_smoke.py` (writes `stability-results.json`)
- Target: live server `python -m virtual_factory.main serve --host 127.0.0.1 --port 8099`
- Result: `all_ok = true`

## Checks

| Check | Detail | Result |
|---|---|---|
| `cold_start_registry` | server ready; workspaces `["TIPA","shwtp"]` | PASS |
| `select_tipa` | select returns TIPA view | PASS |
| `tipa_prepare_new_attempt` | session reset to a fresh attempt | PASS |
| `tipa_steps` | 120 steps, 0 non-200 | PASS |
| `tipa_reset` | 200 | PASS |
| `tipa_replay` | 200 (fresh run identity) | PASS |
| `tipa_new_attempt` | 200 (fresh run identity) | PASS |
| `select_shwtp` | select returns shwtp view | PASS |
| `shwtp_prepare_new_attempt` | fresh attempt | PASS |
| `shwtp_steps` | 150 steps, 0 non-200 | PASS |
| `shwtp_reset` | 200 | PASS |
| `shwtp_replay` | 200 | PASS |
| `shwtp_new_attempt` | 200 | PASS |
| `repeated_switching` | 20 alternating switches; TIPA `run_id` stable (no mutation) | PASS |
| `bad_requests_handled` | unknown workspace 404; unknown action 400; missing workspace_id 400; missing action 400 | PASS |
| `responsive_after` | registry still served after all of the above | PASS |
| `monitor_still_serves` | `/vnext/workspaces/TIPA/view` 200 | PASS |

## Scale / timing observation

- Total steps: **270** (120 TIPA + 150 shwtp), plus reset/replay/new_attempt and
  20 switches. Server never crashed; no 5xx observed.
- Wall time for the whole smoke: ~101–108 s including per-request HTTP round
  trips to the live server (sequential, single client). This is a **timing
  observation only**, not a performance assertion.
- The smoke was executed twice, independently, against the same live server:
  run 1 `elapsed_s=108.487` (`all_ok=true`, 17/17), run 2 `elapsed_s=101.147`
  (`all_ok=true`, 17/17). Both runs are recorded verbatim in
  `stability-smoke.out`; `stability-results.json` holds the latest run.


## Readiness conclusion

The demo scale (a few hundred steps, repeated switching and lifecycle actions,
invalid requests) is handled without server failure and remains responsive to
browser/API requests. No memory/leak or crash indicators were observed at this
scale. Suitable for a UAT demo.
