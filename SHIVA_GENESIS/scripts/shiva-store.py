#!/usr/bin/env python3
"""Shiva Store — Catalogue gaming ShivaOS (shivaos.com)"""
import sys, subprocess
try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
    from PyQt6.QtCore import Qt, QUrl
    from PyQt6.QtGui import QFont
except ImportError:
    from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
    from PyQt5.QtCore import Qt, QUrl
    from PyQt5.QtGui import QFont

STORE_URL = "https://shivaos.com/store.php"

STYLE = """
QMainWindow, QWidget {
    background-color: #0d0d1a;
    color: #e0e0e0;
}
"""

def open_in_browser():
    for browser in ["firefox", "chromium-browser", "chromium", "xdg-open"]:
        try:
            subprocess.Popen([browser, STORE_URL])
            sys.exit(0)
        except FileNotFoundError:
            continue
    sys.exit(1)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Shiva Store")

    # Essai PyQt6 (Qt6 installé sur Fedora 44) puis PyQt5 en fallback
    WebEngineView = None
    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView as WebEngineView
        from PyQt6.QtCore import QUrl as QUrl6
        USE_QT6 = True
    except ImportError:
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView as WebEngineView
            from PyQt5.QtCore import QUrl as QUrl6
            USE_QT6 = False
        except ImportError:
            open_in_browser()

    win = QMainWindow()
    win.setWindowTitle("🔱 Shiva Store — Pure Gaming")
    win.setMinimumSize(1100, 750)
    win.setStyleSheet(STYLE)

    header = QWidget()
    header.setFixedHeight(48)
    header.setStyleSheet("background:#0d0d1a; border-bottom:2px solid #ff6400;")
    hlay = QVBoxLayout(header)
    hlay.setContentsMargins(20, 0, 20, 0)
    hlay.setAlignment(Qt.AlignmentFlag.AlignVCenter if USE_QT6 else Qt.AlignVCenter)
    title = QLabel("🔱  SHIVA STORE  —  Pure Gaming Ecosystem")
    title.setFont(QFont("Sans", 13, QFont.Weight.Bold if USE_QT6 else QFont.Bold))
    title.setStyleSheet("color:#ff6400; letter-spacing:2px;")
    hlay.addWidget(title)

    view = WebEngineView()
    view.load(QUrl6(STORE_URL))

    central = QWidget()
    win.setCentralWidget(central)
    layout = QVBoxLayout(central)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(header)
    layout.addWidget(view)

    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
