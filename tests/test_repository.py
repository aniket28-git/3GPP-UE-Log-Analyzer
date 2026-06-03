import pytest
from datetime import datetime, timedelta
from pathlib import Path

from core.log_entry import LogEntry, AnalysisEvent, RadioMeasurement
from core.storage.repository import Repository
from core.analysis.kpi_engine import KPIResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_repo(tmp_path: Path) -> Repository:
    return Repository(str(tmp_path / "test.db"))


def _entry(msg: str, layer: str = "NAS", direction: str = "UL",
           offset_sec: int = 0, decoded: dict | None = None) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 10, 0, 0) + timedelta(seconds=offset_sec),
        layer=layer,
        direction=direction,
        message_type=msg,
        decoded=decoded or {},
    )


def _event(event_type: str, severity: str = "INFO",
           entry: LogEntry | None = None, offset_sec: int = 0,
           cause_code: int | None = None) -> AnalysisEvent:
    return AnalysisEvent(
        timestamp=datetime(2024, 1, 15, 10, 0, 0) + timedelta(seconds=offset_sec),
        event_type=event_type,
        severity=severity,
        description=f"{event_type} occurred",
        entry=entry,
        cause_code=cause_code,
    )


def _meas(rsrp: float, rsrq: float, sinr: float,
          entry: LogEntry | None = None, offset_sec: int = 0) -> RadioMeasurement:
    return RadioMeasurement(
        timestamp=datetime(2024, 1, 15, 10, 0, 0) + timedelta(seconds=offset_sec),
        rsrp=rsrp, rsrq=rsrq, sinr=sinr,
        pci=42, earfcn=1850,
        entry=entry,
    )


# ── save_log_file ──────────────────────────────────────────────────────────────

def test_save_log_file(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    assert lf.id is not None
    assert lf.path == "/logs/test.txt"
    assert lf.format == "text"
    repo.close()


def test_save_log_file_returns_unique_ids(tmp_path):
    repo = _make_repo(tmp_path)
    lf1 = repo.save_log_file("/logs/a.txt", "text")
    lf2 = repo.save_log_file("/logs/b.txt", "text")
    assert lf1.id != lf2.id
    repo.close()


# ── save_entries ───────────────────────────────────────────────────────────────

def test_save_entries_basic(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    entries = [
        _entry("Attach Request IMSI=001010123456789", "NAS", "UL"),
        _entry("Attach Accept GUTI=001010-0-0001", "NAS", "DL", offset_sec=1),
        _entry("RRCConnectionSetup PCI=42", "RRC", "DL", offset_sec=2),
    ]
    rows = repo.save_entries(entries, lf.id)
    assert len(rows) == 3
    assert rows[0].layer == "NAS"
    assert rows[1].direction == "DL"
    assert rows[2].message_type == "RRCConnectionSetup PCI=42"
    repo.close()


def test_save_entries_with_decoded_fields(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    entry = _entry("Attach Request", decoded={"imsi": "001010123456789", "apn": "internet"})
    rows = repo.save_entries([entry], lf.id)
    field_names = {f.field_name for f in rows[0].fields}
    assert "imsi" in field_names
    assert "apn" in field_names
    repo.close()


def test_save_entries_empty_list(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    rows = repo.save_entries([], lf.id)
    assert rows == []
    repo.close()


def test_save_entries_row_ids_are_unique(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    rows = repo.save_entries([_entry(f"Msg {i}") for i in range(5)], lf.id)
    ids = [r.id for r in rows]
    assert len(ids) == len(set(ids))
    repo.close()


# ── save_events ────────────────────────────────────────────────────────────────

def test_save_events_linked_to_entries(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    e1 = _entry("Attach Request", offset_sec=0)
    e2 = _entry("Attach Accept", offset_sec=1)
    rows = repo.save_entries([e1, e2], lf.id)
    entry_id_map = {id(e1): rows[0].id, id(e2): rows[1].id}

    ev1 = _event("Attach Request", entry=e1, offset_sec=0)
    ev2 = _event("Attach Success", entry=e2, offset_sec=1)
    repo.save_events([ev1, ev2], entry_id_map)

    db_events = repo.query_events()
    assert len(db_events) == 2
    assert db_events[0].event_type == "Attach Request"
    assert db_events[0].entry_id == rows[0].id
    assert db_events[1].entry_id == rows[1].id
    repo.close()


def test_save_events_no_entry(tmp_path):
    """Anomaly events with entry=None must save without error."""
    repo = _make_repo(tmp_path)
    ev = _event("Anomaly Detected", severity="WARNING", entry=None)
    repo.save_events([ev], {})
    db_events = repo.query_events()
    assert len(db_events) == 1
    assert db_events[0].entry_id is None
    repo.close()


def test_save_events_entry_not_in_map(tmp_path):
    """Event whose entry is absent from entry_id_map saves with entry_id=None."""
    repo = _make_repo(tmp_path)
    e = _entry("Attach Request")
    ev = _event("Attach Request", entry=e)
    repo.save_events([ev], {})          # deliberately empty map
    db_events = repo.query_events()
    assert db_events[0].entry_id is None
    repo.close()


def test_save_events_empty_list(tmp_path):
    repo = _make_repo(tmp_path)
    repo.save_events([], {})            # must not raise
    assert repo.query_events() == []
    repo.close()


def test_save_events_with_cause_code(tmp_path):
    repo = _make_repo(tmp_path)
    ev = _event("Attach Failure", severity="ERROR", cause_code=11)
    ev.cause_description = "PLMN not allowed"
    repo.save_events([ev], {})
    db = repo.query_events()[0]
    assert db.cause_code == 11
    assert "PLMN" in db.cause_description
    repo.close()


def test_save_events_severity_stored(tmp_path):
    repo = _make_repo(tmp_path)
    repo.save_events([
        _event("OK",       severity="INFO"),
        _event("Degraded", severity="WARNING"),
        _event("Failed",   severity="ERROR"),
        _event("Crashed",  severity="CRITICAL"),
    ], {})
    severities = {e.severity for e in repo.query_events()}
    assert severities == {"INFO", "WARNING", "ERROR", "CRITICAL"}
    repo.close()


# ── save_measurements ──────────────────────────────────────────────────────────

def test_save_measurements_linked(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    e = _entry("MeasurementReport PCI=42 RSRP=-85", "RRC", "DL")
    rows = repo.save_entries([e], lf.id)
    m = _meas(-85.0, -10.0, 12.0, entry=e)
    repo.save_measurements([m], {id(e): rows[0].id})

    db_meas = repo.query_measurements()
    assert len(db_meas) == 1
    assert db_meas[0].rsrp == pytest.approx(-85.0)
    assert db_meas[0].rsrq == pytest.approx(-10.0)
    assert db_meas[0].sinr == pytest.approx(12.0)
    assert db_meas[0].entry_id == rows[0].id
    repo.close()


def test_save_measurements_no_linked_entry(tmp_path):
    repo = _make_repo(tmp_path)
    m = _meas(-90.0, -12.0, 8.0, entry=None)
    repo.save_measurements([m], {})
    db_meas = repo.query_measurements()
    assert len(db_meas) == 1
    assert db_meas[0].entry_id is None
    repo.close()


def test_save_measurements_empty_list(tmp_path):
    repo = _make_repo(tmp_path)
    repo.save_measurements([], {})
    assert repo.query_measurements() == []
    repo.close()


def test_save_measurements_pci_earfcn_stored(tmp_path):
    repo = _make_repo(tmp_path)
    m = _meas(-80.0, -10.0, 14.0)
    m.pci = 77
    m.earfcn = 3050
    repo.save_measurements([m], {})
    db = repo.query_measurements()[0]
    assert db.pci == 77
    assert db.earfcn == 3050
    repo.close()


# ── save_kpis ─────────────────────────────────────────────────────────────────

def test_save_kpis(tmp_path):
    from core.storage.schema import KPIRow
    repo = _make_repo(tmp_path)
    kpis = [
        KPIResult("Attach Success Rate", 100.0, "%"),
        KPIResult("Avg RSRP", -82.5, "dBm"),
        KPIResult("RLF Count", 2.0, "count"),
    ]
    repo.save_kpis(kpis, window_sec=60)
    rows = repo._session.query(KPIRow).all()
    assert len(rows) == 3
    names = {r.kpi_name for r in rows}
    assert {"Attach Success Rate", "Avg RSRP", "RLF Count"} == names
    assert all(r.window_sec == 60 for r in rows)
    repo.close()


def test_save_kpis_empty_list(tmp_path):
    repo = _make_repo(tmp_path)
    repo.save_kpis([])                  # must not raise
    repo.close()


def test_save_kpis_values_stored_correctly(tmp_path):
    from core.storage.schema import KPIRow
    repo = _make_repo(tmp_path)
    repo.save_kpis([KPIResult("Handover Success Rate", 75.0, "%")])
    row = repo._session.query(KPIRow).first()
    assert row.value == pytest.approx(75.0)
    assert row.unit == "%"
    repo.close()


# ── query_entries filters ─────────────────────────────────────────────────────

def test_query_entries_by_layer(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    repo.save_entries([
        _entry("Attach Request",       "NAS", "UL"),
        _entry("RRCConnectionSetup",   "RRC", "DL"),
        _entry("MeasurementReport",    "PHY", "DL"),
    ], lf.id)
    assert len(repo.query_entries(layer="NAS")) == 1
    assert len(repo.query_entries(layer="RRC")) == 1
    assert len(repo.query_entries(layer="PHY")) == 1
    repo.close()


def test_query_entries_by_direction(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    repo.save_entries([
        _entry("Attach Request",  "NAS", "UL"),
        _entry("Attach Accept",   "NAS", "DL"),
        _entry("Attach Complete", "NAS", "UL"),
    ], lf.id)
    assert len(repo.query_entries(direction="UL")) == 2
    assert len(repo.query_entries(direction="DL")) == 1
    repo.close()


def test_query_entries_message_type_case_insensitive(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    repo.save_entries([
        _entry("Attach Request IMSI=001010123456789"),
        _entry("Attach Accept GUTI=001010-0-0001"),
        _entry("Tracking Area Update Request"),
    ], lf.id)
    results = repo.query_entries(message_type="attach")
    assert len(results) == 2
    repo.close()


def test_query_entries_by_time_range(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    repo.save_entries([
        _entry("Msg A", offset_sec=0),
        _entry("Msg B", offset_sec=10),
        _entry("Msg C", offset_sec=20),
        _entry("Msg D", offset_sec=30),
    ], lf.id)
    results = repo.query_entries(
        start_time="2024-01-15T10:00:05",
        end_time="2024-01-15T10:00:25",
    )
    assert len(results) == 2
    assert results[0].message_type == "Msg B"
    assert results[1].message_type == "Msg C"
    repo.close()


def test_query_entries_combined_filters(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    repo.save_entries([
        _entry("Attach Request",  "NAS", "UL", offset_sec=0),
        _entry("Attach Accept",   "NAS", "DL", offset_sec=1),
        _entry("RRCSetup",        "RRC", "DL", offset_sec=2),
    ], lf.id)
    results = repo.query_entries(layer="NAS", direction="UL")
    assert len(results) == 1
    assert results[0].message_type == "Attach Request"
    repo.close()


def test_query_entries_no_match_returns_empty(tmp_path):
    repo = _make_repo(tmp_path)
    lf = repo.save_log_file("/logs/test.txt", "text")
    repo.save_entries([_entry("Attach Request")], lf.id)
    results = repo.query_entries(layer="MAC")
    assert results == []
    repo.close()


# ── query_events filters ───────────────────────────────────────────────────────

def test_query_events_by_severity(tmp_path):
    repo = _make_repo(tmp_path)
    repo.save_events([
        _event("Attach Success",  severity="INFO"),
        _event("Handover Failure", severity="ERROR"),
        _event("RLF",              severity="ERROR"),
        _event("Signal Degraded",  severity="WARNING"),
    ], {})
    assert len(repo.query_events(severity="ERROR"))   == 2
    assert len(repo.query_events(severity="WARNING")) == 1
    assert len(repo.query_events(severity="INFO"))    == 1
    repo.close()


def test_query_events_by_type_case_insensitive(tmp_path):
    repo = _make_repo(tmp_path)
    repo.save_events([
        _event("Attach Request"),
        _event("Attach Success"),
        _event("Handover Command"),
        _event("Handover Complete"),
    ], {})
    assert len(repo.query_events(event_type="Handover")) == 2
    assert len(repo.query_events(event_type="attach"))   == 2
    repo.close()


def test_query_events_by_time_range(tmp_path):
    repo = _make_repo(tmp_path)
    repo.save_events([
        _event("Ev A", offset_sec=0),
        _event("Ev B", offset_sec=30),
        _event("Ev C", offset_sec=60),
    ], {})
    results = repo.query_events(
        start_time="2024-01-15T10:00:15",
        end_time="2024-01-15T10:01:05",
    )
    assert len(results) == 2
    assert results[0].event_type == "Ev B"
    repo.close()


# ── query_measurements filters ─────────────────────────────────────────────────

def test_query_measurements_by_time_range(tmp_path):
    repo = _make_repo(tmp_path)
    repo.save_measurements([
        _meas(-80.0, -10.0, 12.0, offset_sec=0),
        _meas(-85.0, -11.0, 10.0, offset_sec=60),
        _meas(-90.0, -13.0,  7.0, offset_sec=120),
    ], {})
    results = repo.query_measurements(
        start_time="2024-01-15T10:00:30",
        end_time="2024-01-15T10:02:30",
    )
    assert len(results) == 2
    assert results[0].rsrp == pytest.approx(-85.0)
    repo.close()


def test_query_measurements_no_filter_returns_all(tmp_path):
    repo = _make_repo(tmp_path)
    repo.save_measurements([_meas(-80.0, -10.0, 12.0, offset_sec=i) for i in range(5)], {})
    assert len(repo.query_measurements()) == 5
    repo.close()


# ── Multi-file isolation ───────────────────────────────────────────────────────

def test_multiple_files_isolated(tmp_path):
    from core.storage.schema import LogEntryRow
    repo = _make_repo(tmp_path)
    lf1 = repo.save_log_file("/logs/session1.txt", "text")
    lf2 = repo.save_log_file("/logs/session2.txt", "text")
    repo.save_entries([_entry("Attach Request")], lf1.id)
    repo.save_entries([_entry("Registration Request"), _entry("Registration Accept")], lf2.id)

    f1 = repo._session.query(LogEntryRow).filter_by(file_id=lf1.id).all()
    f2 = repo._session.query(LogEntryRow).filter_by(file_id=lf2.id).all()
    assert len(f1) == 1
    assert len(f2) == 2
    repo.close()


def test_duplicate_path_guard_prevents_double_save(tmp_path):
    """Simulates the path-guard in _on_load_finished: same path saved only once."""
    repo = _make_repo(tmp_path)
    path = "/logs/session.txt"
    loaded_files: list[str] = []

    def _guarded_save(entries):
        if path not in loaded_files:
            lf = repo.save_log_file(path, "text")
            repo.save_entries(entries, lf.id)
            loaded_files.append(path)

    entries = [_entry("Attach Request"), _entry("Attach Accept")]
    _guarded_save(entries)
    _guarded_save(entries)              # second call must be a no-op

    all_entries = repo.query_entries()
    assert len(all_entries) == 2        # not 4
    repo.close()


# ── Full pipeline from fixture files ──────────────────────────────────────────

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str, tmp_path: Path):
    """Run the full parse → classify → save pipeline on a fixture file."""
    from core.ingestion.loader import load_log
    from core.ingestion.detector import detect_format
    from core.parsers import nas_parser, rrc_parser, phy_parser
    from core.analysis.classifier import classify
    from core.analysis.anomaly import detect_anomalies
    from core.analysis.kpi_engine import compute_kpis

    path = str(FIXTURES / name)
    raw = list(load_log(path))
    entries, events, measurements = [], [], []
    for e in raw:
        nas_parser.enrich_entry(e)
        rrc_parser.enrich_entry(e)
        entries.append(e)
        ev = classify(e)
        if ev:
            events.append(ev)
        m = phy_parser.parse_phy_measurement(e)
        if m:
            measurements.append(m)
    events.extend(detect_anomalies(events))

    repo = Repository(str(tmp_path / f"{name}.db"))
    lf = repo.save_log_file(path, detect_format(path))
    rows = repo.save_entries(entries, lf.id)
    entry_id_map = {id(e): r.id for e, r in zip(entries, rows)}
    repo.save_events(events, entry_id_map)
    repo.save_measurements(measurements, entry_id_map)
    kpis = compute_kpis(events, measurements).to_kpi_list()
    if kpis:
        repo.save_kpis(kpis)
    return repo, entries, events, measurements


def test_pipeline_nas_success_fixture(tmp_path):
    repo, entries, events, measurements = _load_fixture("sample_nas_log.txt", tmp_path)
    assert len(repo.query_entries()) == len(entries)
    assert len(repo.query_entries(layer="NAS")) > 0
    assert len(repo.query_entries(message_type="Attach")) > 0
    repo.close()


def test_pipeline_failure_fixture_has_error_events(tmp_path):
    repo, entries, events, measurements = _load_fixture("sample_failure_log.txt", tmp_path)
    errors = repo.query_events(severity="ERROR")
    assert len(errors) > 0, "Failure log must produce at least one ERROR event"
    repo.close()


def test_pipeline_5g_registration_success(tmp_path):
    repo, entries, events, measurements = _load_fixture("sample_5g_registration_success.txt", tmp_path)
    assert len(repo.query_entries()) == len(entries)
    assert len(repo.query_measurements()) == len(measurements)
    repo.close()


def test_pipeline_handover_failure_has_failure_events(tmp_path):
    repo, entries, events, measurements = _load_fixture("sample_handover_failure.txt", tmp_path)
    event_types = {e.event_type for e in repo.query_events()}
    assert any(
        "Reestablishment" in t or "RLF" in t or "Failure" in t or "Reject" in t
        for t in event_types
    ), f"Expected failure/RLF events, got: {event_types}"
    repo.close()


def test_pipeline_rlf_recovery_measurements_span_good_to_bad(tmp_path):
    repo, entries, events, measurements = _load_fixture("sample_rlf_recovery.txt", tmp_path)
    meas_rows = repo.query_measurements()
    assert len(meas_rows) > 0
    rsrp_values = [m.rsrp for m in meas_rows if m.rsrp is not None]
    assert min(rsrp_values) < -95, "Should include very poor RSRP during RLF"
    assert max(rsrp_values) > -80, "Should include good RSRP before/after RLF"
    repo.close()


def test_pipeline_kpi_stress_produces_kpis(tmp_path):
    from core.storage.schema import KPIRow
    repo, entries, events, measurements = _load_fixture("sample_kpi_stress.txt", tmp_path)
    kpi_rows = repo._session.query(KPIRow).all()
    assert len(kpi_rows) > 0
    kpi_names = {k.kpi_name for k in kpi_rows}
    assert "Attach Success Rate" in kpi_names
    repo.close()


def test_pipeline_crash_scenario_has_errors(tmp_path):
    repo, entries, events, measurements = _load_fixture("sample_crash_scenario.txt", tmp_path)
    assert len(repo.query_events(severity="ERROR")) >= 1
    assert len(repo.query_events(event_type="Attach")) > 0
    repo.close()


def test_pipeline_pdn_failure_has_dl_nas_entries(tmp_path):
    repo, entries, events, measurements = _load_fixture("sample_pdn_bearer_failure.txt", tmp_path)
    assert len(repo.query_entries()) == len(entries)
    nas_dl = repo.query_entries(layer="NAS", direction="DL")
    assert len(nas_dl) > 0
    repo.close()


def test_pipeline_5g_registration_failure_has_errors(tmp_path):
    repo, entries, events, measurements = _load_fixture("sample_5g_registration_failure.txt", tmp_path)
    assert len(repo.query_events(severity="ERROR")) >= 1
    assert len(repo.query_measurements()) > 0
    repo.close()


def test_entry_id_map_no_dangling_references(tmp_path):
    """Every event that has an entry_id must point to an existing log_entries row."""
    repo, entries, events, measurements = _load_fixture("sample_nas_log.txt", tmp_path)
    valid_ids = {row.id for row in repo.query_entries()}
    for ev in repo.query_events():
        if ev.entry_id is not None:
            assert ev.entry_id in valid_ids, (
                f"Dangling entry_id {ev.entry_id} in event '{ev.event_type}'"
            )
    repo.close()


def test_measurement_entry_ids_are_valid(tmp_path):
    """Every measurement that has an entry_id must point to an existing log_entries row."""
    repo, entries, events, measurements = _load_fixture("sample_kpi_stress.txt", tmp_path)
    valid_ids = {row.id for row in repo.query_entries()}
    for m in repo.query_measurements():
        if m.entry_id is not None:
            assert m.entry_id in valid_ids, (
                f"Dangling entry_id {m.entry_id} in measurement at {m.timestamp}"
            )
    repo.close()
