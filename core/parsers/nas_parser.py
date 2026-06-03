from __future__ import annotations
import re
from core.log_entry import LogEntry

# EMM Cause Codes — TS 24.301 §9.9.3.9
EMM_CAUSES: dict[int, str] = {
    2:  "IMSI unknown in HSS",
    3:  "Illegal UE",
    6:  "Illegal ME",
    7:  "EPS services not allowed",
    8:  "EPS and non-EPS services not allowed",
    9:  "UE identity cannot be derived by network",
    10: "Implicitly detached",
    11: "PLMN not allowed",
    12: "Tracking area not allowed",
    13: "Roaming not allowed in this tracking area",
    14: "EPS services not allowed in this PLMN",
    15: "No suitable cells in tracking area",
    16: "MSC temporarily not reachable",
    17: "Network failure",
    18: "CS domain not available",
    19: "ESM failure",
    20: "MAC failure",
    21: "Synch failure",
    22: "Congestion",
    23: "UE security capabilities mismatch",
    24: "Security mode rejected, unspecified",
    25: "Not authorized for this CSG",
    26: "Non-EPS authentication unacceptable",
    35: "Requested service option not authorized in this PLMN",
    39: "CS service temporarily not available",
    40: "No EPS bearer context activated",
    42: "Severe network failure",
}

# 5GMM Cause Codes — TS 24.501 §9.11.3.2
FIVEGMM_CAUSES: dict[int, str] = {
    3:  "Illegal UE",
    5:  "PEI not accepted",
    6:  "Illegal ME",
    7:  "5GS services not allowed",
    9:  "UE identity cannot be derived by network",
    10: "Implicitly deregistered",
    11: "PLMN not allowed",
    12: "Tracking area not allowed",
    13: "Roaming not allowed in this tracking area",
    15: "No suitable cells in tracking area",
    17: "N1 mode not allowed",
    20: "MAC failure",
    21: "Synch failure",
    22: "Congestion",
    23: "UE security capabilities mismatch",
    24: "Security mode rejected, unspecified",
    26: "Non-3GPP access to 5GCN not allowed",
    27: "Temporary not authorized for this SNPN",
    28: "Permanently not authorized for this SNPN",
    31: "Redirection to EPC required",
    43: "LADN not available",
    62: "No network slices available",
    65: "Maximum number of PDU sessions reached",
    67: "Insufficient resources for specific slice and DNN",
    69: "Insufficient resources for specific slice",
    71: "ngKSI already in use",
    72: "Non-3GPP access to 5GCN temporarily not allowed",
    73: "PLMN not allowed to operate at the present UE location",
    74: "UAS services not allowed",
    76: "IAB node not authorized",
    90: "Payload was not forwarded",
    91: "DNN not supported or not subscribed in the slice",
    92: "Insufficient user-plane resources for the PDU session",
}

# ESM / 5GSM cause codes
ESM_CAUSES: dict[int, str] = {
    8:  "Operator determined barring",
    26: "Insufficient resources",
    27: "Missing or unknown APN",
    28: "Unknown PDN type",
    29: "User authentication failed",
    30: "Request rejected by Serving GW or PDN GW",
    31: "Request rejected, unspecified",
    32: "Service option not supported",
    33: "Requested service option not subscribed",
    34: "Service option temporarily out of order",
    35: "PTI already in use",
    36: "Regular deactivation",
    37: "EPS QoS not accepted",
    38: "Network failure",
    39: "Reactivation requested",
    41: "Semantic error in the TFT operation",
    42: "Syntactical error in the TFT operation",
    43: "Invalid EPS bearer identity",
    44: "Semantic errors in packet filter(s)",
    45: "Syntactical errors in packet filter(s)",
    46: "Unused EPS bearer identity",
    47: "Last PDN disconnection not allowed",
    48: "PDN type IPv4 only allowed",
    49: "PDN type IPv6 only allowed",
    50: "Single address bearers only allowed",
    51: "ESM information not received",
    52: "PDN connection does not exist",
    53: "Multiple PDN connections for a given APN not allowed",
    54: "Collision with network initiated request",
    57: "Unsupported QCI value",
    58: "Bearer handling not supported",
    65: "Maximum number of EPS bearers reached",
    66: "Requested APN not supported in current RAT and PLMN combination",
    111: "Protocol error, unspecified",
}


def get_emm_cause(code: int) -> str:
    return EMM_CAUSES.get(code, f"Unknown cause #{code}")


def get_5gmm_cause(code: int) -> str:
    return FIVEGMM_CAUSES.get(code, f"Unknown cause #{code}")


def get_esm_cause(code: int) -> str:
    return ESM_CAUSES.get(code, f"Unknown cause #{code}")


# Regex patterns to extract key NAS fields from text logs
_IMSI_RE = re.compile(r"IMSI[:\s=]+(\d{15})")
_GUTI_RE = re.compile(r"GUTI[:\s=]+([0-9A-Fa-f-]+)")
_SUCI_RE = re.compile(r"SUCI[:\s=]+([0-9A-Fa-f]+)")
_APN_RE = re.compile(r"APN[:\s=]+([A-Za-z0-9.\-_]+)")
_DNN_RE = re.compile(r"DNN[:\s=]+([A-Za-z0-9.\-_]+)")
_BEARER_ID_RE = re.compile(r"EBI[:\s=]+(\d+)|Bearer\s+ID[:\s=]+(\d+)", re.I)
_CAUSE_RE = re.compile(r"[Cc]ause[:\s=#]+(\d+)")
_MCC_MNC_RE = re.compile(r"MCC[:\s=]+(\d{3}).*?MNC[:\s=]+(\d{2,3})")
_TAC_RE = re.compile(r"TAC[:\s=]+([0-9A-Fa-f]+)")
_PDN_TYPE_RE = re.compile(r"PDN\s+[Tt]ype[:\s=]+(IPv4v6|IPv4|IPv6|Non-IP)", re.I)
_SEC_ALG_RE = re.compile(
    r"(EEA\d|EIA\d|NIA\d|NEA\d|128-EEA\d|128-EIA\d)", re.I
)


def parse_nas_fields(entry: LogEntry) -> dict:
    """Extract key NAS information elements from decoded text in LogEntry."""
    text = " ".join([entry.message_type] + [str(v) for v in entry.decoded.values()])
    # Also check raw source if decoded is empty
    fields: dict = {}

    m = _IMSI_RE.search(text)
    if m:
        fields["imsi"] = m.group(1)

    m = _GUTI_RE.search(text)
    if m:
        fields["guti"] = m.group(1)

    m = _SUCI_RE.search(text)
    if m:
        fields["suci"] = m.group(1)

    m = _APN_RE.search(text)
    if m:
        fields["apn"] = m.group(1)

    m = _DNN_RE.search(text)
    if m:
        fields["dnn"] = m.group(1)

    m = _BEARER_ID_RE.search(text)
    if m:
        fields["bearer_id"] = int(m.group(1) or m.group(2))

    m = _CAUSE_RE.search(text)
    if m:
        code = int(m.group(1))
        fields["cause_code"] = code
        layer = entry.layer.upper()
        if "5G" in entry.message_type.upper() or "5GMM" in text.upper():
            fields["cause_description"] = get_5gmm_cause(code)
        else:
            fields["cause_description"] = get_emm_cause(code)

    m = _MCC_MNC_RE.search(text)
    if m:
        fields["mcc"] = m.group(1)
        fields["mnc"] = m.group(2)

    m = _TAC_RE.search(text)
    if m:
        fields["tac"] = m.group(1)

    m = _PDN_TYPE_RE.search(text)
    if m:
        fields["pdn_type"] = m.group(1)

    algs = _SEC_ALG_RE.findall(text)
    if algs:
        fields["security_algorithms"] = algs

    return fields


def enrich_entry(entry: LogEntry) -> LogEntry:
    """Enrich a LogEntry's decoded dict with parsed NAS fields."""
    if entry.layer in ("NAS", "UNKNOWN"):
        nas_fields = parse_nas_fields(entry)
        entry.decoded.update(nas_fields)
    return entry
