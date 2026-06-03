from __future__ import annotations
from datetime import datetime
from typing import Sequence

from PyQt6.QtCore import pyqtSignal, Qt, QRectF, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QBrush, QWheelEvent
from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QGraphicsEllipseItem,
    QGraphicsTextItem, QToolTip, QWidget, QVBoxLayout, QLabel,
)

from core.log_entry import AnalysisEvent
from ui.theme import LANE_BG_EVEN, LANE_BG_ODD, LANE_GRID, LANE_LABEL

SEVERITY_COLORS = {
    "INFO":     QColor("#2ed573"),
    "WARNING":  QColor("#ffa502"),
    "ERROR":    QColor("#ff4757"),
    "CRITICAL": QColor("#a55eea"),
}

LAYER_Y: dict[str, int] = {
    "NAS": 40,
    "RRC": 90,
    "MAC": 140,
    "PHY": 190,
    "GTP": 240,
    "UNKNOWN": 290,
}

LANE_HEIGHT = 50
MARKER_R = 6
LABEL_OFFSET_Y = -18


class EventMarker(QGraphicsEllipseItem):
    def __init__(self, event: AnalysisEvent, x: float, y: float, color: QColor):
        super().__init__(x - MARKER_R, y - MARKER_R, MARKER_R * 2, MARKER_R * 2)
        self._event = event
        self.setBrush(QBrush(color))
        self.setPen(QPen(color.darker(130), 1.5))
        self.setAcceptHoverEvents(True)
        self.setZValue(2)

    @property
    def event(self) -> AnalysisEvent:
        return self._event


class TimelineView(QWidget):
    event_selected = pyqtSignal(AnalysisEvent)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._scene = QGraphicsScene()
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setBackgroundBrush(QBrush(QColor("#181b2d")))
        self._view.wheelEvent = self._wheel_event
        self._view.mousePressEvent = self._mouse_press
        layout.addWidget(self._view)

        self._events: list[AnalysisEvent] = []
        self._markers: list[EventMarker] = []
        self._scale_x: float = 1.0

    def load_events(self, events: Sequence[AnalysisEvent]):
        self._events = sorted(events, key=lambda e: e.timestamp)
        self._render()

    def current_events(self) -> list[AnalysisEvent]:
        return list(self._events)

    def fit_to_window(self):
        self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _render(self):
        self._scene.clear()
        self._markers.clear()
        if not self._events:
            return

        t_min = self._events[0].timestamp
        t_max = self._events[-1].timestamp
        total_sec = max((t_max - t_min).total_seconds(), 1.0)
        width = max(1200, total_sec * self._scale_x * 2)

        # Draw lane backgrounds and labels
        layers = list(LAYER_Y.keys())
        for layer, y in LAYER_Y.items():
            bg = QColor(LANE_BG_EVEN if layers.index(layer) % 2 == 0 else LANE_BG_ODD)
            rect = self._scene.addRect(0, y - LANE_HEIGHT // 2, width, LANE_HEIGHT)
            rect.setBrush(QBrush(bg))
            rect.setPen(QPen(Qt.GlobalColor.transparent))
            rect.setZValue(0)

            lbl = QGraphicsTextItem(layer)
            lbl.setPos(-60, y - 10)
            lbl.setDefaultTextColor(QColor(LANE_LABEL))
            font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            lbl.setFont(font)
            lbl.setZValue(1)
            self._scene.addItem(lbl)

            line = self._scene.addLine(0, y + LANE_HEIGHT // 2, width, y + LANE_HEIGHT // 2)
            line.setPen(QPen(QColor(LANE_GRID), 1.0))
            line.setZValue(1)

        # Draw time axis ticks
        tick_interval_sec = max(1, int(total_sec / (width / 60)))
        import math
        tick_sec = 0
        while tick_sec <= total_sec:
            x = tick_sec / total_sec * width
            tick_line = self._scene.addLine(x, 0, x, 320)
            tick_line.setPen(QPen(QColor("#252840"), 0.8, Qt.PenStyle.DashLine))
            tick_line.setZValue(0)
            tick_sec += tick_interval_sec

        # Draw event markers
        for ev in self._events:
            elapsed = (ev.timestamp - t_min).total_seconds()
            x = elapsed / total_sec * width
            layer = ev.entry.layer if ev.entry else "UNKNOWN"
            y = LAYER_Y.get(layer, LAYER_Y["UNKNOWN"])
            color = SEVERITY_COLORS.get(ev.severity, QColor("#888"))
            marker = EventMarker(ev, x, y, color)
            self._scene.addItem(marker)
            self._markers.append(marker)

        self._scene.setSceneRect(-80, -10, width + 100, 340)

    def _wheel_event(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._view.scale(factor, 1.0)

    def _mouse_press(self, event):
        # Forward to base first
        QGraphicsView.mousePressEvent(self._view, event)

        scene_pos = self._view.mapToScene(event.pos())
        items = self._scene.items(QRectF(scene_pos.x() - 8, scene_pos.y() - 8, 16, 16))
        for item in items:
            if isinstance(item, EventMarker):
                self.event_selected.emit(item.event)
                break
