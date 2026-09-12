"""VF-vNEXT-G18 — SH-WTP T108->DIST-P108 scenario-assumed topology fixture.

Materializes the FIRST bounded example of a :class:`ScenarioTopologyOverlay`
assumption for SH-WTP:

    T108 (shwtp/line1/l1_t108) --ASSUMED_FLOWS_TO--> DIST-P108 (shwtp/dist_p108)

This is an explicit simulation/design-stage assumption only. It is NOT PIM
semantic authority and NOT site truth:

- The exact unit-level T108 -> DIST-P108 relation remains NOT ESTABLISHED by PIM
  (T108-DIST-EVIDENCE — STILL_INSUFFICIENT; PIM evidence
  d10049801a1eb022a7fa2e83badabefb92fb7412).
- The assumed edge uses VF-LOCAL topology identities, never PIM canonical ids.
- It is reversible/replaceable and must be reconciled when future survey
  evidence resolves the relation.

This module is additive and dependency-light: it depends only on the generic
G18 overlay mechanism and the frozen T108 scope identity. It never modifies
PIM, the reference connectivity graph, G4, run-control, or any runtime.
"""

from __future__ import annotations

from virtual_factory.connectivity.scenario_overlay import (
    AssumedTopologyEdge,
    ScenarioTopologyOverlay,
)
from virtual_factory.shwtp.runtime import SHWTP_T108_SCOPE_PATH

# VF-local (NOT PIM) topology identity of the assumed DIST-P108 distribution
# sink. This mirrors the G16 readiness ``vf_path`` ("shwtp/dist_p108") and is a
# VF planning path, not a PIM canonical unit id.
SHWTP_DIST_P108_VF_PATH = "shwtp/dist_p108"

SHWTP_T108_DIST_P108_ASSUMPTION_ID = "ASSUME-SHW-T108-DIST-P108"
SHWTP_T108_DIST_P108_ASSUMPTION_VERSION = "1"
SHWTP_T108_DIST_P108_RELATION_TYPE = "ASSUMED_FLOWS_TO"
SHWTP_ASSUMED_OVERLAY_ID = "shwtp-scenario-assumed-topology"
SHWTP_ASSUMED_OVERLAY_VERSION = "1"
SHWTP_ASSUMED_OVERLAY_DOMAIN = "shwtp"

SHWTP_T108_DIST_P108_RATIONALE = (
    "Simulation/design-stage assumption only: the T108 clean-water outlet "
    "feeds distribution P108. NOT confirmed by PIM as site truth; reversible "
    "and replaceable when future survey evidence resolves the exact "
    "T108 -> DIST-P108 relation (T108-DIST-EVIDENCE — STILL_INSUFFICIENT)."
)


def build_shwtp_t108_dist_p108_assumption() -> AssumedTopologyEdge:
    """Build the single T108 -> DIST-P108 scenario assumption edge."""
    return AssumedTopologyEdge(
        assumption_id=SHWTP_T108_DIST_P108_ASSUMPTION_ID,
        version=SHWTP_T108_DIST_P108_ASSUMPTION_VERSION,
        source=SHWTP_T108_SCOPE_PATH.as_string(),
        target=SHWTP_DIST_P108_VF_PATH,
        relation_type=SHWTP_T108_DIST_P108_RELATION_TYPE,
        rationale=SHWTP_T108_DIST_P108_RATIONALE,
    )


def build_shwtp_t108_dist_p108_overlay() -> ScenarioTopologyOverlay:
    """Build the SH-WTP scenario-assumed topology overlay (one assumption)."""
    return ScenarioTopologyOverlay(
        overlay_id=SHWTP_ASSUMED_OVERLAY_ID,
        version=SHWTP_ASSUMED_OVERLAY_VERSION,
        domain=SHWTP_ASSUMED_OVERLAY_DOMAIN,
        edges=(build_shwtp_t108_dist_p108_assumption(),),
    )
