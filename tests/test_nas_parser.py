import pytest
from datetime import datetime
from core.log_entry import LogEntry
from core.parsers.nas_parser import (
    parse_nas_fields, get_emm_cause, get_5gmm_cause, get_esm_cause, enrich_entry
)


def _entry(msg_type: str, decoded: dict | None = None) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 10, 0, 0),
        layer="NAS",
        direction="UL",
        message_type=msg_type,
        decoded=decoded or {},
    )


def test_emm_cause_known():
    assert "PLMN not allowed" in get_emm_cause(11)


def test_emm_cause_unknown():
    result = get_emm_cause(255)
    assert "#255" in result


def test_5gmm_cause_known():
    assert "Illegal UE" in get_5gmm_cause(3)


def test_esm_cause_known():
    assert "Insufficient resources" in get_esm_cause(26)


def test_parse_imsi():
    entry = _entry("Attach Request IMSI=001010123456789")
    fields = parse_nas_fields(entry)
    assert fields.get("imsi") == "001010123456789"


def test_parse_apn():
    entry = _entry("PDN Connectivity Request APN=internet.carrier.com")
    fields = parse_nas_fields(entry)
    assert fields.get("apn") == "internet.carrier.com"


def test_parse_cause_code():
    entry = _entry("Attach Reject Cause #11")
    fields = parse_nas_fields(entry)
    assert fields.get("cause_code") == 11
    assert "PLMN" in fields.get("cause_description", "")


def test_parse_mcc_mnc():
    entry = _entry("Attach Accept MCC=001 MNC=01 TAC=ABCD")
    fields = parse_nas_fields(entry)
    assert fields.get("mcc") == "001"
    assert fields.get("mnc") == "01"
    assert fields.get("tac") == "ABCD"


def test_enrich_entry_adds_fields():
    entry = _entry("Attach Request IMSI=001010123456789 APN=test MCC=310 MNC=410")
    enrich_entry(entry)
    assert "imsi" in entry.decoded
    assert "apn" in entry.decoded


def test_security_algorithms():
    entry = _entry("Security Mode Command EEA2 EIA2")
    fields = parse_nas_fields(entry)
    assert "EEA2" in fields.get("security_algorithms", [])
