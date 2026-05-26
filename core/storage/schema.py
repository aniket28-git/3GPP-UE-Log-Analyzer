from __future__ import annotations
from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, Text, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session


class Base(DeclarativeBase):
    pass


class LogFile(Base):
    __tablename__ = "log_files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String, nullable=False)
    format = Column(String)
    loaded_at = Column(String)
    entries = relationship("LogEntryRow", back_populates="file", cascade="all, delete-orphan")


class LogEntryRow(Base):
    __tablename__ = "log_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("log_files.id"))
    timestamp = Column(String, nullable=False)
    layer = Column(String)
    direction = Column(String)
    message_type = Column(String)
    raw_hex = Column(Text)
    source_line = Column(Integer)
    file = relationship("LogFile", back_populates="entries")
    fields = relationship("DecodedField", back_populates="entry", cascade="all, delete-orphan")
    events = relationship("EventRow", back_populates="entry")
    measurement = relationship("RadioMeasurementRow", back_populates="entry", uselist=False)


class DecodedField(Base):
    __tablename__ = "decoded_fields"
    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(Integer, ForeignKey("log_entries.id"))
    field_name = Column(String)
    field_value = Column(Text)
    entry = relationship("LogEntryRow", back_populates="fields")


class EventRow(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String)
    event_type = Column(String)
    severity = Column(String)
    description = Column(Text)
    cause_code = Column(Integer)
    cause_description = Column(Text)
    entry_id = Column(Integer, ForeignKey("log_entries.id"), nullable=True)
    entry = relationship("LogEntryRow", back_populates="events")


class KPIRow(Base):
    __tablename__ = "kpis"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String)
    window_sec = Column(Integer)
    kpi_name = Column(String)
    value = Column(Float)
    unit = Column(String)


class RadioMeasurementRow(Base):
    __tablename__ = "radio_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(Integer, ForeignKey("log_entries.id"), nullable=True)
    timestamp = Column(String)
    pci = Column(Integer)
    earfcn = Column(Integer)
    rsrp = Column(Float)
    rsrq = Column(Float)
    sinr = Column(Float)
    cqi = Column(Integer)
    mcs = Column(Integer)
    bler = Column(Float)
    entry = relationship("LogEntryRow", back_populates="measurement")


def create_db(db_path: str = "ue_analyzer.db") -> Session:
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return Session(engine)
