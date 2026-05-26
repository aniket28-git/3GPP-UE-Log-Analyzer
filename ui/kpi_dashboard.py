from __future__ import annotations
from typing import Sequence

from PyQt6.QtWidgets import (
    QGridLayout, QGroupBox, QLabel, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QFrame

from core.log_entry import AnalysisEvent, RadioMeasurement
from core.analysis.kpi_engine import compute_kpis, KPIResult

SEVERITY_COLORS = {
    "INFO":     "#4CAF50",
    "WARNING":  "#FFC107",
    "ERROR":    "#F44336",
    "CRITICAL": "#9C27B0",
}


class KPICard(QFrame):
    def __init__(self, name: str, value: str, unit: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { background: #F9F9F9; border: 1px solid #DDD; border-radius: 6px; }"
        )
        layout = QVBoxLayout(self)

        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setWordWrap(True)
        small_font = QFont()
        small_font.setPointSize(8)
        name_lbl.setFont(small_font)
        name_lbl.setStyleSheet("color: #666;")

        val_lbl = QLabel(f"{value}")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        big_font = QFont()
        big_font.setPointSize(16)
        big_font.setBold(True)
        val_lbl.setFont(big_font)

        unit_lbl = QLabel(unit)
        unit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        unit_lbl.setStyleSheet("color: #888;")
        unit_lbl.setFont(small_font)

        layout.addWidget(name_lbl)
        layout.addWidget(val_lbl)
        layout.addWidget(unit_lbl)


class SeverityBar(QWidget):
    """Simple horizontal bar chart of event severities."""

    def __init__(self, events: Sequence[AnalysisEvent], parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Event Severity Distribution"))

        counts = {"INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
        for ev in events:
            if ev.severity in counts:
                counts[ev.severity] += 1

        total = sum(counts.values()) or 1
        for sev, count in counts.items():
            row = QWidget()
            row_layout = QGridLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)

            lbl = QLabel(f"{sev:<12} {count:>5}")
            lbl.setFixedWidth(140)
            lbl.setFont(QFont("Monospace", 9))

            bar = QFrame()
            bar.setFixedHeight(14)
            pct = count / total
            bar.setFixedWidth(max(2, int(pct * 200)))
            color = SEVERITY_COLORS.get(sev, "#888")
            bar.setStyleSheet(f"background-color: {color}; border-radius: 3px;")

            row_layout.addWidget(lbl, 0, 0)
            row_layout.addWidget(bar, 0, 1)
            layout.addWidget(row)


class CauseCodeTable(QWidget):
    def __init__(self, events: Sequence[AnalysisEvent], parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Top Failure Cause Codes"))

        cause_counts: dict[str, int] = {}
        for ev in events:
            if ev.cause_code is not None and ev.severity in ("ERROR", "CRITICAL"):
                key = f"#{ev.cause_code} — {ev.cause_description}"
                cause_counts[key] = cause_counts.get(key, 0) + 1

        top = sorted(cause_counts.items(), key=lambda x: -x[1])[:8]
        for cause, count in top:
            lbl = QLabel(f"  {count:>3}×  {cause}")
            lbl.setFont(QFont("Monospace", 8))
            lbl.setStyleSheet("color: #C62828;")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

        if not top:
            layout.addWidget(QLabel("No failures detected"))


class KPIDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll)

        self._placeholder = QLabel("Load a log file to see KPIs")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_layout.addWidget(self._placeholder)

    def load(
        self,
        events: Sequence[AnalysisEvent],
        measurements: Sequence[RadioMeasurement],
    ):
        # Clear old content
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not events and not measurements:
            self._content_layout.addWidget(QLabel("No data"))
            return

        summary = compute_kpis(events, measurements)
        kpis = summary.to_kpi_list()

        # KPI cards grid
        cards_group = QGroupBox("Key Performance Indicators")
        grid = QGridLayout(cards_group)
        for i, kpi in enumerate(kpis):
            val = f"{kpi.value:.1f}" if kpi.value != int(kpi.value) else str(int(kpi.value))
            card = KPICard(kpi.name, val, kpi.unit)
            card.setFixedSize(160, 90)
            grid.addWidget(card, i // 4, i % 4)
        self._content_layout.addWidget(cards_group)

        # Severity distribution
        sev_group = QGroupBox("Events")
        sev_layout = QVBoxLayout(sev_group)
        sev_layout.addWidget(SeverityBar(events))
        self._content_layout.addWidget(sev_group)

        # Cause codes
        cause_group = QGroupBox("Failure Analysis")
        cause_layout = QVBoxLayout(cause_group)
        cause_layout.addWidget(CauseCodeTable(events))
        self._content_layout.addWidget(cause_group)

        # Radio measurements summary
        if measurements:
            radio_group = QGroupBox("Radio Measurements Summary")
            radio_grid = QGridLayout(radio_group)
            radio_items = []
            if summary.rsrp_values:
                radio_items.append(("Avg RSRP", f"{summary.avg_rsrp():.1f}", "dBm"))
                radio_items.append(("Min RSRP", f"{min(summary.rsrp_values):.1f}", "dBm"))
                radio_items.append(("Max RSRP", f"{max(summary.rsrp_values):.1f}", "dBm"))
            if summary.rsrq_values:
                radio_items.append(("Avg RSRQ", f"{summary.avg_rsrq():.1f}", "dB"))
            if summary.sinr_values:
                radio_items.append(("Avg SINR", f"{summary.avg_sinr():.1f}", "dB"))
            for i, (name, val, unit) in enumerate(radio_items):
                radio_grid.addWidget(KPICard(name, val, unit), i // 4, i % 4)
            self._content_layout.addWidget(radio_group)

        self._content_layout.addStretch()
