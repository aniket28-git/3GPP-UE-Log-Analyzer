from __future__ import annotations
from pathlib import Path
from typing import Iterator

from core.log_entry import LogEntry
from core.ingestion.detector import detect_format
from core.ingestion.text_reader import read_text_log


def load_log(path: str | Path) -> Iterator[LogEntry]:
    """Auto-detect format and yield LogEntry objects."""
    fmt = detect_format(path)

    if fmt == "pcap":
        from core.ingestion.pcap_reader import read_pcap
        yield from read_pcap(path)
    elif fmt == "qxdm":
        raise NotImplementedError("QXDM binary format requires Qualcomm SDK. Load exported text instead.")
    elif fmt in ("text", "at", "hex"):
        yield from read_text_log(path)
    else:
        yield from read_text_log(path)
