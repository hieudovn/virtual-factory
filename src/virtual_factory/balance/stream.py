"""Material stream skeleton."""

from dataclasses import dataclass


@dataclass(slots=True)
class Stream:
    """Represents a future material stream between physical ports."""

    medium_id: str
    flow_rate_m3_s: float = 0.0
