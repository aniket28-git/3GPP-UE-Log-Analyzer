from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Sequence

from core.log_entry import AnalysisEvent, RadioMeasurement


@dataclass
class KPIResult:
    name: str
    value: float
    unit: str
    window_label: str = "full"


@dataclass
class KPISummary:
    attach_requests: int = 0
    attach_successes: int = 0
    attach_failures: int = 0
    attach_setup_times_ms: list[float] = field(default_factory=list)

    registration_requests: int = 0
    registration_successes: int = 0
    registration_failures: int = 0

    handover_commands: int = 0
    handover_successes: int = 0
    handover_failures: int = 0

    rlf_count: int = 0
    reestablishment_count: int = 0

    pdn_setup_times_ms: list[float] = field(default_factory=list)

    rsrp_values: list[float] = field(default_factory=list)
    rsrq_values: list[float] = field(default_factory=list)
    sinr_values: list[float] = field(default_factory=list)

    def attach_success_rate(self) -> float | None:
        if self.attach_requests == 0:
            return None
        return self.attach_successes / self.attach_requests * 100

    def handover_success_rate(self) -> float | None:
        if self.handover_commands == 0:
            return None
        return self.handover_successes / self.handover_commands * 100

    def avg_attach_setup_ms(self) -> float | None:
        if not self.attach_setup_times_ms:
            return None
        return sum(self.attach_setup_times_ms) / len(self.attach_setup_times_ms)

    def avg_rsrp(self) -> float | None:
        if not self.rsrp_values:
            return None
        return sum(self.rsrp_values) / len(self.rsrp_values)

    def avg_rsrq(self) -> float | None:
        if not self.rsrq_values:
            return None
        return sum(self.rsrq_values) / len(self.rsrq_values)

    def avg_sinr(self) -> float | None:
        if not self.sinr_values:
            return None
        return sum(self.sinr_values) / len(self.sinr_values)

    def to_kpi_list(self, window_label: str = "full") -> list[KPIResult]:
        results: list[KPIResult] = []

        def _add(name: str, value: float | None, unit: str) -> None:
            if value is not None:
                results.append(KPIResult(name, round(value, 2), unit, window_label))

        _add("Attach Success Rate", self.attach_success_rate(), "%")
        _add("Avg Attach Setup Time", self.avg_attach_setup_ms(), "ms")
        _add("Handover Success Rate", self.handover_success_rate(), "%")
        _add("RLF Count", float(self.rlf_count), "count")
        _add("Reestablishment Count", float(self.reestablishment_count), "count")
        _add("Avg RSRP", self.avg_rsrp(), "dBm")
        _add("Avg RSRQ", self.avg_rsrq(), "dB")
        _add("Avg SINR", self.avg_sinr(), "dB")
        if self.pdn_setup_times_ms:
            _add(
                "Avg PDN/PDU Setup Time",
                sum(self.pdn_setup_times_ms) / len(self.pdn_setup_times_ms),
                "ms",
            )
        return results


def compute_kpis(
    events: Sequence[AnalysisEvent],
    measurements: Sequence[RadioMeasurement],
    window_seconds: int | None = None,
) -> KPISummary:
    """Compute KPIs from classified events and radio measurements."""
    summary = KPISummary()

    # Optionally restrict to a time window
    if window_seconds and events:
        cutoff = events[-1].timestamp - timedelta(seconds=window_seconds)
        events = [e for e in events if e.timestamp >= cutoff]
    if window_seconds and measurements:
        cutoff = measurements[-1].timestamp - timedelta(seconds=window_seconds)
        measurements = [m for m in measurements if m.timestamp >= cutoff]

    # Track pending request timestamps for setup-time calculation
    pending_attach: datetime | None = None
    pending_pdn: datetime | None = None
    last_ho_command: datetime | None = None

    for ev in sorted(events, key=lambda e: e.timestamp):
        et = ev.event_type

        if et == "Attach Request" or "Attach" in et and "Request" in et:
            summary.attach_requests += 1
            pending_attach = ev.timestamp
        elif et == "Attach Success":
            summary.attach_successes += 1
            if pending_attach:
                dt = (ev.timestamp - pending_attach).total_seconds() * 1000
                if 0 < dt < 60_000:
                    summary.attach_setup_times_ms.append(dt)
                pending_attach = None
        elif et == "Attach Failure":
            summary.attach_failures += 1
            pending_attach = None

        elif "Registration" in et and "Request" in et:
            summary.registration_requests += 1
        elif et == "Registration Success":
            summary.registration_successes += 1
        elif et == "Registration Failure":
            summary.registration_failures += 1

        elif "Handover" in et and "Command" in et:
            summary.handover_commands += 1
            last_ho_command = ev.timestamp
        elif et == "Handover Complete":
            summary.handover_successes += 1
            last_ho_command = None
        elif "Handover" in et and "Fail" in et:
            summary.handover_failures += 1
            last_ho_command = None

        elif et in ("RLF", "Radio Link Failure"):
            summary.rlf_count += 1
        elif et == "RRC Reestablishment":
            summary.reestablishment_count += 1

        elif "PDN" in et and "Request" in et or "PDU" in et and "Request" in et:
            pending_pdn = ev.timestamp
        elif ("PDN Session Success" in et or "PDU Session Success" in et):
            if pending_pdn:
                dt = (ev.timestamp - pending_pdn).total_seconds() * 1000
                if 0 < dt < 60_000:
                    summary.pdn_setup_times_ms.append(dt)
                pending_pdn = None

    for meas in measurements:
        if meas.rsrp is not None:
            summary.rsrp_values.append(meas.rsrp)
        if meas.rsrq is not None:
            summary.rsrq_values.append(meas.rsrq)
        if meas.sinr is not None:
            summary.sinr_values.append(meas.sinr)

    return summary
