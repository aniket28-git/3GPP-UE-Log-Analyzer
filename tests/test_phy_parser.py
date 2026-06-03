import pytest
from datetime import datetime
from core.log_entry import LogEntry
from core.parsers.phy_parser import parse_phy_measurement


def _entry(msg_type: str) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 10, 0, 0),
        layer="PHY",
        direction="DL",
        message_type=msg_type,
    )


def test_parse_rsrp_rsrq_sinr():
    entry = _entry("PHY Measurement RSRP=-88 RSRQ=-10 SINR=14")
    meas = parse_phy_measurement(entry)
    assert meas is not None
    assert meas.rsrp == pytest.approx(-88.0)
    assert meas.rsrq == pytest.approx(-10.0)
    assert meas.sinr == pytest.approx(14.0)


def test_parse_cqi_mcs():
    entry = _entry("PHY Indication CQI=12 MCS=20")
    meas = parse_phy_measurement(entry)
    assert meas is not None
    assert meas.cqi == 12
    assert meas.mcs == 20


def test_parse_pci_earfcn():
    entry = _entry("PHY Cell PCI=101 EARFCN=2850")
    meas = parse_phy_measurement(entry)
    assert meas is not None
    assert meas.pci == 101
    assert meas.earfcn == 2850


def test_parse_bler():
    entry = _entry("PHY HARQ BLER=0.05")
    meas = parse_phy_measurement(entry)
    assert meas is not None
    assert meas.bler == pytest.approx(0.05)


def test_returns_none_when_no_measurements():
    entry = _entry("PHY Unknown Message Without Any Metrics")
    meas = parse_phy_measurement(entry)
    assert meas is None


def test_partial_measurements_rsrp_only():
    entry = _entry("PHY Measurement RSRP=-100")
    meas = parse_phy_measurement(entry)
    assert meas is not None
    assert meas.rsrp == pytest.approx(-100.0)
    assert meas.rsrq is None
    assert meas.sinr is None


def test_measurement_timestamp_matches_entry():
    entry = _entry("PHY Measurement RSRP=-75")
    meas = parse_phy_measurement(entry)
    assert meas is not None
    assert meas.timestamp == entry.timestamp
