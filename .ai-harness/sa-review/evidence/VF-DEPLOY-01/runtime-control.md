# VF-DEPLOY-01 — runtime-control.md

Docker runtime control behavior via the accepted API (§8). All endpoints HTTP
200:

| Action | API | Result |
|---|---|---|
| Reset (HAPPY_PATH) | `POST /assy-demo/reset` `{"scenario":"HAPPY_PATH"}` | 200 |
| Step | `POST /assy-demo/step` | 200 |
| Run mode → MANUAL | `POST /assy-demo/run-mode` `{"mode":"MANUAL"}` | 200 |
| Run mode → AUTO | `POST /assy-demo/run-mode` `{"mode":"AUTO"}` | 200 |
| Select sub-line ASSY-SL03 | `POST /assy-demo/select` `{"sub_line_id":"ASSY-SL03"}` | 200 |
| Reset (AP06_FAIL_RETEST_PASS) | `POST /assy-demo/reset` `{"scenario":"AP06_FAIL_RETEST_PASS"}` | 200 |
| Reset (AP08_NG_REINSPECT_PASS) | `POST /assy-demo/reset` `{"scenario":"AP08_NG_REINSPECT_PASS"}` | 200 |
| Reset (FAILED_FINAL) | `POST /assy-demo/reset` `{"scenario":"FAILED_FINAL"}` | 200 |
| Reset (HAPPY_PATH again) | `POST /assy-demo/reset` `{"scenario":"HAPPY_PATH"}` | 200 |

Notes:
- Page reload/reset behavior is whatever the accepted runtime does — not
  redesigned in this gate (unchanged semantics).
- AUTO is the client-side presentation pacing of repeated STEP; Pause/Stop are
  client-side controls on the auto timer (accepted behavior, no new API).
- Scenario selection resets the line with the chosen scenario exactly as the
  accepted runtime does.
