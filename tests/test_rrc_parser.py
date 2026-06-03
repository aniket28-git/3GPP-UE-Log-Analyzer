import pytest
from datetime import datetime
from core.log_entry import LogEntry
from core.parsers.rrc_parser import parse_rrc_fields, is_handover, is_rlf, enrich_entry


def _entry(msg_type: str, layer: str = "RRC", decoded: dict | None = None) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 10, 0, 0),
        layer=layer,
        direction="DL",
        message_type=msg_type,
        decoded=decoded or {},
    )


def test_parse_pci():
    entry = _entry("RRCConnectionSetup PCI=42 EARFCN=1850")
    fields = parse_rrc_fields(entry)
    assert fields["pci"] == 42


def test_parse_earfcn():
    entry = _entry("MeasurementReport EARFCN=1850 RSRP=-85")
    fields = parse_rrc_fields(entry)
    assert fields["earfcn"] == 1850


def test_parse_rsrp_rsrq():
    entry = _entry("MeasurementReport RSRP=-95 RSRQ=-11")
    fields = parse_rrc_fields(entry)
    assert fields["rsrp"] == pytest.approx(-95.0)
    assert fields["rsrq"] == pytest.approx(-11.0)


def test_parse_sinr():
    entry = _entry("MeasurementReport SINR=18")
    fields = parse_rrc_fields(entry)
    assert fields["sinr"] == pytest.approx(18.0)


def test_parse_failure_cause_description():
    entry = _entry("RRCConnectionReestablishmentRequest reestablishmentCause=rlc-MaxNumRetx")
    fields = parse_rrc_fields(entry)
    assert fields["failure_cause"] == "rlc-MaxNumRetx"
    assert "RLC" in fields["failure_cause_description"]


def test_parse_failure_cause_t310():
    entry = _entry("RRCConnectionReestablishmentRequest reestablishmentCause=t310-Expiry")
    fields = parse_rrc_fields(entry)
    assert fields["failure_cause"] == "t310-Expiry"
    assert "T310" in fields["failure_cause_description"]


def test_parse_handover_target_pci():
    entry = _entry("RRCConnectionReconfiguration HandoverCommand targetPhysCellId=43")
    fields = parse_rrc_fields(entry)
    assert fields["handover_target_pci"] == 43


def test_is_handover_true_by_message():
    entry = _entry("RRCConnectionReconfiguration handover", decoded={"handover_target_pci": 43})
    assert is_handover(entry) is True


def test_is_handover_true_by_decoded_pci():
    entry = _entry("rrcreconfiguration", decoded={"handover_target_pci": 55})
    assert is_handover(entry) is True


def test_is_handover_false():
    entry = _entry("RRCConnectionSetup PCI=1")
    assert is_handover(entry) is False


def test_is_rlf_by_cause():
    entry = _entry("RRCConnectionReestablishmentRequest", decoded={"failure_cause": "t310-Expiry"})
    assert is_rlf(entry) is True


def test_is_rlf_by_rlc_retx():
    entry = _entry("RRCConnectionReestablishmentRequest", decoded={"failure_cause": "rlc-MaxNumRetx"})
    assert is_rlf(entry) is True


def test_is_rlf_by_reestablishment_message():
    entry = _entry("RRCConnectionReestablishment PCI=42")
    assert is_rlf(entry) is True


def test_is_rlf_false_for_normal_setup():
    entry = _entry("RRCConnectionSetup PCI=1")
    assert is_rlf(entry) is False


def test_enrich_entry_rrc_adds_fields():
    entry = _entry("MeasurementReport PCI=7 RSRP=-80 RSRQ=-9 SINR=12")
    enrich_entry(entry)
    assert entry.decoded.get("pci") == 7
    assert entry.decoded.get("rsrp") == pytest.approx(-80.0)
    assert entry.decoded.get("rsrq") == pytest.approx(-9.0)


def test_enrich_entry_non_rrc_skipped():
    entry = _entry("Attach Request RSRP=-80", layer="NAS")
    enrich_entry(entry)
    assert "rsrp" not in entry.decoded
