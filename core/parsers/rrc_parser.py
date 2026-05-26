from __future__ import annotations
import re
from core.log_entry import LogEntry

# RRC failure causes — TS 36.331 §6.2.2
RRC_FAILURE_CAUSES: dict[str, str] = {
    "unspecified": "Unspecified failure",
    "t310-Expiry": "T310 timer expiry (serving cell out of sync)",
    "randomAccessProblem": "Random access failure",
    "rlc-MaxNumRetx": "RLC max retransmissions reached",
    "synchReconfigFailure-SCG": "SCG synchronisation reconfiguration failure",
    "scg-reconfigFailure": "SCG reconfiguration failure",
    "srb3-IntegrityFailure": "SRB3 integrity failure",
    "other": "Other unspecified cause",
}

# RRC connection release causes
RRC_RELEASE_CAUSES: dict[str, str] = {
    "other": "Other",
    "loadBalancingTAUrequired": "Load balancing TAU required",
    "other": "Other",
    "cs-FallbackHighPriority": "CS fallback high priority",
    "rrc-Suspend": "RRC suspend",
}

_PCI_RE = re.compile(r"[Pp][Cc][Ii][:\s=]+(\d+)")
_EARFCN_RE = re.compile(r"(?:EARFCN|ARFCN)[:\s=]+(\d+)")
_RSRP_RE = re.compile(r"RSRP[:\s=]+([-\d.]+)")
_RSRQ_RE = re.compile(r"RSRQ[:\s=]+([-\d.]+)")
_SINR_RE = re.compile(r"SINR[:\s=]+([-\d.]+)")
_MEAS_ID_RE = re.compile(r"measId[:\s=]+(\d+)")
_REPORT_AMOUNT_RE = re.compile(r"reportAmount[:\s=]+(\w+)")
_BAND_RE = re.compile(r"\bBand[:\s]+(\d+)\b")
_FREQ_RE = re.compile(r"\bFreq(?:uency)?[:\s=]+([\d.]+)\s*(MHz|GHz)?", re.I)
_FAILURE_CAUSE_RE = re.compile(
    r"failureCause[:\s=]+(\w[\w\-]*)|"
    r"reestablishmentCause[:\s=]+(\w[\w\-]*)",
    re.I,
)
_HO_TARGET_PCI_RE = re.compile(r"targetPhysCellId[:\s=]+(\d+)")


def parse_rrc_fields(entry: LogEntry) -> dict:
    """Extract key RRC fields from message text."""
    text = entry.message_type + " " + " ".join(str(v) for v in entry.decoded.values())
    fields: dict = {}

    m = _PCI_RE.search(text)
    if m:
        fields["pci"] = int(m.group(1))

    m = _EARFCN_RE.search(text)
    if m:
        fields["earfcn"] = int(m.group(1))

    m = _RSRP_RE.search(text)
    if m:
        fields["rsrp"] = float(m.group(1))

    m = _RSRQ_RE.search(text)
    if m:
        fields["rsrq"] = float(m.group(1))

    m = _SINR_RE.search(text)
    if m:
        fields["sinr"] = float(m.group(1))

    m = _MEAS_ID_RE.search(text)
    if m:
        fields["meas_id"] = int(m.group(1))

    m = _BAND_RE.search(text)
    if m:
        fields["band"] = int(m.group(1))

    m = _FAILURE_CAUSE_RE.search(text)
    if m:
        cause = m.group(1) or m.group(2)
        fields["failure_cause"] = cause
        fields["failure_cause_description"] = RRC_FAILURE_CAUSES.get(cause, cause)

    m = _HO_TARGET_PCI_RE.search(text)
    if m:
        fields["handover_target_pci"] = int(m.group(1))

    return fields


def is_handover(entry: LogEntry) -> bool:
    msg = entry.message_type.lower()
    return "reconfigur" in msg and (
        "handover" in msg
        or entry.decoded.get("handover_target_pci") is not None
    )


def is_rlf(entry: LogEntry) -> bool:
    msg = entry.message_type.lower()
    cause = entry.decoded.get("failure_cause", "")
    return (
        "reestablishment" in msg
        or cause in ("t310-Expiry", "rlc-MaxNumRetx", "randomAccessProblem")
    )


def enrich_entry(entry: LogEntry) -> LogEntry:
    if entry.layer == "RRC":
        entry.decoded.update(parse_rrc_fields(entry))
    return entry
