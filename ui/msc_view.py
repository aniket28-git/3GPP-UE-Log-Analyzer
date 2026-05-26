from __future__ import annotations
from typing import Sequence

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QFont, QPen, QBrush, QPainter
from PyQt6.QtWidgets import (
    QGraphicsLineItem, QGraphicsScene, QGraphicsTextItem,
    QGraphicsView, QVBoxLayout, QWidget,
)

from core.log_entry import LogEntry

# Entities and their X positions
ENTITIES = ["UE", "eNB/gNB", "MME/AMF", "SGW/UPF"]
ENTITY_X = {e: (i + 1) * 180 for i, e in enumerate(ENTITIES)}
LINE_SPACING = 36
ARROW_LEN = 8
ENTITY_Y = 30
FIRST_MSG_Y = 80

# Which entity sends / receives each message type
_MSG_ROUTING: dict[str, tuple[str, str]] = {
    # NAS (UE ↔ MME/AMF)
    "Attach Request":                ("UE", "MME/AMF"),
    "Attach Accept":                 ("MME/AMF", "UE"),
    "Attach Reject":                 ("MME/AMF", "UE"),
    "Attach Complete":               ("UE", "MME/AMF"),
    "Detach Request":                ("UE", "MME/AMF"),
    "Detach Accept":                 ("MME/AMF", "UE"),
    "Authentication Request":        ("MME/AMF", "UE"),
    "Authentication Response":       ("UE", "MME/AMF"),
    "Authentication Failure":        ("UE", "MME/AMF"),
    "Security Mode Command":         ("MME/AMF", "UE"),
    "Security Mode Complete":        ("UE", "MME/AMF"),
    "Security Mode Reject":          ("UE", "MME/AMF"),
    "Tracking Area Update Request":  ("UE", "MME/AMF"),
    "Tracking Area Update Accept":   ("MME/AMF", "UE"),
    "Tracking Area Update Reject":   ("MME/AMF", "UE"),
    "Registration Request":          ("UE", "MME/AMF"),
    "Registration Accept":           ("MME/AMF", "UE"),
    "Registration Reject":           ("MME/AMF", "UE"),
    "Registration Complete":         ("UE", "MME/AMF"),
    "Pdn Connectivity Request":      ("UE", "MME/AMF"),
    "Pdn Connectivity Accept":       ("MME/AMF", "UE"),
    "Pdu Session Establishment Request": ("UE", "MME/AMF"),
    "Pdu Session Establishment Accept":  ("MME/AMF", "UE"),
    "Pdu Session Establishment Reject":  ("MME/AMF", "UE"),
    "Identity Request":              ("MME/AMF", "UE"),
    "Identity Response":             ("UE", "MME/AMF"),
    # RRC (UE ↔ eNB/gNB)
    "Rrcconnectionrequest":          ("UE", "eNB/gNB"),
    "Rrcconnectionsetup":            ("eNB/gNB", "UE"),
    "Rrcconnectionsetupcomplete":    ("UE", "eNB/gNB"),
    "Rrcconnectionreject":           ("eNB/gNB", "UE"),
    "Rrcconnectionreconfiguration":  ("eNB/gNB", "UE"),
    "Rrcconnectionreconfigurationcomplete": ("UE", "eNB/gNB"),
    "Rrcconnectionrelease":          ("eNB/gNB", "UE"),
    "Rrcreestablishmentrequest":     ("UE", "eNB/gNB"),
    "Rrcreestablishment":            ("eNB/gNB", "UE"),
    "Rrcreestablishmentcomplete":    ("UE", "eNB/gNB"),
    "Measurementreport":             ("UE", "eNB/gNB"),
    "Rrcsetup":                      ("eNB/gNB", "UE"),
    "Rrcsetuprequest":               ("UE", "eNB/gNB"),
    "Rrcsetupcomplete":              ("UE", "eNB/gNB"),
    "Rrcreconfiguration":            ("eNB/gNB", "UE"),
    "Rrcrelease":                    ("eNB/gNB", "UE"),
}

SUCCESS_COLOR = QColor("#388E3C")
FAILURE_COLOR = QColor("#D32F2F")
DEFAULT_COLOR = QColor("#1565C0")


class MSCView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._scene = QGraphicsScene()
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        layout.addWidget(self._view)

    def load(self, entries: Sequence[LogEntry]):
        self._scene.clear()
        if not entries:
            return

        sorted_entries = sorted(entries, key=lambda e: e.timestamp)

        # Draw entity headers
        for name, x in ENTITY_X.items():
            box = self._scene.addRect(x - 50, 5, 100, 24)
            box.setBrush(QBrush(QColor("#1565C0")))
            lbl = QGraphicsTextItem(name)
            lbl.setDefaultTextColor(QColor("white"))
            lbl.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            lbl.setPos(x - 40, 8)
            self._scene.addItem(lbl)

        # Draw vertical entity lifelines
        total_h = FIRST_MSG_Y + len(sorted_entries) * LINE_SPACING + 40
        for x in ENTITY_X.values():
            line = self._scene.addLine(x, 30, x, total_h)
            line.setPen(QPen(QColor("#BBBBBB"), 1, Qt.PenStyle.DashLine))

        # Draw message arrows
        y = FIRST_MSG_Y
        for entry in sorted_entries:
            routing = _MSG_ROUTING.get(entry.message_type)
            if not routing:
                routing = _MSG_ROUTING.get(entry.message_type.title())
            if not routing:
                continue

            src_entity, dst_entity = routing
            x1 = ENTITY_X.get(src_entity, ENTITY_X["UE"])
            x2 = ENTITY_X.get(dst_entity, ENTITY_X["MME/AMF"])

            is_failure = any(
                kw in entry.message_type.lower()
                for kw in ("reject", "failure", "fail", "error")
            )
            is_success = any(
                kw in entry.message_type.lower()
                for kw in ("accept", "complete", "success")
            )

            color = FAILURE_COLOR if is_failure else (SUCCESS_COLOR if is_success else DEFAULT_COLOR)

            # Arrow line
            arrow_line = self._scene.addLine(x1, y, x2, y)
            arrow_line.setPen(QPen(color, 1.5))

            # Arrowhead
            dx = 1 if x2 > x1 else -1
            tip_x = x2
            self._scene.addLine(tip_x, y, tip_x - dx * ARROW_LEN, y - 5).setPen(QPen(color, 1.5))
            self._scene.addLine(tip_x, y, tip_x - dx * ARROW_LEN, y + 5).setPen(QPen(color, 1.5))

            # Message label
            mid_x = (x1 + x2) / 2
            label = QGraphicsTextItem(entry.message_type)
            label.setDefaultTextColor(color)
            label.setFont(QFont("Arial", 7))
            label.setPos(mid_x - len(entry.message_type) * 2.5, y - 14)
            self._scene.addItem(label)

            # Timestamp label on left
            ts_lbl = QGraphicsTextItem(entry.timestamp.strftime("%H:%M:%S.%f")[:-3])
            ts_lbl.setFont(QFont("Monospace", 6))
            ts_lbl.setDefaultTextColor(QColor("#888"))
            ts_lbl.setPos(5, y - 10)
            self._scene.addItem(ts_lbl)

            y += LINE_SPACING

        self._scene.setSceneRect(0, 0, max(ENTITY_X.values()) + 100, y + 20)
