from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from typing import Iterator

from core.log_entry import LogEntry

# Common timestamp patterns found in modem text logs
_TS_PATTERNS = [
    # 2024-01-15 10:23:45.123
    re.compile(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[.,]\d+)"),
    # 01/15/2024 10:23:45.123
    re.compile(r"(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}[.,]\d+)"),
    # 10:23:45.123 (time only)
    re.compile(r"(\d{2}:\d{2}:\d{2}[.,]\d+)"),
]

_TS_FORMATS = [
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S,%f",
    "%m/%d/%Y %H:%M:%S.%f",
    "%H:%M:%S.%f",
    "%H:%M:%S,%f",
]

# Layer and direction detection
_LAYER_RE = re.compile(
    r"\b(NAS|RRC|PDCP|RLC|MAC|PHY|EMM|ESM|5GMM|5GSM|MM|SM)\b", re.I
)
_DIR_RE = re.compile(r"\b(UL|DL|Uplink|Downlink|Send|Recv|Tx|Rx)\b", re.I)

_DIR_MAP = {
    "ul": "UL", "uplink": "UL", "send": "UL", "tx": "UL",
    "dl": "DL", "downlink": "DL", "recv": "DL", "rx": "DL",
}

# Known NAS/RRC message names
_NAS_MESSAGES = {
    "attach request", "attach accept", "attach reject", "attach complete",
    "detach request", "detach accept",
    "authentication request", "authentication response", "authentication failure",
    "authentication result",
    "security mode command", "security mode complete", "security mode reject",
    "tau request", "tau accept", "tau reject", "tau complete",
    "tracking area update request", "tracking area update accept",
    "tracking area update reject", "tracking area update complete",
    "service request", "service reject", "service accept",
    "pdn connectivity request", "pdn connectivity accept", "pdn connectivity reject",
    "pdu session establishment request", "pdu session establishment accept",
    "pdu session establishment reject",
    "pdu session modification request", "pdu session modification accept",
    "pdu session release request", "pdu session release accept",
    "registration request", "registration accept", "registration reject",
    "registration complete",
    "deregistration request", "deregistration accept",
    "emm information", "emm status",
    "activate default eps bearer context request",
    "activate default eps bearer context accept",
    "activate dedicated eps bearer context request",
    "deactivate eps bearer context request",
    "deactivate eps bearer context accept",
    "configuration update command", "configuration update complete",
    "identity request", "identity response",
    "gmm attach request", "gmm attach accept", "gmm attach reject",
}

_RRC_MESSAGES = {
    "rrcconnectionrequest", "rrcconnectionsetup", "rrcconnectionsetupcomplete",
    "rrcconnectionreject", "rrcconnectionreconfiguration",
    "rrcconnectionreconfigurationcomplete", "rrcconnectionrelease",
    "rrcconnectionreestablishmentrequest", "rrcconnectionreestablishment",
    "rrcconnectionreestablishmentcomplete", "rrcconnectionreestablishmentreject",
    "measurementreport", "uecontentionresolution", "uecapabilityenquiry",
    "uecapabilityinformation", "systeminformation", "masterinformationblock",
    "rrcsetup", "rrcsetuprequest", "rrcsetupcomplete",
    "rrcreconfiguration", "rrcconfigurationcomplete", "rrcrelease",
    "rrcreestablishmentrequest", "rrcreestablishment", "rrcreestablishmentcomplete",
    "rrcsuspend", "rrcresume", "rrcresumerequest",
}


def _parse_timestamp(line: str) -> datetime | None:
    for pattern, fmt in zip(_TS_PATTERNS, _TS_FORMATS):
        m = pattern.search(line)
        if m:
            ts_str = m.group(1).replace(",", ".")
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
    # Try remaining formats on last match
    for pattern in _TS_PATTERNS[len(_TS_FORMATS):]:
        m = pattern.search(line)
        if m:
            ts_str = m.group(1).replace(",", ".")
            for fmt in _TS_FORMATS:
                try:
                    return datetime.strptime(ts_str, fmt)
                except ValueError:
                    continue
    return None


def _detect_layer(line: str) -> str:
    m = _LAYER_RE.search(line)
    if not m:
        return "UNKNOWN"
    layer = m.group(1).upper()
    # Normalize EMM/ESM → NAS, 5GMM/5GSM → NAS
    if layer in ("EMM", "ESM", "5GMM", "5GSM", "MM", "SM"):
        return "NAS"
    return layer


def _detect_direction(line: str) -> str:
    m = _DIR_RE.search(line)
    if not m:
        return "UNKNOWN"
    return _DIR_MAP.get(m.group(1).lower(), "UNKNOWN")


def _detect_message_type(line: str) -> str:
    lower = line.lower()
    for msg in _NAS_MESSAGES:
        if msg in lower:
            return msg.title()
    # Normalise RRC (strip spaces for matching)
    compact = re.sub(r"\s+", "", lower)
    for msg in _RRC_MESSAGES:
        if msg in compact:
            return msg
    return "Unknown"


def read_text_log(path: str | Path) -> Iterator[LogEntry]:
    """Yield LogEntry objects from a plain-text modem log file."""
    p = Path(path)
    last_ts: datetime = datetime(2000, 1, 1)
    pending_lines: list[str] = []
    pending_start: int = 0

    def _flush(lines: list[str], lineno: int) -> LogEntry | None:
        if not lines:
            return None
        full = " ".join(lines)
        ts = _parse_timestamp(full) or last_ts
        layer = _detect_layer(full)
        direction = _detect_direction(full)
        msg_type = _detect_message_type(full)

        # Try to extract hex payload if present
        hex_match = re.search(r"([0-9A-Fa-f]{2}\s?){4,}", full)
        raw = bytes.fromhex(re.sub(r"\s", "", hex_match.group())) if hex_match else b""

        return LogEntry(
            timestamp=ts,
            layer=layer,
            direction=direction,
            message_type=msg_type,
            raw_bytes=raw,
            decoded={},
            source_file=str(p),
            source_line=lineno,
        )

    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        for lineno, raw_line in enumerate(f, start=1):
            line = raw_line.rstrip()
            if not line:
                entry = _flush(pending_lines, pending_start)
                if entry:
                    yield entry
                pending_lines = []
                continue

            ts = _parse_timestamp(line)
            if ts:
                entry = _flush(pending_lines, pending_start)
                if entry:
                    yield entry
                last_ts = ts
                pending_lines = [line]
                pending_start = lineno
            else:
                pending_lines.append(line)

    entry = _flush(pending_lines, pending_start)
    if entry:
        yield entry
