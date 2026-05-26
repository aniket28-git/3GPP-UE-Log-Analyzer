from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class LogEntry:
    timestamp: datetime
    layer: str                    # NAS, RRC, MAC, PHY
    direction: str                # UL, DL, INTERNAL
    message_type: str
    raw_bytes: bytes = b""
    decoded: dict = field(default_factory=dict)
    source_file: str = ""
    source_line: int = 0
    session_id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "layer": self.layer,
            "direction": self.direction,
            "message_type": self.message_type,
            "raw_hex": self.raw_bytes.hex() if self.raw_bytes else "",
            "decoded": self.decoded,
            "source_file": self.source_file,
            "source_line": self.source_line,
        }


@dataclass
class AnalysisEvent:
    timestamp: datetime
    event_type: str
    severity: str                 # INFO, WARNING, ERROR, CRITICAL
    description: str
    entry: Optional[LogEntry] = None
    cause_code: Optional[int] = None
    cause_description: str = ""

    SEVERITY_ORDER = {"INFO": 0, "WARNING": 1, "ERROR": 2, "CRITICAL": 3}

    def severity_level(self) -> int:
        return self.SEVERITY_ORDER.get(self.severity, 0)


@dataclass
class RadioMeasurement:
    timestamp: datetime
    pci: Optional[int] = None
    earfcn: Optional[int] = None
    rsrp: Optional[float] = None
    rsrq: Optional[float] = None
    sinr: Optional[float] = None
    cqi: Optional[int] = None
    mcs: Optional[int] = None
    bler: Optional[float] = None
    entry: Optional[LogEntry] = None
