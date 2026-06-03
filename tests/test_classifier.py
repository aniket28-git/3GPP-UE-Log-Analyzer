import pytest
from datetime import datetime
from core.log_entry import LogEntry
from core.analysis.classifier import classify


def _entry(layer: str, msg_type: str, decoded: dict | None = None) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 10, 0, 0),
        layer=layer,
        direction="DL",
        message_type=msg_type,
        decoded=decoded or {},
    )


def test_classify_attach_success():
    event = classify(_entry("NAS", "Attach Accept"))
    assert event is not None
    assert event.event_type == "Attach Success"
    assert event.severity == "INFO"


def test_classify_attach_failure():
    entry = _entry("NAS", "Attach Reject", decoded={"cause_code": 11, "cause_description": "PLMN not allowed"})
    event = classify(entry)
    assert event is not None
    assert event.event_type == "Attach Failure"
    assert event.severity == "ERROR"
    assert "PLMN" in event.description


def test_classify_authentication_failure():
    event = classify(_entry("NAS", "Authentication Failure"))
    assert event is not None
    assert event.event_type == "Authentication Failure"
    assert event.severity == "ERROR"


def test_classify_pdu_session_success():
    event = classify(_entry("NAS", "PDU Session Establishment Accept"))
    assert event is not None
    assert event.event_type == "PDU Session Success"
    assert event.severity == "INFO"


def test_classify_rrc_setup_success():
    event = classify(_entry("RRC", "rrcConnectionSetupComplete"))
    assert event is not None
    assert event.event_type == "RRC Setup Success"


def test_classify_handover_complete():
    event = classify(_entry("RRC", "rrcConnectionReconfigurationComplete"))
    assert event is not None
    assert event.event_type == "Handover Complete"


def test_classify_rrc_release():
    event = classify(_entry("RRC", "rrcRelease"))
    assert event is not None
    assert event.event_type == "RRC Release"


def test_classify_reestablishment_warning():
    event = classify(_entry("RRC", "rrcReestablishmentComplete"))
    assert event is not None
    assert event.event_type == "RRC Reestablishment"
    assert event.severity == "WARNING"


def test_classify_unknown_returns_none():
    event = classify(_entry("PHY", "SomePhyMessage"))
    assert event is None


def test_classify_includes_apn_in_description():
    entry = _entry("NAS", "PDN Connectivity Accept", decoded={"apn": "internet"})
    event = classify(entry)
    assert event is not None
    assert "internet" in event.description


def test_classify_event_timestamp_matches_entry():
    entry = _entry("NAS", "Attach Accept")
    event = classify(entry)
    assert event is not None
    assert event.timestamp == entry.timestamp
