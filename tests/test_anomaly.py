import pytest
from datetime import datetime, timedelta
from core.log_entry import AnalysisEvent
from core.analysis.anomaly import detect_anomalies


def _ev(event_type: str, severity: str = "ERROR", offset_sec: int = 0,
         cause_code: int | None = None) -> AnalysisEvent:
    return AnalysisEvent(
        timestamp=datetime(2024, 1, 15, 10, 0, 0) + timedelta(seconds=offset_sec),
        event_type=event_type,
        severity=severity,
        description="test",
        cause_code=cause_code,
    )


def test_repeated_attach_failures_detected():
    events = [_ev("Attach Failure", offset_sec=i * 60) for i in range(3)]
    anomalies = detect_anomalies(events)
    types = [a.event_type for a in anomalies]
    assert "Repeated Attach Failures" in types


def test_no_anomaly_for_single_failure():
    events = [_ev("Attach Failure")]
    anomalies = detect_anomalies(events)
    types = [a.event_type for a in anomalies]
    assert "Repeated Attach Failures" not in types


def test_auth_loop_detected():
    events = [_ev("Authentication Failure", offset_sec=i * 10) for i in range(3)]
    anomalies = detect_anomalies(events)
    types = [a.event_type for a in anomalies]
    assert "Authentication Loop" in types


def test_rlf_cluster_detected():
    events = [_ev("RLF", "ERROR", offset_sec=i * 30) for i in range(2)]
    anomalies = detect_anomalies(events)
    types = [a.event_type for a in anomalies]
    assert "RLF Cluster" in types


def test_no_anomalies_on_empty():
    assert detect_anomalies([]) == []
