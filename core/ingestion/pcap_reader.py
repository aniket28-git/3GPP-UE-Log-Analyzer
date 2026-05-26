from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Iterator

from core.log_entry import LogEntry


def read_pcap(path: str | Path) -> Iterator[LogEntry]:
    """Yield LogEntry objects from a PCAP/PCAPNG file using scapy."""
    try:
        from scapy.all import PcapReader, raw  # type: ignore
        from scapy.layers.inet import IP, UDP  # type: ignore
    except ImportError:
        raise RuntimeError("scapy is required for PCAP support: pip install scapy")

    p = Path(path)
    with PcapReader(str(p)) as reader:
        for lineno, pkt in enumerate(reader, start=1):
            ts = datetime.fromtimestamp(float(pkt.time))
            raw_bytes = bytes(raw(pkt))

            # Try to identify NAS/RRC from common ports or payload heuristics
            layer = _guess_layer_from_packet(pkt)
            direction = _guess_direction(pkt)
            msg_type = _guess_nas_message_type(raw_bytes)

            yield LogEntry(
                timestamp=ts,
                layer=layer,
                direction=direction,
                message_type=msg_type,
                raw_bytes=raw_bytes,
                decoded={},
                source_file=str(p),
                source_line=lineno,
            )


def _guess_layer_from_packet(pkt) -> str:
    try:
        from scapy.layers.inet import UDP
        if pkt.haslayer(UDP):
            dport = pkt[UDP].dport
            sport = pkt[UDP].sport
            # GTPv1-U: port 2152
            if dport == 2152 or sport == 2152:
                return "GTP"
            # SCTP S1AP / NGAP common ports
            if dport in (36412, 38412) or sport in (36412, 38412):
                return "NAS"
    except Exception:
        pass
    return "UNKNOWN"


def _guess_direction(pkt) -> str:
    try:
        from scapy.layers.inet import IP
        if pkt.haslayer(IP):
            src = pkt[IP].src
            # Rough heuristic: UE typically has 192.168.x.x or 10.x.x.x
            if src.startswith("192.168.") or src.startswith("10."):
                return "UL"
            return "DL"
    except Exception:
        pass
    return "UNKNOWN"


# NAS discriminators from TS 24.301 Table 9.2 and TS 24.501 Table 9.7
_NAS_MSG_MAP: dict[int, str] = {
    0x41: "Attach Request",
    0x42: "Attach Accept",
    0x44: "Attach Reject",
    0x45: "Attach Complete",
    0x49: "Detach Request",
    0x4A: "Detach Accept",
    0x48: "Tracking Area Update Request",
    0x49: "Tracking Area Update Accept",
    0x4B: "Tracking Area Update Reject",
    0x4C: "Tracking Area Update Complete",
    0x52: "Authentication Request",
    0x53: "Authentication Response",
    0x54: "Authentication Reject",
    0x5C: "Authentication Failure",
    0x55: "Identity Request",
    0x56: "Identity Response",
    0x5D: "Security Mode Command",
    0x5E: "Security Mode Complete",
    0x5F: "Security Mode Reject",
    0x41: "Registration Request",       # 5GMM
    0x42: "Registration Accept",
    0x44: "Registration Reject",
    0x45: "Registration Complete",
    0x46: "Deregistration Request",
    0x47: "Deregistration Accept",
}


def _guess_nas_message_type(payload: bytes) -> str:
    if len(payload) < 3:
        return "Unknown"
    msg_byte = payload[2] if len(payload) > 2 else payload[-1]
    return _NAS_MSG_MAP.get(msg_byte, "Unknown")
