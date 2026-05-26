import pytest
from pathlib import Path
from core.ingestion.text_reader import read_text_log

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_reads_sample_log():
    entries = list(read_text_log(FIXTURE_DIR / "sample_nas_log.txt"))
    assert len(entries) > 0


def test_attach_request_found():
    entries = list(read_text_log(FIXTURE_DIR / "sample_nas_log.txt"))
    msg_types = [e.message_type.lower() for e in entries]
    assert any("attach request" in m for m in msg_types)


def test_timestamps_parsed():
    entries = list(read_text_log(FIXTURE_DIR / "sample_nas_log.txt"))
    for entry in entries:
        assert entry.timestamp.year == 2024


def test_layers_detected():
    entries = list(read_text_log(FIXTURE_DIR / "sample_nas_log.txt"))
    layers = {e.layer for e in entries}
    assert "NAS" in layers or "RRC" in layers


def test_failure_log_has_rejects():
    entries = list(read_text_log(FIXTURE_DIR / "sample_failure_log.txt"))
    msg_types = [e.message_type.lower() for e in entries]
    assert any("attach reject" in m for m in msg_types)
