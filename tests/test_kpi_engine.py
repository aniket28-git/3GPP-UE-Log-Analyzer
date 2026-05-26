import pytest
from datetime import datetime, timedelta
from core.log_entry import AnalysisEvent, RadioMeasurement
from core.analysis.kpi_engine import compute_kpis


def _ev(event_type: str, severity: str = "INFO", offset_sec: int = 0) -> AnalysisEvent:
    return AnalysisEvent(
        timestamp=datetime(2024, 1, 15, 10, 0, 0) + timedelta(seconds=offset_sec),
        event_type=event_type,
        severity=severity,
        description="",
    )


def _meas(rsrp: float, rsrq: float, sinr: float, offset_sec: int = 0) -> RadioMeasurement:
    return RadioMeasurement(
        timestamp=datetime(2024, 1, 15, 10, 0, 0) + timedelta(seconds=offset_sec),
        rsrp=rsrp,
        rsrq=rsrq,
        sinr=sinr,
    )


def test_attach_success_rate_100():
    events = [
        _ev("Attach Request", offset_sec=0),
        _ev("Attach Success", offset_sec=1),
    ]
    summary = compute_kpis(events, [])
    assert summary.attach_success_rate() == 100.0


def test_attach_success_rate_50():
    events = [
        _ev("Attach Request", offset_sec=0),
        _ev("Attach Failure", "ERROR", offset_sec=1),
        _ev("Attach Request", offset_sec=5),
        _ev("Attach Success", offset_sec=6),
    ]
    summary = compute_kpis(events, [])
    assert summary.attach_success_rate() == 50.0


def test_no_events_returns_none():
    summary = compute_kpis([], [])
    assert summary.attach_success_rate() is None
    assert summary.handover_success_rate() is None


def test_avg_rsrp():
    meas = [_meas(-85, -10, 12, i) for i in range(5)]
    summary = compute_kpis([], meas)
    assert summary.avg_rsrp() == pytest.approx(-85.0)


def test_rlf_count():
    events = [
        _ev("RLF", "ERROR", offset_sec=i * 60) for i in range(3)
    ]
    summary = compute_kpis(events, [])
    assert summary.rlf_count == 3


def test_kpi_list_not_empty():
    events = [_ev("Attach Request"), _ev("Attach Success", offset_sec=2)]
    meas = [_meas(-80, -9, 15)]
    summary = compute_kpis(events, meas)
    kpis = summary.to_kpi_list()
    names = [k.name for k in kpis]
    assert "Attach Success Rate" in names
    assert "Avg RSRP" in names
