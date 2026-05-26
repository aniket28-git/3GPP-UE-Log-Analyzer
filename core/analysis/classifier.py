from __future__ import annotations
from datetime import datetime
from core.log_entry import LogEntry, AnalysisEvent

# Maps (layer, message_type_substring) → (event_type, severity)
_RULES: list[tuple[str, str, str, str]] = [
    # NAS success events
    ("NAS", "attach accept",          "Attach Success",          "INFO"),
    ("NAS", "attach complete",        "Attach Complete",         "INFO"),
    ("NAS", "registration accept",    "Registration Success",    "INFO"),
    ("NAS", "registration complete",  "Registration Complete",   "INFO"),
    ("NAS", "pdn connectivity accept","PDN Session Success",     "INFO"),
    ("NAS", "pdu session establishment accept", "PDU Session Success", "INFO"),
    ("NAS", "detach accept",          "Detach Success",          "INFO"),
    ("NAS", "deregistration accept",  "Deregistration Success",  "INFO"),
    ("NAS", "tau accept",             "TAU Success",             "INFO"),
    ("NAS", "tracking area update accept", "TAU Success",        "INFO"),
    ("NAS", "authentication response","Authentication Success",  "INFO"),
    ("NAS", "security mode complete", "Security Mode Success",   "INFO"),
    # NAS failure events
    ("NAS", "attach reject",          "Attach Failure",          "ERROR"),
    ("NAS", "registration reject",    "Registration Failure",    "ERROR"),
    ("NAS", "pdn connectivity reject","PDN Session Failure",     "ERROR"),
    ("NAS", "pdu session establishment reject", "PDU Session Failure", "ERROR"),
    ("NAS", "tau reject",             "TAU Failure",             "ERROR"),
    ("NAS", "tracking area update reject", "TAU Failure",        "ERROR"),
    ("NAS", "authentication failure", "Authentication Failure",  "ERROR"),
    ("NAS", "authentication reject",  "Authentication Reject",   "ERROR"),
    ("NAS", "security mode reject",   "Security Mode Failure",   "ERROR"),
    ("NAS", "service reject",         "Service Reject",          "WARNING"),
    # RRC success
    ("RRC", "rrcconnectionsetupcomplete",  "RRC Setup Success",      "INFO"),
    ("RRC", "rrcsetupcomplete",            "RRC Setup Success",      "INFO"),
    ("RRC", "rrcconnectionreconfigurationcomplete", "Handover Complete", "INFO"),
    ("RRC", "rrcconfigurationcomplete",    "RRC Reconfig Complete",  "INFO"),
    ("RRC", "rrcreestablishmentcomplete",  "RRC Reestablishment",    "WARNING"),
    # RRC failures
    ("RRC", "rrcconnectionreject",         "RRC Connection Reject",  "ERROR"),
    ("RRC", "rrcconnectionreestablishmentreject", "Reestablishment Reject", "ERROR"),
    ("RRC", "rrcrelease",                  "RRC Release",            "INFO"),
    ("RRC", "rrcconnectionrelease",        "RRC Release",            "INFO"),
]


def classify(entry: LogEntry) -> AnalysisEvent | None:
    """Return an AnalysisEvent if this entry matches a known event pattern."""
    layer = entry.layer.upper()
    msg = entry.message_type.lower()

    for rule_layer, pattern, event_type, severity in _RULES:
        if layer == rule_layer and pattern in msg:
            cause_code = entry.decoded.get("cause_code")
            cause_desc = entry.decoded.get("cause_description", "")
            desc = _build_description(event_type, entry, cause_code, cause_desc)
            return AnalysisEvent(
                timestamp=entry.timestamp,
                event_type=event_type,
                severity=severity,
                description=desc,
                entry=entry,
                cause_code=cause_code,
                cause_description=cause_desc,
            )
    return None


def _build_description(
    event_type: str,
    entry: LogEntry,
    cause_code: int | None,
    cause_desc: str,
) -> str:
    parts = [event_type]
    if cause_code is not None:
        parts.append(f"cause #{cause_code}: {cause_desc}")
    apn = entry.decoded.get("apn") or entry.decoded.get("dnn")
    if apn:
        parts.append(f"APN/DNN={apn}")
    return " — ".join(parts)
