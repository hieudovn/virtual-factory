"""Tests for the Maintenance Event Generator."""

from virtual_factory.maintenance.event_generator import (
    EventGenerator,
    EventType,
    AlarmEvent,
    WorkOrder,
    RepairAction,
    DowntimeEvent,
    FailureEvent,
    SparePartReplacement,
    InspectionEvent,
    OperatorLog,
)


class TestEventGenerator:
    def test_record_alarm(self):
        gen = EventGenerator()
        alarm = gen.record_alarm("COMP01", "HIGH_VIB", 150.0, severity="HIGH")
        assert alarm.event_type == EventType.ALARM
        assert alarm.equipment_id == "COMP01"
        assert alarm.alarm_id == "HIGH_VIB"
        assert alarm.severity == "HIGH"
        assert len(gen.events) == 1

    def test_record_work_order(self):
        gen = EventGenerator()
        wo = gen.record_work_order("COMP01", 200.0, "WO-001", priority="HIGH")
        assert wo.event_type == EventType.WORK_ORDER
        assert wo.work_order_id == "WO-001"
        assert wo.priority == "HIGH"
        assert wo.status == "OPEN"

    def test_record_repair(self):
        gen = EventGenerator()
        repair = gen.record_repair(
            "COMP01", 300.0,
            action_type="replace",
            duration_s=7200.0,
            parts_replaced=["BRG-001", "SEAL-002"],
            successful=True,
        )
        assert repair.event_type == EventType.REPAIR
        assert repair.action_type == "replace"
        assert len(repair.parts_replaced) == 2
        assert repair.successful

    def test_record_downtime(self):
        gen = EventGenerator()
        dt = gen.record_downtime("COMP01", 400.0, downtime_type="unplanned",
                                 duration_s=3600.0, reason="Bearing failure")
        assert dt.event_type == EventType.DOWNTIME
        assert dt.downtime_type == "unplanned"
        assert dt.duration_s == 3600.0

    def test_record_failure(self):
        gen = EventGenerator()
        failure = gen.record_failure("COMP01", 500.0, failure_mode="Bearing seizure",
                                     fault_id="bearing_wear", downtime_s=28800.0)
        assert failure.event_type == EventType.FAILURE
        assert failure.fault_id == "bearing_wear"
        assert failure.downtime_s == 28800.0

    def test_record_spare_part(self):
        gen = EventGenerator()
        sp = gen.record_spare_part("COMP01", 600.0, part_number="BRG-1234",
                                   part_name="DE Bearing", quantity=2)
        assert sp.event_type == EventType.SPARE_PART
        assert sp.part_number == "BRG-1234"
        assert sp.quantity == 2

    def test_record_inspection(self):
        gen = EventGenerator()
        insp = gen.record_inspection("COMP01", 700.0, inspection_type="vibration",
                                     findings="Elevated DE vibration")
        assert insp.event_type == EventType.INSPECTION
        assert insp.inspection_type == "vibration"

    def test_record_operator_log(self):
        gen = EventGenerator()
        log = gen.record_operator_log("COMP01", 800.0, operator_id="OP01",
                                      log_category="observation",
                                      description="Unusual noise from DE bearing")
        assert log.event_type == EventType.OPERATOR_LOG
        assert log.operator_id == "OP01"

    def test_get_by_equipment(self):
        gen = EventGenerator()
        gen.record_alarm("COMP01", "VIB_HIGH", 100.0)
        gen.record_alarm("PUMP01", "FLOW_LOW", 150.0)
        gen.record_alarm("COMP01", "TEMP_HIGH", 200.0)

        comp_events = gen.get_by_equipment("COMP01")
        assert len(comp_events) == 2

        pump_events = gen.get_by_equipment("PUMP01")
        assert len(pump_events) == 1

    def test_get_by_type(self):
        gen = EventGenerator()
        gen.record_alarm("COMP01", "A1", 100.0)
        gen.record_work_order("COMP01", 200.0, "WO1")
        gen.record_repair("COMP01", 300.0)

        alarms = gen.get_by_type(EventType.ALARM)
        assert len(alarms) == 1
        assert isinstance(alarms[0], AlarmEvent)

        wos = gen.get_by_type(EventType.WORK_ORDER)
        assert len(wos) == 1
        assert isinstance(wos[0], WorkOrder)

    def test_get_time_range(self):
        gen = EventGenerator()
        gen.record_alarm("COMP01", "A1", 100.0)
        gen.record_alarm("COMP01", "A2", 200.0)
        gen.record_alarm("COMP01", "A3", 300.0)

        mid = gen.get_time_range(150.0, 250.0)
        assert len(mid) == 1
        assert mid[0].alarm_id == "A2"

    def test_to_records(self):
        gen = EventGenerator()
        gen.record_alarm("COMP01", "HIGH_VIB", 100.0, severity="HIGH")
        gen.record_repair("COMP01", 300.0, duration_s=7200.0,
                          parts_replaced=["BRG-001"])

        records = gen.to_records()
        assert len(records) == 2
        assert records[0]["event_type"] == "alarm"
        assert records[0]["severity"] == "HIGH"
        assert records[1]["event_type"] == "repair"
        assert records[1]["duration_s"] == 7200.0

    def test_reset(self):
        gen = EventGenerator()
        gen.record_alarm("COMP01", "A1", 100.0)
        gen.reset()
        assert len(gen.events) == 0
