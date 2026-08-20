"""TIPA ASSY Customer Demo Scenario v1 — contract fixtures.

VF-DM-DEMO-ASSY-MES-01. Produces sanitized cross-repo contract fixtures from
REAL delivered ProjectedMessages (not invented). Pure extraction — does not
run or mutate the scenario.
"""

from __future__ import annotations

from virtual_factory.observation.projection import ProjectedMessage


def _serialize(m) -> dict:
    return {
        "message_key": m.key,
        "projection_id": m.projection_id,
        "message_type": m.message_type,
        "schema_name": m.schema_name,
        "schema_version": m.schema_version,
        "headers": dict(m.headers),
        "payload": dict(m.payload),
    }


def build_fixtures(messages: list[ProjectedMessage], run_id: str) -> dict:
    """Categorize REAL messages into contract fixtures. Pure (no run)."""
    msgs = [_serialize(m) for m in messages]

    def by_event(*event_types: str):
        return [m for m in msgs if m["payload"].get("event_type") in event_types]

    def by_station(station: str):
        return [m for m in msgs if m["payload"].get("station_id") == station]

    return {
        "contract_version": "tipa-assy-demo-v1",
        "run_id": run_id,
        "subline_id": "ASSY-SL01",
        "total_message_count": len(msgs),
        "fixtures": {
            "happy_completion": {
                "line_out_good": [
                    m for m in by_event("LINE_OUT")
                    if m["payload"].get("disposition") == "good"
                ][:1],
                "ap11_final_qc_pass": by_event("AP11_FINAL_QC_PASS")[:1],
            },
            "quality_fail_retest_pass": {
                "ap06_fail_attempt1": [
                    m for m in by_station("AP06")
                    if m["payload"].get("disposition") == "FAIL"
                ][:1],
                "ap06_pass_attempt2": [
                    m for m in by_station("AP06")
                    if m["payload"].get("disposition") == "PASS"
                    and m["payload"].get("attempt_number") == 2
                ][:1],
            },
            "genealogy": by_event("AP04_JOIN")[:1],
            "line_state": by_event("LINE_STATE_CHANGED"),
            "exception_raised_resolved": by_event("EXCEPTION_RAISED", "EXCEPTION_RESOLVED"),
            "downtime": by_event("DOWNTIME_START", "DOWNTIME_END"),
            "line_out_good_reject": by_event("LINE_OUT"),
            "oee_summary": by_event("OEE_SUMMARY"),
        },
    }
