"""Package validator — cross-reference validation for VF-2 simulation packages.

Validates that objects, signals, topology edges, and scenarios are
internally consistent after a package has been loaded by ``package_loader``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import VF2Package, VF2ProcessEdge


@dataclass
class ValidationResult:
    """Outcome of a validation pass.

    Attributes:
        valid: ``True`` when no errors were found (warnings are allowed).
        errors: List of error messages.  Any error → ``valid = False``.
        warnings: List of warning messages (non-blocking).
    """

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────


def validate_package(pkg: VF2Package, strict: bool = False) -> ValidationResult:
    """Validate a loaded VF-2 package for internal consistency.

    Checks (in priority order):

    V1  — ``package_id`` is present and non-empty
    V2  — ``source_model.system == "PIM"``
    V3  — Duplicate ``simulation_object_id``
    V4  — Duplicate ``simulation_signal_id``
    V5  — Duplicate ``scenario_id``
    V6  — Every object has ``simulation_object_id`` + ``canonical_id``
    V7  — Every signal's ``canonical_asset_id`` references an object (warning)
    V8  — Every signal has ``simulation_signal_id`` with ``VF2.`` prefix
    V9  — Topology edge ``from`` exists in objects (compat warning / strict error)
    V10 — Topology edge ``to`` exists in objects (compat warning / strict error)
    V11 — Scenario ``trigger_simulation_object_id`` references a real object
    V12 — Scenario ``affected_simulation_signal_ids`` reference real signals (warning)
    V13 — Orphan signal (no matching object for ``canonical_asset_id``) (warning)
    V14 — ``schema_version == "1.0"``
    V15 — ``validation_rules`` have ``rule_id``, ``rule_name``, ``severity`` (warning)
    V16 — Scenario ``expected_effects[].signal_id`` references a valid signal (warning)

    Args:
        pkg: Loaded ``VF2Package``.
        strict: If ``True``, boundary endpoints are errors instead of warnings.

    Returns:
        ``ValidationResult`` with errors and warnings.
    """
    result = ValidationResult()

    # ── Build lookup sets ────────────────────────────────────────────
    object_ids: set[str] = set()
    object_canonical_ids: set[str] = set()
    for obj in pkg.objects:
        object_ids.add(obj.simulation_object_id)
        object_canonical_ids.add(obj.canonical_id)

    signal_ids: set[str] = set()
    signal_id_to_canonical_asset: dict[str, str] = {}
    for sig in pkg.signals:
        signal_ids.add(sig.simulation_signal_id)
        signal_id_to_canonical_asset[sig.simulation_signal_id] = sig.canonical_asset_id

    scenario_ids: set[str] = set()
    for s in pkg.scenarios:
        scenario_ids.add(s.scenario_id)

    # ── V1: package_id non-empty ─────────────────────────────────────
    if not pkg.package_id:
        result.errors.append("V1: package_id is empty or missing")
        result.valid = False

    # ── V2: source_model.system == "PIM" ──────────────────────────────
    if pkg.source_model.system != "PIM":
        result.errors.append(
            f"V2: source_model.system is '{pkg.source_model.system}', expected 'PIM'"
        )
        result.valid = False

    # ── V3: Duplicate object IDs ──────────────────────────────────────
    seen_obj: set[str] = set()
    for obj in pkg.objects:
        if obj.simulation_object_id in seen_obj:
            result.errors.append(
                f"V3: Duplicate simulation_object_id '{obj.simulation_object_id}'"
            )
            result.valid = False
        seen_obj.add(obj.simulation_object_id)

    # ── V4: Duplicate signal IDs ──────────────────────────────────────
    seen_sig: set[str] = set()
    for sig in pkg.signals:
        if sig.simulation_signal_id in seen_sig:
            result.errors.append(
                f"V4: Duplicate simulation_signal_id '{sig.simulation_signal_id}'"
            )
            result.valid = False
        seen_sig.add(sig.simulation_signal_id)

    # ── V5: Duplicate scenario IDs ────────────────────────────────────
    seen_scn: set[str] = set()
    for scn in pkg.scenarios:
        if scn.scenario_id in seen_scn:
            result.errors.append(
                f"V5: Duplicate scenario_id '{scn.scenario_id}'"
            )
            result.valid = False
        seen_scn.add(scn.scenario_id)

    # ── V6: Object identity fields ────────────────────────────────────
    for obj in pkg.objects:
        if not obj.simulation_object_id:
            result.errors.append("V6: Object has empty simulation_object_id")
            result.valid = False
        if not obj.canonical_id:
            result.errors.append(
                f"V6: Object '{obj.simulation_object_id}' has empty canonical_id"
            )
            result.valid = False

    # ── V8: Signal ID prefix check (before V7) ────────────────────────
    for sig in pkg.signals:
        if not sig.simulation_signal_id.startswith("VF2."):
            result.errors.append(
                f"V8: Signal '{sig.simulation_signal_id}' does not start with 'VF2.'"
            )
            result.valid = False

    # ── V7 + V13: Signal canonical_asset_id references ───────────────
    for sig in pkg.signals:
        if sig.canonical_asset_id not in object_canonical_ids:
            result.warnings.append(
                f"V7/V13: Signal '{sig.simulation_signal_id}' references "
                f"canonical_asset_id '{sig.canonical_asset_id}' "
                f"which is not in any object"
            )

    # ── V9 + V10: Topology edge endpoints ────────────────────────────
    for edge in pkg.topology.process_edges:
        _check_edge_endpoint(edge, "from", edge.from_simulation_object_id,
                             object_ids, strict, result)
        _check_edge_endpoint(edge, "to", edge.to_simulation_object_id,
                             object_ids, strict, result)

    for edge in pkg.topology.electrical_edges:
        _check_edge_endpoint(edge, "from", edge.from_simulation_object_id,
                             object_ids, strict, result)
        _check_edge_endpoint(edge, "to", edge.to_simulation_object_id,
                             object_ids, strict, result)

    # ── V11: Scenario trigger references real object ──────────────────
    for scn in pkg.scenarios:
        if scn.trigger_simulation_object_id:
            if scn.trigger_simulation_object_id not in object_ids:
                result.errors.append(
                    f"V11: Scenario '{scn.scenario_id}' trigger "
                    f"simulation_object_id '{scn.trigger_simulation_object_id}' "
                    f"does not exist in objects"
                )
                result.valid = False

    # ── V12: Affected signal IDs exist ────────────────────────────────
    for scn in pkg.scenarios:
        for aff_sid in scn.affected_simulation_signal_ids:
            if aff_sid and aff_sid not in signal_ids:
                result.warnings.append(
                    f"V12: Scenario '{scn.scenario_id}' references "
                    f"affected_simulation_signal_id '{aff_sid}' "
                    f"which is not in signals"
                )

    # ── V14: schema_version ───────────────────────────────────────────
    if pkg.schema_version != "1.0":
        result.errors.append(
            f"V14: schema_version is '{pkg.schema_version}', expected '1.0'"
        )
        result.valid = False

    # ── V15: Validation rules completeness ───────────────────────────
    for rule in pkg.validation_rules:
        if not rule.rule_id:
            result.warnings.append("V15: Validation rule missing rule_id")
        if not rule.rule_name:
            result.warnings.append("V15: Validation rule missing rule_name")
        if rule.severity not in ("error", "warning", "info"):
            result.warnings.append(
                f"V15: Validation rule '{rule.rule_id}' has unrecognized severity "
                f"'{rule.severity}'"
            )

    # ── V16: Expected effects signal_id reference ─────────────────────
    for scn in pkg.scenarios:
        for eff in scn.expected_effects:
            if eff.signal_id and eff.signal_id not in signal_ids:
                result.warnings.append(
                    f"V16: Scenario '{scn.scenario_id}' expected_effect "
                    f"signal_id '{eff.signal_id}' does not exist in signals"
                )

    return result


# ──────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────


def _check_edge_endpoint(
    edge: VF2ProcessEdge,
    side: str,
    value: str,
    object_ids: set[str],
    strict: bool,
    result: ValidationResult,
) -> None:
    """Check one endpoint of a topology edge (V9 / V10)."""
    if value in object_ids:
        return

    msg = (
        f"Topology edge {side}='{value}' "
        f"(relation_type='{edge.relation_type}') "
        f"not found in objects[]"
    )
    if strict:
        result.errors.append(f"V9/V10: {msg}")
        result.valid = False
    else:
        result.warnings.append(
            f"V9/V10: Boundary endpoint ({side}): {msg} — treated as external"
        )
