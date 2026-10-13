"""Render README screenshots offscreen with a simulated monitor (no hardware, no personal data).

Usage: .venv/bin/python tools/screenshots.py [outdir]   (default: assets/screenshots)
"""

import json
import os
import sys
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "org.kde.desktop")
# Draw like a Plasma session (Breeze widgets style, KDE colours) instead of offscreen Fusion.
os.environ.setdefault("QT_STYLE_OVERRIDE", "Breeze")
os.environ.setdefault("QT_QPA_PLATFORMTHEME", "kde")

import shiboken6  # noqa: E402
from PySide6.QtCore import Q_ARG, QMetaObject, QPoint  # noqa: E402
from PySide6.QtGui import QCursor  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from benq_monitor_control.config.settings import Settings  # noqa: E402
from benq_monitor_control.core.controller import MonitorController  # noqa: E402
from benq_monitor_control.core.executor import ImmediateExecutor  # noqa: E402
from benq_monitor_control.core.session import MonitorSession  # noqa: E402
from benq_monitor_control.ddc.fake import FakeBackend  # noqa: E402
from benq_monitor_control.desktop.nightlight import NightLightWatcher  # noqa: E402
from benq_monitor_control.flow.service import FlowService  # noqa: E402
from benq_monitor_control.flow.store import ScenarioStore  # noqa: E402
from benq_monitor_control.models.ma320u import MA320U  # noqa: E402
from benq_monitor_control.ui.app import create_engine  # noqa: E402
from benq_monitor_control.ui.settings_bridge import SettingsBridge  # noqa: E402
from benq_monitor_control.ui.tray import Tray  # noqa: E402

SCENARIOS = [
    {"name": "Day", "schedule": {"kind": "sunrise", "offset_min": 0},
     "actions": [{"type": "picture_mode", "value": 0x0F}, {"type": "brightness", "value": 70}]},
    {"name": "Evening", "schedule": {"kind": "sunset", "offset_min": 30},
     "actions": [{"type": "picture_mode", "value": 0x0F}, {"type": "brightness", "value": 40},
                 {"type": "low_blue_light", "value": 3}]},
    {"name": "Cinema", "schedule": {"kind": "manual", "offset_min": 0},
     "actions": [{"type": "picture_mode", "value": 0x32}, {"type": "volume", "value": 25}]},
]


def quick_window(obj) -> QQuickWindow:
    return shiboken6.wrapInstance(shiboken6.getCppPointer(obj)[0], QQuickWindow)


def settle(app: QApplication, rounds: int = 20) -> None:
    for _ in range(rounds):
        app.processEvents()


def main() -> int:
    outdir = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/screenshots")
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    app = QApplication(sys.argv)
    QCursor.setPos(QPoint(10000, 10000))  # offscreen cursor sits at (0, 0) and would hover the first item

    controller = MonitorController(MonitorSession(FakeBackend(), MA320U), ImmediateExecutor())
    controller.start()
    location = Settings(latitude=52.52, longitude=13.405).location()  # Berlin, for the sun times
    flow = FlowService(ScenarioStore(tmp / "scenarios.json"), controller, lambda: location,
                       list_apps=lambda: [], launch=lambda d: True, logind=False)
    for spec in SCENARIOS:
        sid = flow.create(spec["name"])
        data = dict(next(s for s in flow.scenarios if s["id"] == sid), **{k: v for k, v in spec.items() if k != "name"})
        flow.update(json.dumps(data))
    evening = next(s["id"] for s in flow.scenarios if s["name"] == "Evening")
    flow.activate(evening)
    bridge = SettingsBridge(Settings(latitude=52.52, longitude=13.405), tmp / "settings.json",
                            autostart_fn=lambda e: None, autostart_state=lambda: True, panel_edge=lambda: "top")
    night = NightLightWatcher(fetch=lambda: None)
    tray = Tray(controller, flow, open_settings=lambda page: None, quit_app=lambda: None)
    engine, warnings = create_engine({"monitor": controller, "flow": flow, "appSettings": bridge,
                                      "nightLight": night, "tray": tray, "appInfo": {"version": "0.1.0"}})
    root = engine.rootObjects()[0]

    panel = quick_window(root.property("panel"))
    panel.show()
    settle(app)
    panel.grabWindow().save(str(outdir / "quick-panel.png"))
    panel.hide()

    window = quick_window(root.property("settingsWindow"))
    for page in ("flow", "general"):
        QMetaObject.invokeMethod(window, "showPage", Q_ARG("QVariant", page))
        settle(app)
        window.grabWindow().save(str(outdir / f"settings-{page}.png"))

    relevant = [w for w in warnings if "layershell" not in w.lower()]
    for w in relevant:
        print("QML warning:", w, file=sys.stderr)
    print("wrote", ", ".join(sorted(p.name for p in outdir.glob("*.png"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
