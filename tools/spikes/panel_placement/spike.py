"""Throwaway spike: anchor a QML panel via org.kde.layershell from PySide6.

Usage: python spike.py [layershell|plain]
"""

import os
import signal
import sys
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "wayland"

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QStyle, QSystemTrayIcon


def main() -> int:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    variant = sys.argv[1] if len(sys.argv) > 1 else "layershell"
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    engine = QQmlApplicationEngine()
    name = "PanelLayerShell.qml" if variant == "layershell" else "PanelPlain.qml"
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name(name))))
    if not engine.rootObjects():
        print("QML failed to load")
        return 1
    panel = engine.rootObjects()[0]
    state = {"t0": 0.0, "hidden": float("-inf")}

    def on_visible(visible: bool) -> None:
        if visible:
            print(f"panel visible after {(time.monotonic() - state['t0']) * 1000:.0f} ms", flush=True)
        else:
            state["hidden"] = time.monotonic()
            print("panel hidden", flush=True)

    panel.visibleChanged.connect(on_visible)
    panel.activeChanged.connect(lambda: print("active:", panel.isActive(), flush=True))

    def toggle(reason) -> None:
        if reason is not QSystemTrayIcon.ActivationReason.Trigger:
            return
        if panel.isVisible():
            panel.hide()
            return
        if time.monotonic() - state["hidden"] < 0.3:
            return  # this click already closed the panel via focus loss
        state["t0"] = time.monotonic()
        panel.show()
        panel.requestActivate()

    tray = QSystemTrayIcon(app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
    tray.activated.connect(toggle)
    tray.show()
    print(f"platform={app.platformName()} variant={variant}; click the tray icon, Ctrl+C quits", flush=True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
