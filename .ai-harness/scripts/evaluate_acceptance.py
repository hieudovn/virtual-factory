#!/usr/bin/env python3
"""evaluate_acceptance.py — Rule-based acceptance criterion evaluator.

Usage:
    python .ai-harness/scripts/evaluate_acceptance.py <evidence.json> <contract.json>

Converts acceptance items from UNKNOWN to PASS/FAIL/UNKNOWN based on
explicit rule operators applied to evidence fields.
"""

from __future__ import annotations

import json
import sys
from typing import Any


# Supported operators
_OPERATORS = {
    "equals": lambda actual, expected: actual == expected,
    "not_equals": lambda actual, expected: actual != expected,
    "is_true": lambda actual, _: actual is True,
    "is_false": lambda actual, _: actual is False,
    "is_present": lambda actual, _: actual is not None and actual != "" and actual != [],
    "is_empty": lambda actual, _: actual is None or actual == "" or actual == [],
    "greater_than_or_equal": lambda actual, expected: isinstance(actual, (int, float)) and actual >= expected,
    "less_than_or_equal": lambda actual, expected: isinstance(actual, (int, float)) and actual <= expected,
    "sha_equals": lambda actual, expected: str(actual).lower() == str(expected).lower(),
    "contains": lambda actual, expected: expected in str(actual) if actual else False,
    "not_contains": lambda actual, expected: expected not in str(actual) if actual else True,
    "all_success": lambda actual, _: all(
        s.get("conclusion") == "success" for s in actual
    ) if isinstance(actual, list) else False,
}


def _resolve_field(data: dict, field_path: str) -> Any:
    """Resolve a dotted field path like 'implementation.commit_exists_remotely'."""
    parts = field_path.split(".")
    current: Any = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def evaluate_acceptance(evidence: dict, contract: dict) -> list[dict]:
    """Evaluate acceptance criteria against evidence."""
    results: list[dict] = []
    criteria = contract.get("acceptance_criteria", [])

    for item in criteria:
        rule = item.get("rule")
        if not rule:
            results.append({
                "id": item["id"],
                "description": item.get("description", ""),
                "result": "UNKNOWN",
                "evidence": "No executable rule defined",
            })
            continue

        field_path = rule.get("field", "")
        operator_name = rule.get("operator", "")
        expected = rule.get("expected")

        if operator_name not in _OPERATORS:
            results.append({
                "id": item["id"],
                "description": item.get("description", ""),
                "result": "UNKNOWN",
                "evidence": f"Unsupported operator: {operator_name}",
            })
            continue

        actual = _resolve_field(evidence, field_path)
        operator_fn = _OPERATORS[operator_name]

        try:
            passed = operator_fn(actual, expected)
        except Exception as e:
            results.append({
                "id": item["id"],
                "description": item.get("description", ""),
                "result": "UNKNOWN",
                "evidence": f"Operator evaluation error: {e}",
            })
            continue

        result = "PASS" if passed else "FAIL"
        evidence_str = (
            f"field={field_path} operator={operator_name} "
            f"expected={expected} actual={actual} → {result}"
        )
        results.append({
            "id": item["id"],
            "description": item.get("description", ""),
            "result": result,
            "evidence": evidence_str,
        })

    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate acceptance criteria against evidence"
    )
    parser.add_argument("evidence_file", help="Path to evidence JSON")
    parser.add_argument("contract_file", help="Path to task contract JSON")
    parser.add_argument("--output", help="Path to write updated evidence JSON")
    args = parser.parse_args()

    with open(args.evidence_file, "r", encoding="utf-8") as f:
        evidence = json.load(f)
    with open(args.contract_file, "r", encoding="utf-8") as f:
        contract = json.load(f)

    results = evaluate_acceptance(evidence, contract)
    evidence["acceptance"] = results

    passes = sum(1 for r in results if r["result"] == "PASS")
    fails = sum(1 for r in results if r["result"] == "FAIL")
    unknowns = sum(1 for r in results if r["result"] == "UNKNOWN")

    print(f"Acceptance: {passes} PASS, {fails} FAIL, {unknowns} UNKNOWN")
    for r in results:
        print(f"  [{r['result']}] {r['id']}: {r['description']}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(evidence, f, indent=2)

    if fails > 0 or unknowns > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
