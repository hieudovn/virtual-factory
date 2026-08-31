"""Canonical ASSY production-line / sub-line identity model.

M6-S04B-I01: Establishes the TIPA ASSY identity hierarchy.
No runtime. No composition. No multi-context. No API.

Hierarchy:
    TIPA Plant
    └── ASSY Production Line
        ├── ASSY-SL01 — Hydraulic
        ├── ASSY-SL02 — Hydraulic
        ├── ASSY-SL03 — Hydraulic
        ├── ASSY-SL04 — Thermal
        ├── ASSY-SL05 — Thermal
        └── ASSY-SL06 — Thermal

Terminology:
    - ASSY is ONE Production Line
    - ASSY-SL01..SL06 are SIX Sub-lines within ASSY
    - Hydraulic / Thermal are input-process variant dimensions

Never:
    - "six ASSY lines"
    - "six production lines"
    - "Line 01..06"
    - line_id = "ASSY-SL01" (flattened)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import yaml


# ═══════════════════════════════════════════════════════════
# Identity Types
# ═══════════════════════════════════════════════════════════

VALID_VARIANTS = frozenset({"hydraulic", "thermal"})

CANONICAL_TIPA_SUB_LINE_IDS = frozenset({
    "ASSY-SL01", "ASSY-SL02", "ASSY-SL03",
    "ASSY-SL04", "ASSY-SL05", "ASSY-SL06",
})

CANONICAL_HYDRAULIC_IDS = frozenset({"ASSY-SL01", "ASSY-SL02", "ASSY-SL03"})
CANONICAL_THERMAL_IDS = frozenset({"ASSY-SL04", "ASSY-SL05", "ASSY-SL06"})


@dataclass(frozen=True, slots=True)
class AssySubLineIdentity:
    """Identity of one ASSY sub-line within the ASSY production line.

    Immutable.  Carries configuration metadata only — no runtime state.
    """

    production_line_id: str   # "ASSY"
    sub_line_id: str          # "ASSY-SL01"
    variant: str              # "hydraulic" | "thermal"
    label: str                # "ASSY-SL01 — Hydraulic"


@dataclass(frozen=True, slots=True)
class AssyProductionLineIdentity:
    """Identity of the TIPA ASSY production line and its sub-lines.

    Immutable.  Configuration/deployment metadata — no runtime state.
    Does NOT encode unconfirmed physical topology.
    """

    plant_id: str                                     # "TIPA"
    production_line_id: str                           # "ASSY"
    label: str                                        # "ASSY Line"
    sub_lines: tuple[AssySubLineIdentity, ...]         # exactly 6 for TIPA demo
    target_sub_line_for_exception: str                # "ASSY-SL03"

    def get_sub_line(self, sub_line_id: str) -> Optional[AssySubLineIdentity]:
        """Look up a sub-line identity by ID."""
        for sl in self.sub_lines:
            if sl.sub_line_id == sub_line_id:
                return sl
        return None

    @property
    def hydraulic_sub_lines(self) -> tuple[AssySubLineIdentity, ...]:
        return tuple(sl for sl in self.sub_lines if sl.variant == "hydraulic")

    @property
    def thermal_sub_lines(self) -> tuple[AssySubLineIdentity, ...]:
        return tuple(sl for sl in self.sub_lines if sl.variant == "thermal")


# ═══════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════

class SubLineIdentityError(ValueError):
    """Raised when sub-line identity configuration is invalid."""


def _validate_tipa_demo_identity(pline: AssyProductionLineIdentity) -> None:
    """Validate the TIPA demo sub-line identity configuration.

    Fails fast on structural errors. Specific to current TIPA baseline.
    """
    if not pline.plant_id:
        raise SubLineIdentityError("plant_id must not be empty")
    if pline.plant_id != "TIPA":
        raise SubLineIdentityError(
            f"plant_id must be 'TIPA' for current TIPA baseline, "
            f"got {pline.plant_id!r}"
        )
    if not pline.production_line_id:
        raise SubLineIdentityError("production_line_id must not be empty")
    if pline.production_line_id != "ASSY":
        raise SubLineIdentityError(
            f"production_line_id must be 'ASSY' for current TIPA baseline, "
            f"got {pline.production_line_id!r}"
        )

    ids = [sl.sub_line_id for sl in pline.sub_lines]

    if len(ids) != 6:
        raise SubLineIdentityError(
            f"Expected exactly 6 TIPA demo sub-lines, got {len(ids)}: {ids}"
        )

    if len(set(ids)) != len(ids):
        seen = set()
        dupes = [x for x in ids if x in seen or seen.add(x)]
        raise SubLineIdentityError(f"Duplicate sub_line_id values: {dupes}")

    for sl in pline.sub_lines:
        if sl.sub_line_id not in CANONICAL_TIPA_SUB_LINE_IDS:
            raise SubLineIdentityError(
                f"Unknown sub_line_id: {sl.sub_line_id!r}. "
                f"Expected one of {sorted(CANONICAL_TIPA_SUB_LINE_IDS)}"
            )

        if sl.production_line_id != pline.production_line_id:
            raise SubLineIdentityError(
                f"Sub-line {sl.sub_line_id} has production_line_id "
                f"{sl.production_line_id!r}, expected {pline.production_line_id!r}"
            )

        if sl.variant not in VALID_VARIANTS:
            raise SubLineIdentityError(
                f"Sub-line {sl.sub_line_id}: unknown variant {sl.variant!r}. "
                f"Expected one of {sorted(VALID_VARIANTS)}"
            )

        # Canonical variant mapping
        if sl.sub_line_id in CANONICAL_HYDRAULIC_IDS and sl.variant != "hydraulic":
            raise SubLineIdentityError(
                f"Sub-line {sl.sub_line_id}: must have variant 'hydraulic', "
                f"got {sl.variant!r}"
            )
        if sl.sub_line_id in CANONICAL_THERMAL_IDS and sl.variant != "thermal":
            raise SubLineIdentityError(
                f"Sub-line {sl.sub_line_id}: must have variant 'thermal', "
                f"got {sl.variant!r}"
            )

    target = pline.target_sub_line_for_exception
    target_ids = [sl.sub_line_id for sl in pline.sub_lines]
    if target not in target_ids:
        raise SubLineIdentityError(
            f"target_sub_line_for_exception {target!r} "
            f"is not a configured sub-line: {target_ids}"
        )


# ═══════════════════════════════════════════════════════════
# Config Loader (additive — does NOT affect AssyLineConfig)
# ═══════════════════════════════════════════════════════════

def load_assy_demo_identity_from_yaml(path: str) -> AssyProductionLineIdentity:
    """Load TIPA ASSY demo deployment/identity metadata from YAML.

    Reads the 'production_line' section of the config.  Does NOT
    read or affect the existing AssyLineConfig process/runtime
    sections (conveyor, station_durations, quality, etc.).
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    pline_data = data.get("production_line")
    if pline_data is None:
        raise SubLineIdentityError(
            f"No 'production_line' section found in {path}"
        )

    plant_id = pline_data.get("plant_id", "")
    line_id = pline_data.get("id", "")

    if not plant_id:
        raise SubLineIdentityError("production_line.plant_id is required")
    if not line_id:
        raise SubLineIdentityError("production_line.id is required")

    line_label = pline_data.get("label", line_id)

    # Parse sub-lines
    raw_sub_lines = pline_data.get("sub_lines", [])
    if not raw_sub_lines:
        raise SubLineIdentityError("production_line.sub_lines must not be empty")

    sub_lines: list[AssySubLineIdentity] = []
    for entry in raw_sub_lines:
        sl_id = entry.get("id", "")
        if not sl_id:
            raise SubLineIdentityError("Each sub_line must have an 'id' field")

        sub_lines.append(AssySubLineIdentity(
            production_line_id=line_id,   # "ASSY"
            sub_line_id=sl_id,            # "ASSY-SL01"
            variant=entry.get("variant", ""),
            label=entry.get("label", sl_id),
        ))

    demo_cfg = pline_data.get("demo", {})
    target = demo_cfg.get("target_sub_line_for_exception", "")

    identity = AssyProductionLineIdentity(
        plant_id=plant_id,
        production_line_id=line_id,
        label=line_label,
        sub_lines=tuple(sub_lines),
        target_sub_line_for_exception=target,
    )

    _validate_tipa_demo_identity(identity)
    return identity
