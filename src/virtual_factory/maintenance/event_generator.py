"""Event & Maintenance Generator.

Generates realistic industrial events and maintenance records that
influence equipment health and telemetry through the fault engine.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    ALARM = "alarm"
    OPERATOR_LOG = "operator_log"
    INSPECTION = "inspection"
    WORK_ORDER = "work_order"
    FAILURE = "failure"
    REPAIR = "repair"
    DOWNTIME = "downtime"
    SPARE_PART = "spare_part"


@dataclass(slots=True)
class MaintenanceEvent:
    """Base class for all maintenance-related events."""
    event_id: str
    equipment_id: str
    timestamp_s: float
    event_type: EventType = EventType.ALARM
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AlarmEvent(MaintenanceEvent):
    """An alarm that triggered on equipment."""
    alarm_id: str = ""
    severity: str = "WARNING"
    acknowledged: bool = False

    def __post_init__(self) -> None:
        self.event_type = EventType.ALARM


@dataclass(slots=True)
class OperatorLog(MaintenanceEvent):
    """An operator observation or action log."""
    operator_id: str = ""
    log_category: str = "observation"

    def __post_init__(self) -> None:
        self.event_type = EventType.OPERATOR_LOG


@dataclass(slots=True)
class InspectionEvent(MaintenanceEvent):
    """A scheduled or triggered inspection."""
    inspection_type: str = "visual"
    findings: str = ""
    next_inspection_s: float = 0.0

    def __post_init__(self) -> None:
        self.event_type = EventType.INSPECTION


@dataclass(slots=True)
class WorkOrder(MaintenanceEvent):
    """A work order for maintenance."""
    work_order_id: str = ""
    priority: str = "MEDIUM"
    status: str = "OPEN"
    assigned_to: str = ""

    def __post_init__(self) -> None:
        self.event_type = EventType.WORK_ORDER


@dataclass(slots=True)
class FailureEvent(MaintenanceEvent):
    """An equipment failure event."""
    failure_mode: str = ""
    fault_id: str = ""
    downtime_s: float = 0.0

    def __post_init__(self) -> None:
        self.event_type = EventType.FAILURE


@dataclass(slots=True)
class RepairAction(MaintenanceEvent):
    """A repair action taken on equipment."""
    action_type: str = "repair"
    duration_s: float = 0.0
    parts_replaced: list[str] = field(default_factory=list)
    successful: bool = True

    def __post_init__(self) -> None:
        self.event_type = EventType.REPAIR


@dataclass(slots=True)
class DowntimeEvent(MaintenanceEvent):
    """Equipment downtime event."""
    downtime_type: str = "unplanned"
    duration_s: float = 0.0
    reason: str = ""

    def __post_init__(self) -> None:
        self.event_type = EventType.DOWNTIME


@dataclass(slots=True)
class SparePartReplacement(MaintenanceEvent):
    """Spare part replacement record."""
    part_number: str = ""
    part_name: str = ""
    quantity: int = 1
    reason: str = "scheduled"

    def __post_init__(self) -> None:
        self.event_type = EventType.SPARE_PART


@dataclass
class EventGenerator:
    """Generates maintenance and event records for a simulation run.

    Tracks event history and provides structured exports for analytics.

    Usage::

        gen = EventGenerator()
        gen.record_alarm("COMP01", "HIGH_VIBRATION", 150.0, severity="HIGH")
        gen.record_inspection("COMP01", 200.0, findings="Bearing wear observed")
        gen.record_work_order("COMP01", 210.0, "WO-001", priority="HIGH")
        gen.record_repair("COMP01", 250.0, duration_s=7200.0,
                          parts_replaced=["BRG-1234"])
        # Export
        events_df = gen.to_records()
    """

    events: list[MaintenanceEvent] = field(default_factory=list)
    _event_counter: dict[str, int] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Event recording
    # ------------------------------------------------------------------

    def record_alarm(
        self,
        equipment_id: str,
        alarm_id: str,
        timestamp_s: float,
        severity: str = "WARNING",
        description: str = "",
        acknowledged: bool = False,
    ) -> AlarmEvent:
        event = AlarmEvent(
            event_id=self._next_id("ALM"),
            equipment_id=equipment_id,
            timestamp_s=timestamp_s,
            alarm_id=alarm_id,
            severity=severity,
            acknowledged=acknowledged,
            description=description,
        )
        self.events.append(event)
        return event

    def record_operator_log(
        self,
        equipment_id: str,
        timestamp_s: float,
        operator_id: str = "",
        log_category: str = "observation",
        description: str = "",
    ) -> OperatorLog:
        event = OperatorLog(
            event_id=self._next_id("LOG"),
            equipment_id=equipment_id,
            timestamp_s=timestamp_s,
            operator_id=operator_id,
            log_category=log_category,
            description=description,
        )
        self.events.append(event)
        return event

    def record_inspection(
        self,
        equipment_id: str,
        timestamp_s: float,
        inspection_type: str = "visual",
        findings: str = "",
        next_inspection_s: float = 0.0,
        description: str = "",
    ) -> InspectionEvent:
        event = InspectionEvent(
            event_id=self._next_id("INS"),
            equipment_id=equipment_id,
            timestamp_s=timestamp_s,
            inspection_type=inspection_type,
            findings=findings,
            next_inspection_s=next_inspection_s,
            description=description,
        )
        self.events.append(event)
        return event

    def record_work_order(
        self,
        equipment_id: str,
        timestamp_s: float,
        work_order_id: str = "",
        priority: str = "MEDIUM",
        status: str = "OPEN",
        assigned_to: str = "",
        description: str = "",
    ) -> WorkOrder:
        event = WorkOrder(
            event_id=self._next_id("WO"),
            equipment_id=equipment_id,
            timestamp_s=timestamp_s,
            work_order_id=work_order_id or f"WO-{self._event_counter.get('WO', 0):04d}",
            priority=priority,
            status=status,
            assigned_to=assigned_to,
            description=description,
        )
        self.events.append(event)
        return event

    def record_failure(
        self,
        equipment_id: str,
        timestamp_s: float,
        failure_mode: str = "",
        fault_id: str = "",
        downtime_s: float = 0.0,
        description: str = "",
    ) -> FailureEvent:
        event = FailureEvent(
            event_id=self._next_id("FLR"),
            equipment_id=equipment_id,
            timestamp_s=timestamp_s,
            failure_mode=failure_mode,
            fault_id=fault_id,
            downtime_s=downtime_s,
            description=description,
        )
        self.events.append(event)
        return event

    def record_repair(
        self,
        equipment_id: str,
        timestamp_s: float,
        action_type: str = "repair",
        duration_s: float = 0.0,
        parts_replaced: list[str] | None = None,
        successful: bool = True,
        description: str = "",
    ) -> RepairAction:
        event = RepairAction(
            event_id=self._next_id("RPR"),
            equipment_id=equipment_id,
            timestamp_s=timestamp_s,
            action_type=action_type,
            duration_s=duration_s,
            parts_replaced=parts_replaced or [],
            successful=successful,
            description=description,
        )
        self.events.append(event)
        return event

    def record_downtime(
        self,
        equipment_id: str,
        timestamp_s: float,
        downtime_type: str = "unplanned",
        duration_s: float = 0.0,
        reason: str = "",
        description: str = "",
    ) -> DowntimeEvent:
        event = DowntimeEvent(
            event_id=self._next_id("DT"),
            equipment_id=equipment_id,
            timestamp_s=timestamp_s,
            downtime_type=downtime_type,
            duration_s=duration_s,
            reason=reason,
            description=description,
        )
        self.events.append(event)
        return event

    def record_spare_part(
        self,
        equipment_id: str,
        timestamp_s: float,
        part_number: str = "",
        part_name: str = "",
        quantity: int = 1,
        reason: str = "scheduled",
        description: str = "",
    ) -> SparePartReplacement:
        event = SparePartReplacement(
            event_id=self._next_id("SPR"),
            equipment_id=equipment_id,
            timestamp_s=timestamp_s,
            part_number=part_number,
            part_name=part_name,
            quantity=quantity,
            reason=reason,
            description=description,
        )
        self.events.append(event)
        return event

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_by_equipment(self, equipment_id: str) -> list[MaintenanceEvent]:
        return [e for e in self.events if e.equipment_id == equipment_id]

    def get_by_type(self, event_type: EventType) -> list[MaintenanceEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def get_time_range(self, start_s: float, end_s: float) -> list[MaintenanceEvent]:
        return [e for e in self.events if start_s <= e.timestamp_s <= end_s]

    def to_records(self) -> list[dict[str, Any]]:
        """Export all events as a list of dicts for DataFrame/Parquet."""
        records = []
        for e in self.events:
            rec = {
                "event_id": e.event_id,
                "event_type": e.event_type.value,
                "equipment_id": e.equipment_id,
                "timestamp_s": e.timestamp_s,
                "description": e.description,
            }
            rec.update(e.metadata)
            # Add type-specific fields
            if isinstance(e, AlarmEvent):
                rec["alarm_id"] = e.alarm_id
                rec["severity"] = e.severity
                rec["acknowledged"] = e.acknowledged
            elif isinstance(e, WorkOrder):
                rec["work_order_id"] = e.work_order_id
                rec["priority"] = e.priority
                rec["status"] = e.status
            elif isinstance(e, RepairAction):
                rec["action_type"] = e.action_type
                rec["duration_s"] = e.duration_s
                rec["parts_replaced"] = ",".join(e.parts_replaced)
                rec["successful"] = e.successful
            elif isinstance(e, DowntimeEvent):
                rec["downtime_type"] = e.downtime_type
                rec["duration_s"] = e.duration_s
                rec["reason"] = e.reason
            elif isinstance(e, FailureEvent):
                rec["failure_mode"] = e.failure_mode
                rec["fault_id"] = e.fault_id
                rec["downtime_s"] = e.downtime_s
            elif isinstance(e, SparePartReplacement):
                rec["part_number"] = e.part_number
                rec["part_name"] = e.part_name
                rec["quantity"] = e.quantity
            elif isinstance(e, InspectionEvent):
                rec["inspection_type"] = e.inspection_type
                rec["findings"] = e.findings
            elif isinstance(e, OperatorLog):
                rec["operator_id"] = e.operator_id
                rec["log_category"] = e.log_category
            records.append(rec)
        return records

    def reset(self) -> None:
        """Clear all events."""
        self.events.clear()
        self._event_counter.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _next_id(self, prefix: str) -> str:
        self._event_counter[prefix] = self._event_counter.get(prefix, 0) + 1
        return f"{prefix}-{self._event_counter[prefix]:06d}"
