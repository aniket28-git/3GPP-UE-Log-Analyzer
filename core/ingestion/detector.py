from __future__ import annotations
import os
import re
from pathlib import Path


PCAP_MAGIC = {b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4", b"\x0a\x0d\x0d\x0a"}

_HEX_DUMP_RE = re.compile(r"^[0-9A-Fa-f]{4}\s+([0-9A-Fa-f]{2}\s+){1,16}", re.M)
_AT_CMD_RE = re.compile(r"AT\+|AT\^|\+CME|\+CMS|\+CREG|\+CEREG", re.I)
_QXDM_EXTENSIONS = {".dlf", ".isf", ".hdf", ".qmdl", ".qmdl2"}
_TEXT_EXTENSIONS = {".txt", ".log", ".csv"}


def detect_format(path: str | Path) -> str:
    """Return one of: 'pcap', 'qxdm', 'hex', 'at', 'text'."""
    p = Path(path)
    ext = p.suffix.lower()

    if ext in (".pcap", ".pcapng"):
        return "pcap"
    if ext in _QXDM_EXTENSIONS:
        return "qxdm"

    try:
        with open(p, "rb") as f:
            header = f.read(4)
        if header[:4] in PCAP_MAGIC or header[:4] == b"\x0a\x0d\x0d\x0a":
            return "pcap"
    except OSError:
        pass

    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            sample = f.read(4096)
        if _AT_CMD_RE.search(sample):
            return "at"
        if _HEX_DUMP_RE.search(sample):
            return "hex"
    except OSError:
        pass

    return "text"
