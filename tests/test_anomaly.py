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


def test_t3410_expiry_detected():
    timer_ev = AnalysisEvent(
        timestamp=datetime(2024, 1, 15, 10, 0, 0),
        event_type="Timer",
        severity="ERROR",
        description="T3410 timer expiry detected",
    )
    anomalies = detect_anomalies([timer_ev])
    types = [a.event_type for a in anomalies]
    assert "Timer Expiry" in types


def test_signaling_storm_detected():
    from datetime import timedelta as _td
    base = datetime(2024, 1, 15, 10, 0, 0)
    events = [
        AnalysisEvent(
            timestamp=base + _td(milliseconds=i * 10),
            event_type="Signal",
            severity="INFO",
            description="",
        )
        for i in range(51)
    ]
    anomalies = detect_anomalies(events)
    types = [a.event_type for a in anomalies]
    assert "Signaling Storm" in types


def test_repeated_registration_failures_detected():
    events = [_ev("Registration Failure", offset_sec=i * 60) for i in range(3)]
    anomalies = detect_anomalies(events)
    types = [a.event_type for a in anomalies]
    assert "Repeated Attach Failures" in types


def test_no_rlf_cluster_for_single_rlf():
    events = [_ev("RLF", "ERROR", offset_sec=0)]
    anomalies = detect_anomalies(events)
    types = [a.event_type for a in anomalies]
    assert "RLF Cluster" not in types
