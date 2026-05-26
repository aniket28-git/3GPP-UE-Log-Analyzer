from __future__ import annotations
from pathlib import Path
from PyQt6.QtWidgets import (
    QGroupBox, QLabel, QListWidget, QListWidgetItem, QVBoxLayout
)
from PyQt6.QtCore import Qt


class FilePanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Loaded Files", parent)
        layout = QVBoxLayout(self)
        self._list = QListWidget()
        self._list.setMaximumHeight(150)
        layout.addWidget(self._list)
        self._summary = QLabel("No files loaded")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

    def add_file(self, path: str, fmt: str, entry_count: int):
        name = Path(path).name
        item = QListWidgetItem(f"{name}  [{fmt}]  {entry_count} msgs")
        item.setToolTip(path)
        self._list.addItem(item)
        total = self._list.count()
        self._summary.setText(f"{total} file(s) loaded")
