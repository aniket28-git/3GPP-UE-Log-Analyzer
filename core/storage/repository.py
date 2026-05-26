from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Sequence

from sqlalchemy.orm import Session

from core.log_entry import LogEntry, AnalysisEvent, RadioMeasurement
from core.storage.schema import (
    LogFile, LogEntryRow, DecodedField, EventRow, KPIRow, RadioMeasurementRow,
    create_db,
)
from core.analysis.kpi_engine import KPIResult


class Repository:
    def __init__(self, db_path: str = "ue_analyzer.db"):
        self._session: Session = create_db(db_path)

    # ── Ingestion ──────────────────────────────────────────────────────────

    def save_log_file(self, path: str, fmt: str) -> LogFile:
        lf = LogFile(path=path, format=fmt, loaded_at=datetime.now().isoformat())
        self._session.add(lf)
        self._session.flush()
        return lf

    def save_entries(self, entries: Sequence[LogEntry], file_id: int) -> list[LogEntryRow]:
        rows: list[LogEntryRow] = []
        for e in entries:
            row = LogEntryRow(
                file_id=file_id,
                timestamp=e.timestamp.isoformat(),
                layer=e.layer,
                direction=e.direction,
                message_type=e.message_type,
                raw_hex=e.raw_bytes.hex() if e.raw_bytes else "",
                source_line=e.source_line,
            )
            self._session.add(row)
            self._session.flush()
            for k, v in (e.decoded or {}).items():
                self._session.add(DecodedField(
                    entry_id=row.id,
                    field_name=str(k),
                    field_value=str(v),
                ))
            rows.append(row)
        self._session.commit()
        return rows

    def save_events(self, events: Sequence[AnalysisEvent], entry_id_map: dict[int, int]) -> None:
        for ev in events:
            eid = entry_id_map.get(id(ev.entry)) if ev.entry else None
            self._session.add(EventRow(
                timestamp=ev.timestamp.isoformat(),
                event_type=ev.event_type,
                severity=ev.severity,
                description=ev.description,
                cause_code=ev.cause_code,
                cause_description=ev.cause_description,
                entry_id=eid,
            ))
        self._session.commit()

    def save_measurements(
        self,
        measurements: Sequence[RadioMeasurement],
        entry_id_map: dict[int, int],
    ) -> None:
        for m in measurements:
            eid = entry_id_map.get(id(m.entry)) if m.entry else None
            self._session.add(RadioMeasurementRow(
                entry_id=eid,
                timestamp=m.timestamp.isoformat(),
                pci=m.pci,
                earfcn=m.earfcn,
                rsrp=m.rsrp,
                rsrq=m.rsrq,
                sinr=m.sinr,
                cqi=m.cqi,
                mcs=m.mcs,
                bler=m.bler,
            ))
        self._session.commit()

    def save_kpis(self, kpis: Sequence[KPIResult], window_sec: int = 0) -> None:
        ts = datetime.now().isoformat()
        for k in kpis:
            self._session.add(KPIRow(
                timestamp=ts,
                window_sec=window_sec,
                kpi_name=k.name,
                value=k.value,
                unit=k.unit,
            ))
        self._session.commit()

    # ── Queries ────────────────────────────────────────────────────────────

    def query_entries(
        self,
        layer: str | None = None,
        direction: str | None = None,
        message_type: str | None = None,
        severity: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        search: str | None = None,
        limit: int = 500,
    ) -> list[LogEntryRow]:
        q = self._session.query(LogEntryRow)
        if layer:
            q = q.filter(LogEntryRow.layer == layer)
        if direction:
            q = q.filter(LogEntryRow.direction == direction)
        if message_type:
            q = q.filter(LogEntryRow.message_type.ilike(f"%{message_type}%"))
        if start_time:
            q = q.filter(LogEntryRow.timestamp >= start_time)
        if end_time:
            q = q.filter(LogEntryRow.timestamp <= end_time)
        if search:
            q = q.join(DecodedField).filter(DecodedField.field_value.ilike(f"%{search}%"))
        return q.order_by(LogEntryRow.timestamp).limit(limit).all()

    def query_events(
        self,
        severity: str | None = None,
        event_type: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 500,
    ) -> list[EventRow]:
        q = self._session.query(EventRow)
        if severity:
            q = q.filter(EventRow.severity == severity)
        if event_type:
            q = q.filter(EventRow.event_type.ilike(f"%{event_type}%"))
        if start_time:
            q = q.filter(EventRow.timestamp >= start_time)
        if end_time:
            q = q.filter(EventRow.timestamp <= end_time)
        return q.order_by(EventRow.timestamp).limit(limit).all()

    def query_measurements(
        self,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[RadioMeasurementRow]:
        q = self._session.query(RadioMeasurementRow)
        if start_time:
            q = q.filter(RadioMeasurementRow.timestamp >= start_time)
        if end_time:
            q = q.filter(RadioMeasurementRow.timestamp <= end_time)
        return q.order_by(RadioMeasurementRow.timestamp).all()

    def close(self) -> None:
        self._session.close()
