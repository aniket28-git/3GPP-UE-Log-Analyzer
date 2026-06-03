"""
Seed ue_analyzer.db with realistic demo data from all fixture scenarios.

Usage:
    python seed_demo_data.py           # add missing scenarios (idempotent)
    python seed_demo_data.py --reset   # wipe DB and re-seed everything
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, func, text

from core.ingestion.loader import load_log
from core.ingestion.detector import detect_format
from core.parsers import nas_parser, rrc_parser, phy_parser
from core.analysis.classifier import classify
from core.analysis.anomaly import detect_anomalies
from core.analysis.kpi_engine import compute_kpis
from core.storage.repository import Repository
from core.storage.schema import Base, LogFile, LogEntryRow, EventRow, RadioMeasurementRow, KPIRow, DecodedField

FIXTURES = Path(__file__).parent / "tests" / "fixtures"
DB_PATH = "ue_analyzer.db"

SCENARIOS: list[tuple[str, str]] = [
    ("sample_nas_log.txt",                 "4G LTE — Successful Attach & Handover"),
    ("sample_failure_log.txt",             "4G LTE — Attach Reject & Auth Failure"),
    ("sample_5g_registration_success.txt", "5G NR — Full Registration Success"),
    ("sample_5g_registration_failure.txt", "5G NR — Registration Failure Cascade"),
    ("sample_handover_failure.txt",        "4G LTE — Handover Failure & RLF"),
    ("sample_rlf_recovery.txt",            "4G LTE — RLF with Successful Recovery"),
    ("sample_kpi_stress.txt",              "4G LTE — KPI Stress: Multi-HO & Re-attach"),
    ("sample_pdn_bearer_failure.txt",      "4G LTE — PDN / Bearer Setup Failures"),
    ("sample_crash_scenario.txt",          "4G LTE — UE Crash / Severe Degradation"),
]


def _reset_db() -> None:
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    engine.dispose()
    print("  Database wiped and schema recreated.\n")


def _seed(repo: Repository) -> None:
    session = repo._session
    already_loaded = {lf.path for lf in session.query(LogFile).all()}

    total_seeded = 0

    for filename, label in SCENARIOS:
        fixture_path = FIXTURES / filename
        if not fixture_path.exists():
            print(f"  [WARN] fixture not found: {filename}")
            continue

        path_str = str(fixture_path)
        if path_str in already_loaded:
            print(f"  [skip] {label}")
            continue

        print(f"  [seed] {label}")

        # ── Parse ──────────────────────────────────────────────────────────
        raw_entries = list(load_log(path_str))
        entries, events, measurements = [], [], []

        for e in raw_entries:
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
        events.sort(key=lambda ev: ev.timestamp)

        # ── Persist ────────────────────────────────────────────────────────
        fmt = detect_format(path_str)
        lf = repo.save_log_file(path_str, fmt)
        rows = repo.save_entries(entries, lf.id)
        entry_id_map = {id(e): r.id for e, r in zip(entries, rows)}
        repo.save_events(events, entry_id_map)
        repo.save_measurements(measurements, entry_id_map)

        kpis = compute_kpis(events, measurements).to_kpi_list()
        if kpis:
            repo.save_kpis(kpis)

        n_err = sum(1 for ev in events if ev.severity in ("ERROR", "CRITICAL"))
        print(
            f"         entries={len(entries):3d}  events={len(events):3d}"
            f"  errors={n_err:2d}  measurements={len(measurements):3d}"
            f"  kpis={len(kpis):2d}"
        )
        total_seeded += 1

    return total_seeded


def _print_summary(repo: Repository) -> None:
    session = repo._session
    tables = {
        "log_files":         LogFile,
        "log_entries":       LogEntryRow,
        "decoded_fields":    DecodedField,
        "events":            EventRow,
        "radio_measurements": RadioMeasurementRow,
        "kpis":              KPIRow,
    }
    width = max(len(k) for k in tables) + 2
    print("\n  Table summary:")
    print(f"  {'Table':<{width}}  Rows")
    print(f"  {'-'*width}  ----")
    for name, model in tables.items():
        count = session.query(func.count(model.id)).scalar()
        print(f"  {name:<{width}}  {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ue_analyzer.db with demo data")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all existing data and re-seed from scratch",
    )
    args = parser.parse_args()

    print("=" * 55)
    print("  3GPP UE Log Analyzer — Demo Data Seeder")
    print("=" * 55)

    if args.reset:
        print("\n  Resetting database...")
        _reset_db()

    print("\n  Seeding scenarios...")
    repo = Repository(DB_PATH)
    total = _seed(repo)

    if total == 0:
        print("\n  All scenarios already present. Run with --reset to reload.")
    else:
        print(f"\n  Done — {total} scenario(s) seeded.")

    _print_summary(repo)
    repo.close()
    print()


if __name__ == "__main__":
    main()
