from __future__ import annotations
from typing import Sequence

from PyQt6.QtWidgets import (
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QFrame

from core.log_entry import AnalysisEvent, RadioMeasurement
from core.analysis.kpi_engine import compute_kpis, KPIResult
from ui.theme import KPI_ACCENT, COL_PRIMARY, COL_BG_CARD, COL_BORDER, COL_MUTED

SEVERITY_COLORS = {
    "INFO":     "#2ed573",
    "WARNING":  "#ffa502",
    "ERROR":    "#ff4757",
    "CRITICAL": "#a55eea",
}


class KPICard(QFrame):
    def __init__(self, name: str, value: str, unit: str,
                 color: str = COL_PRIMARY, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COL_BG_CARD};
                border: 1px solid {COL_BORDER};
                border-left: 4px solid {color};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        name_lbl = QLabel(name.upper())
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(f"color: {COL_MUTED}; font-size: 7pt; font-weight: bold; letter-spacing: 1px; border: none;")

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"color: {color}; font-size: 20pt; font-weight: bold; border: none;")

        unit_lbl = QLabel(unit)
        unit_lbl.setStyleSheet(f"color: {COL_MUTED}; font-size: 8pt; border: none;")

        layout.addWidget(name_lbl)
        layout.addWidget(val_lbl)
        layout.addWidget(unit_lbl)


class SeverityBar(QWidget):
    """Horizontal bar chart of event severities."""

    def __init__(self, events: Sequence[AnalysisEvent], parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        counts = {"INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
        for ev in events:
            if ev.severity in counts:
                counts[ev.severity] += 1

        total = sum(counts.values()) or 1
        for sev, count in counts.items():
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            color = SEVERITY_COLORS.get(sev, "#888")

            # Severity label
            sev_lbl = QLabel(sev)
            sev_lbl.setFixedWidth(70)
            sev_lbl.setStyleSheet(f"color: {color}; font-size: 8pt; font-weight: bold; border: none;")

            # Count badge
            count_lbl = QLabel(str(count))
            count_lbl.setFixedWidth(40)
            count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            count_lbl.setStyleSheet(f"color: {color}; font-size: 9pt; font-weight: bold; border: none;")

            # Bar track + fill
            track = QFrame()
            track.setFixedHeight(8)
            track.setStyleSheet(f"background: #252840; border-radius: 4px; border: none;")

            fill = QFrame(track)
            fill.setFixedHeight(8)
            pct = count / total
            fill.setFixedWidth(max(4, int(pct * 180)))
            fill.setStyleSheet(f"background: {color}; border-radius: 4px; border: none;")

            row_layout.addWidget(sev_lbl)
            row_layout.addWidget(track, 1)
            row_layout.addWidget(count_lbl)
            layout.addWidget(row)


class CauseCodeTable(QWidget):
    def __init__(self, events: Sequence[AnalysisEvent], parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        cause_counts: dict[str, int] = {}
        for ev in events:
            if ev.cause_code is not None and ev.severity in ("ERROR", "CRITICAL"):
                key = f"#{ev.cause_code}  {ev.cause_description}"
                cause_counts[key] = cause_counts.get(key, 0) + 1

        top = sorted(cause_counts.items(), key=lambda x: -x[1])[:8]
        for cause, count in top:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            badge = QLabel(f" {count}× ")
            badge.setStyleSheet(
                "color: white; background: #ff4757; border-radius: 4px; "
                "font-size: 8pt; font-weight: bold; padding: 1px 4px; border: none;"
            )
            badge.setFixedWidth(36)
            cause_lbl = QLabel(cause)
            cause_lbl.setStyleSheet("color: #ff8085; font-size: 8pt; border: none;")
            cause_lbl.setWordWrap(True)
            row_layout.addWidget(badge)
            row_layout.addWidget(cause_lbl, 1)
            layout.addWidget(row)

        if not top:
            ok = QLabel("  No failures detected")
            ok.setStyleSheet("color: #2ed573; font-size: 9pt; border: none;")
            layout.addWidget(ok)


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
        grid.setSpacing(10)
        for i, kpi in enumerate(kpis):
            val = f"{kpi.value:.1f}" if kpi.value != int(kpi.value) else str(int(kpi.value))
            color = KPI_ACCENT.get(kpi.name, COL_PRIMARY)
            card = KPICard(kpi.name, val, kpi.unit, color)
            card.setFixedSize(175, 90)
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
            radio_grid.setSpacing(10)
            for i, (name, val, unit) in enumerate(radio_items):
                color = KPI_ACCENT.get(name, COL_PRIMARY)
                card = KPICard(name, val, unit, color)
                card.setFixedSize(175, 90)
                radio_grid.addWidget(card, i // 4, i % 4)
            self._content_layout.addWidget(radio_group)

        self._content_layout.addStretch()
