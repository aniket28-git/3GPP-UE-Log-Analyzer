from __future__ import annotations
from datetime import datetime

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDateTimeEdit, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout,
)
from PyQt6.QtCore import QDateTime


class FilterPanel(QGroupBox):
    filter_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__("Filters", parent)
        layout = QVBoxLayout(self)

        # Layer
        layout.addWidget(QLabel("Layer:"))
        self._layer = QComboBox()
        self._layer.addItems(["(all)", "NAS", "RRC", "MAC", "PHY"])
        layout.addWidget(self._layer)

        # Severity
        layout.addWidget(QLabel("Severity:"))
        self._severity = QComboBox()
        self._severity.addItems(["(all)", "INFO", "WARNING", "ERROR", "CRITICAL"])
        layout.addWidget(self._severity)

        # Message type
        layout.addWidget(QLabel("Message Type:"))
        self._msg_type = QComboBox()
        self._msg_type.setEditable(True)
        self._msg_type.addItem("(all)")
        layout.addWidget(self._msg_type)

        # Time range
        layout.addWidget(QLabel("Start Time:"))
        self._start_dt = QDateTimeEdit()
        self._start_dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self._start_dt.setSpecialValueText("(any)")
        self._start_dt.setDateTime(QDateTime.fromString("2000-01-01 00:00:00", "yyyy-MM-dd HH:mm:ss"))
        layout.addWidget(self._start_dt)

        layout.addWidget(QLabel("End Time:"))
        self._end_dt = QDateTimeEdit()
        self._end_dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self._end_dt.setSpecialValueText("(any)")
        self._end_dt.setDateTime(QDateTime.fromString("2099-12-31 23:59:59", "yyyy-MM-dd HH:mm:ss"))
        layout.addWidget(self._end_dt)

        # Buttons
        btn_row = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._emit_filters)
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(apply_btn)
        btn_row.addWidget(reset_btn)
        layout.addLayout(btn_row)

        layout.addStretch()

    def populate_message_types(self, types: list[str]):
        current = self._msg_type.currentText()
        self._msg_type.clear()
        self._msg_type.addItem("(all)")
        for t in types:
            self._msg_type.addItem(t)
        idx = self._msg_type.findText(current)
        if idx >= 0:
            self._msg_type.setCurrentIndex(idx)

    def _emit_filters(self):
        layer = self._layer.currentText()
        severity = self._severity.currentText()
        msg_type = self._msg_type.currentText()

        filters: dict = {}
        if layer != "(all)":
            filters["layer"] = layer
        if severity != "(all)":
            filters["severity"] = severity
        if msg_type not in ("(all)", ""):
            filters["message_type"] = msg_type

        start = self._start_dt.dateTime().toPyDateTime()
        end = self._end_dt.dateTime().toPyDateTime()
        if start.year > 2000:
            filters["start_time"] = start
        if end.year < 2099:
            filters["end_time"] = end

        self.filter_changed.emit(filters)

    def _reset(self):
        self._layer.setCurrentIndex(0)
        self._severity.setCurrentIndex(0)
        self._msg_type.setCurrentIndex(0)
        self.filter_changed.emit({})
