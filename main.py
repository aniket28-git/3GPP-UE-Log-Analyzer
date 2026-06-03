from __future__ import annotations
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow
from ui.theme import apply as apply_theme


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("3GPP UE Log Analyzer")
    app.setOrganizationName("UEAnalyzer")
    apply_theme(app)

    window = MainWindow()
    window.show()

    # If a log file was passed as CLI argument, load it immediately
    if len(sys.argv) > 1:
        window._load_file(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
