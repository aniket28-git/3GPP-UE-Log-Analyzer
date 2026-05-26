from __future__ import annotations
from PyQt6.QtWidgets import (
    QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt

from core.log_entry import AnalysisEvent

SEVERITY_BG = {
    "INFO":     "#E8F5E9",
    "WARNING":  "#FFF8E1",
    "ERROR":    "#FFEBEE",
    "CRITICAL": "#F3E5F5",
}


class DetailPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self._header = QLabel("Select an event in the timeline")
        self._header.setWordWrap(True)
        bold = QFont()
        bold.setBold(True)
        self._header.setFont(bold)
        layout.addWidget(self._header)

        self._desc = QLabel("")
        self._desc.setWordWrap(True)
        layout.addWidget(self._desc)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Field", "Value"])
        self._tree.setColumnWidth(0, 220)
        self._tree.setAlternatingRowColors(True)
        layout.addWidget(self._tree)

    def show_event(self, event: AnalysisEvent):
        sev = event.severity
        bg = SEVERITY_BG.get(sev, "#FFFFFF")
        self._header.setText(f"[{sev}] {event.event_type}")
        self._header.setStyleSheet(f"background-color: {bg}; padding: 4px; border-radius: 4px;")
        self._desc.setText(event.description)

        self._tree.clear()

        # Event metadata
        meta = QTreeWidgetItem(["Event"])
        meta.setExpanded(True)
        for field, val in [
            ("Timestamp", event.timestamp.isoformat()),
            ("Event Type", event.event_type),
            ("Severity", sev),
            ("Description", event.description),
        ]:
            child = QTreeWidgetItem([field, str(val)])
            meta.addChild(child)

        if event.cause_code is not None:
            cause_item = QTreeWidgetItem(["Cause Code", str(event.cause_code)])
            cause_desc = QTreeWidgetItem(["Cause Description", event.cause_description])
            cause_item.setForeground(1, QColor("#D32F2F"))
            meta.addChild(cause_item)
            meta.addChild(cause_desc)

        self._tree.addTopLevelItem(meta)

        # Source message fields
        if event.entry:
            entry = event.entry
            msg_item = QTreeWidgetItem(["Message"])
            msg_item.setExpanded(True)
            for field, val in [
                ("Layer", entry.layer),
                ("Direction", entry.direction),
                ("Message Type", entry.message_type),
                ("Source File", entry.source_file),
                ("Source Line", str(entry.source_line)),
                ("Raw Hex", entry.raw_bytes.hex()[:64] + ("…" if len(entry.raw_bytes) > 32 else "")),
            ]:
                msg_item.addChild(QTreeWidgetItem([field, str(val)]))

            if entry.decoded:
                dec_item = QTreeWidgetItem(["Decoded Fields"])
                dec_item.setExpanded(True)
                for k, v in entry.decoded.items():
                    dec_item.addChild(QTreeWidgetItem([str(k), str(v)]))
                msg_item.addChild(dec_item)

            self._tree.addTopLevelItem(msg_item)
