from __future__ import annotations
import csv
import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QSplitter, QStatusBar,
    QTabWidget, QVBoxLayout, QWidget,
)

from core.ingestion.loader import load_log
from core.ingestion.detector import detect_format
from core.parsers import nas_parser, rrc_parser, phy_parser
from core.analysis.classifier import classify
from core.analysis.kpi_engine import compute_kpis
from core.analysis.anomaly import detect_anomalies
from core.storage.repository import Repository
from core.log_entry import LogEntry, AnalysisEvent, RadioMeasurement

from ui.file_panel import FilePanel
from ui.filter_panel import FilterPanel
from ui.timeline_view import TimelineView
from ui.detail_panel import DetailPanel
from ui.kpi_dashboard import KPIDashboard
from ui.msc_view import MSCView


class LoadWorker(QThread):
    progress = pyqtSignal(int, int)      # (done, total)
    finished = pyqtSignal(list, list, list)  # (entries, events, measurements)
    error = pyqtSignal(str)

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def run(self):
        try:
            entries: list[LogEntry] = []
            events: list[AnalysisEvent] = []
            measurements: list[RadioMeasurement] = []

            raw_entries = list(load_log(self.path))
            total = len(raw_entries)

            for i, entry in enumerate(raw_entries):
                # Enrich with layer-specific parsers
                nas_parser.enrich_entry(entry)
                rrc_parser.enrich_entry(entry)
                entries.append(entry)

                ev = classify(entry)
                if ev:
                    events.append(ev)

                meas = phy_parser.parse_phy_measurement(entry)
                if meas:
                    measurements.append(meas)

                if i % 100 == 0:
                    self.progress.emit(i, total)

            # Run anomaly detection on all events
            anomalies = detect_anomalies(events)
            events.extend(anomalies)
            events.sort(key=lambda e: e.timestamp)

            self.finished.emit(entries, events, measurements)
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3GPP UE Log Analyzer")
        self.resize(1400, 900)

        self._repo = Repository("ue_analyzer.db")
        self._all_entries: list[LogEntry] = []
        self._all_events: list[AnalysisEvent] = []
        self._all_measurements: list[RadioMeasurement] = []
        self._loaded_files: list[str] = []

        self._build_menu()
        self._build_ui()
        self._build_status_bar()

    # ── Menu ──────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("File")
        open_act = QAction("Open Log File…", self)
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._open_file)
        file_menu.addAction(open_act)

        file_menu.addSeparator()

        export_csv = QAction("Export Filtered Events → CSV", self)
        export_csv.triggered.connect(self._export_csv)
        file_menu.addAction(export_csv)

        export_json = QAction("Export Filtered Events → JSON", self)
        export_json.triggered.connect(self._export_json)
        file_menu.addAction(export_json)

        file_menu.addSeparator()
        quit_act = QAction("Quit", self)
        quit_act.setShortcut("Ctrl+Q")
        quit_act.triggered.connect(QApplication.quit)
        file_menu.addAction(quit_act)

        view_menu = mb.addMenu("View")
        fit_act = QAction("Fit Timeline to Window", self)
        fit_act.setShortcut("Ctrl+F")
        fit_act.triggered.connect(self._fit_timeline)
        view_menu.addAction(fit_act)

        help_menu = mb.addMenu("Help")
        about_act = QAction("About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    # ── UI Layout ─────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(4, 4, 4, 4)
        root_layout.setSpacing(4)

        # Top splitter: (left sidebar) | (timeline + detail)
        h_split = QSplitter(Qt.Orientation.Horizontal)

        # Left: file list + filters
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.file_panel = FilePanel()
        self.filter_panel = FilterPanel()
        self.filter_panel.filter_changed.connect(self._apply_filters)

        left_layout.addWidget(self.file_panel)
        left_layout.addWidget(self.filter_panel)
        left_widget.setMaximumWidth(280)

        # Right: timeline + tabs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Timeline
        self.timeline = TimelineView()
        self.timeline.event_selected.connect(self._on_event_selected)
        self.timeline.setMinimumHeight(200)

        # Detail / KPI / MSC tabs
        self.tabs = QTabWidget()
        self.detail_panel = DetailPanel()
        self.kpi_dashboard = KPIDashboard()
        self.msc_view = MSCView()

        self.tabs.addTab(self.detail_panel, "Message Detail")
        self.tabs.addTab(self.kpi_dashboard, "KPI Dashboard")
        self.tabs.addTab(self.msc_view, "Message Sequence Chart")

        right_v_split = QSplitter(Qt.Orientation.Vertical)
        right_v_split.addWidget(self.timeline)
        right_v_split.addWidget(self.tabs)
        right_v_split.setSizes([300, 400])

        right_layout.addWidget(right_v_split)

        h_split.addWidget(left_widget)
        h_split.addWidget(right_widget)
        h_split.setSizes([270, 1100])

        root_layout.addWidget(h_split)

    def _build_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._progress = QProgressBar()
        self._progress.setMaximumWidth(200)
        self._progress.setVisible(False)
        self.status_bar.addPermanentWidget(self._progress)
        self._status_label = QLabel("Ready")
        self.status_bar.addWidget(self._status_label)

    # ── File loading ──────────────────────────────────────────────────────

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Log File",
            "",
            "Log Files (*.txt *.log *.pcap *.pcapng *.dlf *.isf);;All Files (*)",
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        self._status_label.setText(f"Loading {Path(path).name}…")
        self._progress.setVisible(True)
        self._progress.setValue(0)

        self._worker = LoadWorker(path)
        self._worker.progress.connect(self._on_load_progress)
        self._worker.finished.connect(lambda e, ev, m: self._on_load_finished(path, e, ev, m))
        self._worker.error.connect(self._on_load_error)
        self._worker.start()

    def _on_load_progress(self, done: int, total: int):
        if total > 0:
            self._progress.setValue(int(done / total * 100))

    def _on_load_finished(
        self,
        path: str,
        entries: list[LogEntry],
        events: list[AnalysisEvent],
        measurements: list[RadioMeasurement],
    ):
        self._all_entries.extend(entries)
        self._all_events.extend(events)
        self._all_measurements.extend(measurements)
        self._loaded_files.append(path)

        fmt = detect_format(path)
        self.file_panel.add_file(path, fmt, len(entries))

        self.timeline.load_events(self._all_events)
        self.kpi_dashboard.load(self._all_events, self._all_measurements)
        self.msc_view.load(entries)
        self.filter_panel.populate_message_types(
            sorted({e.message_type for e in entries})
        )

        n_err = sum(1 for e in events if e.severity in ("ERROR", "CRITICAL"))
        self._status_label.setText(
            f"Loaded {len(entries)} messages, {len(events)} events "
            f"({n_err} errors/criticals)"
        )
        self._progress.setVisible(False)

    def _on_load_error(self, msg: str):
        self._progress.setVisible(False)
        self._status_label.setText("Load failed")
        QMessageBox.critical(self, "Load Error", msg)

    # ── Filtering ─────────────────────────────────────────────────────────

    def _apply_filters(self, filters: dict):
        filtered = self._all_events

        layer = filters.get("layer")
        if layer:
            filtered = [e for e in filtered if e.entry and e.entry.layer == layer]

        severity = filters.get("severity")
        if severity:
            filtered = [e for e in filtered if e.severity == severity]

        msg_type = filters.get("message_type")
        if msg_type:
            filtered = [
                e for e in filtered
                if e.entry and msg_type.lower() in e.entry.message_type.lower()
            ]

        start = filters.get("start_time")
        end = filters.get("end_time")
        if start:
            filtered = [e for e in filtered if e.timestamp >= start]
        if end:
            filtered = [e for e in filtered if e.timestamp <= end]

        self.timeline.load_events(filtered)
        self.kpi_dashboard.load(filtered, self._all_measurements)

    # ── Event selection ───────────────────────────────────────────────────

    def _on_event_selected(self, event: AnalysisEvent):
        self.detail_panel.show_event(event)
        self.tabs.setCurrentIndex(0)

    # ── Timeline fit ──────────────────────────────────────────────────────

    def _fit_timeline(self):
        self.timeline.fit_to_window()

    # ── Export ────────────────────────────────────────────────────────────

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV (*.csv)")
        if not path:
            return
        events = self.timeline.current_events()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Event Type", "Severity", "Description"])
            for ev in events:
                writer.writerow([ev.timestamp.isoformat(), ev.event_type, ev.severity, ev.description])
        self._status_label.setText(f"Exported {len(events)} events to CSV")

    def _export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", "", "JSON (*.json)")
        if not path:
            return
        events = self.timeline.current_events()
        data = [
            {
                "timestamp": ev.timestamp.isoformat(),
                "event_type": ev.event_type,
                "severity": ev.severity,
                "description": ev.description,
                "cause_code": ev.cause_code,
            }
            for ev in events
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self._status_label.setText(f"Exported {len(events)} events to JSON")

    # ── About ─────────────────────────────────────────────────────────────

    def _show_about(self):
        QMessageBox.about(
            self,
            "About 3GPP UE Log Analyzer",
            "3GPP UE Log Analyzer\n\n"
            "Supports NAS (TS 24.301/24.501), RRC (TS 36.331/38.331),\n"
            "PHY radio measurements, KPI computation, and anomaly detection.\n\n"
            "Layers: LTE (4G) and NR (5G)",
        )

    def closeEvent(self, event):
        self._repo.close()
        super().closeEvent(event)
