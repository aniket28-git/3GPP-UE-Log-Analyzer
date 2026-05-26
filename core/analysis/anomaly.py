from __future__ import annotations
from collections import deque
from datetime import datetime, timedelta
from typing import Iterator, Sequence

from core.log_entry import AnalysisEvent


def detect_anomalies(events: Sequence[AnalysisEvent]) -> list[AnalysisEvent]:
    """Run all anomaly rules over a sorted event list and return new anomaly events."""
    sorted_events = sorted(events, key=lambda e: e.timestamp)
    anomalies: list[AnalysisEvent] = []

    anomalies.extend(_repeated_attach_failures(sorted_events))
    anomalies.extend(_authentication_loop(sorted_events))
    anomalies.extend(_ping_pong_handover(sorted_events))
    anomalies.extend(_rlf_cluster(sorted_events))
    anomalies.extend(_t3410_expiry(sorted_events))
    anomalies.extend(_signaling_storm(sorted_events))
    anomalies.extend(_short_lived_bearer(sorted_events))

    return anomalies


def _window_events(
    events: Sequence[AnalysisEvent],
    event_types: set[str],
    window_seconds: int,
) -> Iterator[list[AnalysisEvent]]:
    """Sliding window — yield groups of matching events within the time window."""
    buf: deque[AnalysisEvent] = deque()
    for ev in events:
        if ev.event_type not in event_types:
            continue
        buf.append(ev)
        cutoff = ev.timestamp - timedelta(seconds=window_seconds)
        while buf and buf[0].timestamp < cutoff:
            buf.popleft()
        yield list(buf)


def _repeated_attach_failures(events: Sequence[AnalysisEvent]) -> list[AnalysisEvent]:
    anomalies: list[AnalysisEvent] = []
    for group in _window_events(events, {"Attach Failure", "Registration Failure"}, 300):
        if len(group) >= 3:
            causes = {e.cause_code for e in group if e.cause_code}
            anomalies.append(AnalysisEvent(
                timestamp=group[-1].timestamp,
                event_type="Repeated Attach Failures",
                severity="ERROR",
                description=(
                    f"{len(group)} attach/registration failures in 5 minutes. "
                    f"Cause codes: {sorted(causes)}"
                ),
            ))
            break
    return anomalies


def _authentication_loop(events: Sequence[AnalysisEvent]) -> list[AnalysisEvent]:
    anomalies: list[AnalysisEvent] = []
    for group in _window_events(
        events, {"Authentication Failure", "Authentication Success"}, 120
    ):
        failures = [e for e in group if e.event_type == "Authentication Failure"]
        if len(failures) >= 3:
            anomalies.append(AnalysisEvent(
                timestamp=group[-1].timestamp,
                event_type="Authentication Loop",
                severity="ERROR",
                description=f"{len(failures)} authentication failures in 2 minutes",
            ))
            break
    return anomalies


def _ping_pong_handover(events: Sequence[AnalysisEvent]) -> list[AnalysisEvent]:
    anomalies: list[AnalysisEvent] = []
    ho_events = [e for e in events if e.event_type == "Handover Complete"]
    pcis: deque[tuple[datetime, int | None]] = deque()

    for ev in ho_events:
        pci = ev.entry.decoded.get("handover_target_pci") if ev.entry else None
        cutoff = ev.timestamp - timedelta(seconds=120)
        while pcis and pcis[0][0] < cutoff:
            pcis.popleft()
        pcis.append((ev.timestamp, pci))

        recent_pcis = [p for _, p in pcis if p is not None]
        if len(recent_pcis) >= 3:
            unique = set(recent_pcis[-3:])
            if len(unique) <= 2:
                anomalies.append(AnalysisEvent(
                    timestamp=ev.timestamp,
                    event_type="Ping-Pong Handover",
                    severity="WARNING",
                    description=(
                        f"Repeated handovers between PCIs {sorted(unique)} "
                        f"({len(recent_pcis[-3:])} HOs in 2 minutes)"
                    ),
                ))
                pcis.clear()

    return anomalies


def _rlf_cluster(events: Sequence[AnalysisEvent]) -> list[AnalysisEvent]:
    anomalies: list[AnalysisEvent] = []
    for group in _window_events(events, {"RLF", "Radio Link Failure"}, 300):
        if len(group) >= 2:
            anomalies.append(AnalysisEvent(
                timestamp=group[-1].timestamp,
                event_type="RLF Cluster",
                severity="ERROR",
                description=f"{len(group)} Radio Link Failures in 5 minutes",
            ))
            break
    return anomalies


def _t3410_expiry(events: Sequence[AnalysisEvent]) -> list[AnalysisEvent]:
    return [
        AnalysisEvent(
            timestamp=ev.timestamp,
            event_type="Timer Expiry",
            severity="ERROR",
            description="NAS timer expiry detected — attach procedure may be stuck",
            entry=ev.entry,
        )
        for ev in events
        if "timer" in ev.description.lower() and "expir" in ev.description.lower()
    ]


def _signaling_storm(events: Sequence[AnalysisEvent]) -> list[AnalysisEvent]:
    anomalies: list[AnalysisEvent] = []
    buf: deque[AnalysisEvent] = deque()
    for ev in events:
        buf.append(ev)
        cutoff = ev.timestamp - timedelta(seconds=10)
        while buf and buf[0].timestamp < cutoff:
            buf.popleft()
        if len(buf) > 50:
            anomalies.append(AnalysisEvent(
                timestamp=ev.timestamp,
                event_type="Signaling Storm",
                severity="WARNING",
                description=f"{len(buf)} signaling events in 10 seconds",
            ))
            buf.clear()
    return anomalies


def _short_lived_bearer(events: Sequence[AnalysisEvent]) -> list[AnalysisEvent]:
    anomalies: list[AnalysisEvent] = []
    pdn_activate: dict[str, datetime] = {}

    for ev in events:
        key = str(ev.entry.decoded.get("bearer_id", "")) if ev.entry else ""
        if "PDN Session Success" in ev.event_type or "PDU Session Success" in ev.event_type:
            pdn_activate[key] = ev.timestamp
        elif "Deactivate" in ev.event_type or "Release" in ev.event_type:
            if key in pdn_activate:
                dt = (ev.timestamp - pdn_activate.pop(key)).total_seconds()
                if dt < 2:
                    anomalies.append(AnalysisEvent(
                        timestamp=ev.timestamp,
                        event_type="Short-lived Bearer",
                        severity="WARNING",
                        description=f"Bearer activated and deactivated within {dt:.1f}s",
                        entry=ev.entry,
                    ))

    return anomalies
