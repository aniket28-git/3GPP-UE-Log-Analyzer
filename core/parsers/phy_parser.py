from __future__ import annotations
import re
from core.log_entry import LogEntry
from core.log_entry import RadioMeasurement

_RSRP_RE = re.compile(r"RSRP[:\s=]+([-\d.]+)")
_RSRQ_RE = re.compile(r"RSRQ[:\s=]+([-\d.]+)")
_SINR_RE = re.compile(r"SINR[:\s=]+([-\d.]+)")
_CQI_RE = re.compile(r"\bCQI[:\s=]+(\d+)")
_MCS_RE = re.compile(r"\bMCS[:\s=]+(\d+)")
_BLER_RE = re.compile(r"\bBLER[:\s=]+([\d.]+)")
_PCI_RE = re.compile(r"\bPCI[:\s=]+(\d+)")
_EARFCN_RE = re.compile(r"(?:EARFCN|ARFCN)[:\s=]+(\d+)")
_TA_RE = re.compile(r"(?:Timing\s+Advance|TA)[:\s=]+(\d+)")


def parse_phy_measurement(entry: LogEntry) -> RadioMeasurement | None:
    """Extract radio measurements from a PHY-layer LogEntry."""
    text = " ".join([entry.message_type] + [str(v) for v in entry.decoded.values()])

    meas = RadioMeasurement(timestamp=entry.timestamp, entry=entry)
    found_any = False

    def _f(pattern: re.Pattern, text: str):
        nonlocal found_any
        m = pattern.search(text)
        if m:
            found_any = True
            return float(m.group(1))
        return None

    def _i(pattern: re.Pattern, text: str):
        nonlocal found_any
        m = pattern.search(text)
        if m:
            found_any = True
            return int(m.group(1))
        return None

    meas.rsrp = _f(_RSRP_RE, text)
    meas.rsrq = _f(_RSRQ_RE, text)
    meas.sinr = _f(_SINR_RE, text)
    meas.bler = _f(_BLER_RE, text)
    meas.cqi = _i(_CQI_RE, text)
    meas.mcs = _i(_MCS_RE, text)
    meas.pci = _i(_PCI_RE, text)
    meas.earfcn = _i(_EARFCN_RE, text)

    return meas if found_any else None
