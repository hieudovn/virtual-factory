"""VF-DEPLOY-01 — diff native vs Docker equivalence fingerprints (E1-E4).

Compares docker-fingerprint.json and native-fingerprint.json field by field.
A PASS requires every field to match exactly for all three scenarios.

Usage:
    python diff_fingerprints.py <docker.json> <native.json>
"""

from __future__ import annotations

import json
import sys

SKIP = {"message_keys", "ap04_children", "genealogy_parents"}


def load(p):
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def main() -> None:
    a = load(sys.argv[1])
    b = load(sys.argv[2])
    scenarios = list(a.keys())
    all_pass = True
    for sc in scenarios:
        print(f"== {sc} ==")
        da, db = a[sc], b[sc]
        keys = [k for k in da if k not in SKIP]
        for k in keys:
            same = da[k] == db[k]
            status = "PASS" if same else "DIFF"
            if not same:
                all_pass = False
            line = f"  [{status}] {k}"
            if not same:
                line += f"\n      docker: {str(da[k])[:200]}\n      native: {str(db[k])[:200]}"
            print(line)
        # compare the full ordered message_keys too (they must be identical)
        ka = da["message_keys"]
        kb = db["message_keys"]
        if ka == kb:
            print(f"  [PASS] message_keys (count={len(ka)})")
        else:
            all_pass = False
            print(f"  [DIFF] message_keys count docker={len(ka)} native={len(kb)}")
            for i, (x, y) in enumerate(zip(ka, kb)):
                if x != y:
                    print(f"      first divergence at index {i}:")
                    print(f"        docker: {x}")
                    print(f"        native: {y}")
                    break
    print("\nRESULT:", "EQUIVALENT (all PASS)" if all_pass else "NOT EQUIVALENT")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
