"""VF-CONTRACT-FINALITY-01 — verify Docker emits the enriched terminal fact.

Drives the FAILED_FINAL scenario over HTTP against a running runtime and
prints the AP06 quality facts + release absence. Used to confirm the rebuilt
Docker image emits the same enriched contract as native.
"""

import json
import sys
import urllib.request

B = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def post(u, b=None):
    req = urllib.request.Request(u, data=json.dumps(b or {}).encode(),
                                 method="POST",
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())


def get(u):
    return json.loads(urllib.request.urlopen(u, timeout=30).read().decode())


post(B + "/assy-demo/reset", {"scenario": "FAILED_FINAL"})
q = []
msgs = []
for _ in range(300):
    post(B + "/assy-demo/step")
    msgs = get(B + "/assy-demo/observations")["observations"]
    q = [m for m in msgs
         if m.get("message_type") == "mes.quality_result"
         and m["payload"].get("station_id") == "AP06"]
    if any(m["payload"].get("is_terminal") is True for m in q):
        break

print("ap06 records:", len(q))
for m in q:
    p = m["payload"]
    print("  ", p["record_id"], "attempt", p["attempt_number"], p["disposition"],
          "is_terminal=", p["is_terminal"], "terminal_state=", repr(p["terminal_state"]))
rel = [m for m in msgs if m.get("message_type") == "mes.release"]
term = [m for m in q if m["payload"].get("is_terminal") is True]
print("releases:", len(rel))
ok = (len(term) == 1
      and term[0]["payload"]["run_id"].startswith("ASSY-SL03:")
      and term[0]["payload"]["station_id"] == "AP06"
      and term[0]["payload"]["attempt_number"] == 2
      and term[0]["payload"]["terminal_state"] == "failed_final"
      and len(rel) == 0)
print("RESULT:", "OK" if ok else "FAIL")
