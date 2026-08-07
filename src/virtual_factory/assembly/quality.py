"""Quality disposition model for assembly domain.

M3-S01: Generic pass / fail / rework / scrap outcomes.
No probabilistic scenarios, no TIPA coupling.
"""

from __future__ import annotations

import enum


class QualityDisposition(str, enum.Enum):
    """Outcome of a quality inspection / gate decision."""
    PASS = "pass"
    FAIL = "fail"
    REWORK = "rework"
    SCRAP = "scrap"

    @property
    def is_terminal(self) -> bool:
        """True if this disposition represents a final outcome."""
        return self in (QualityDisposition.PASS, QualityDisposition.SCRAP)

    @property
    def requires_rework(self) -> bool:
        """True if this disposition requires rework processing."""
        return self == QualityDisposition.REWORK
