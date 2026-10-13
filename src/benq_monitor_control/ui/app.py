"""Application bootstrap: wiring, QML engine, tray, logging."""

import logging
import os
import sys
from collections.abc import Mapping
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .. import __version__
from ..config.paths import config_dir, state_dir
from ..config.settings import load_settings
from ..core.controller import MonitorController
from ..core.executor import QtWorkerExecutor
from ..core.session import MonitorSession
from ..ddc.ddcutil_cli import DdcutilCli
from ..desktop.nightlight import NightLightWatcher
from ..flow.service import FlowService
from ..flow.store import ScenarioStore
from ..models.ma320u import MA320U

log = logging.getLogger(__name__)
QML_DIR = Path(__file__).parent / "qml"
ICON_DIR = Path(__file__).parent / "icons"


def setup_logging(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(directory / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def create_engine(context: Mapping[str, object], qml_dir: Path = QML_DIR):
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    engine = QQmlApplicationEngine()
    warnings: list[str] = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    # QML does not own context objects; keep them alive as long as the engine.
    engine._context_refs = dict(context)
    for name, value in context.items():
        engine.rootContext().setContextProperty(name, value)
    engine.load(QUrl.fromLocalFile(str(qml_dir / "Main.qml")))
    return engine, warnings


def run(argv: list[str] | None = None) -> int:
    os.environ["QT_QPA_PLATFORM"] = "wayland"  # Wayland only (spec §1.2)

    from PySide6.QtCore import Q_ARG, QLibraryInfo, QMetaObject
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon

    from .i18n import LanguageManager
    from .settings_bridge import SettingsBridge
    from .tray import Tray

    kde_style = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.QmlImportsPath)) / "org" / "kde" / "desktop"
    if kde_style.is_dir():
        os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "org.kde.desktop")

    setup_logging(state_dir())
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("benq-monitor-control")
    app.setApplicationDisplayName("BenQ Monitor Control")
    app.setDesktopFileName("benq-monitor-control")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(ICON_DIR / "monitor.svg")))
    if app.platformName() != "wayland":
        print("benq-monitor-control needs a Wayland session.", file=sys.stderr)
        return 1
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("No system tray available.", file=sys.stderr)
        return 1

    settings_path = config_dir() / "settings.json"
    settings = load_settings(settings_path)
    executor = QtWorkerExecutor()
    controller = MonitorController(
        MonitorSession(DdcutilCli(), MA320U), executor, poll_interval_s=settings.sync_interval_s
    )
    engine_ref: dict[str, object] = {}
    languages = LanguageManager(app, lambda: engine_ref.get("engine"))
    flow_ref: dict[str, FlowService] = {}
    bridge = SettingsBridge(
        settings,
        settings_path,
        on_language=languages.apply,
        on_location=lambda: flow_ref["flow"].replan(),
        on_sync_interval=controller.setPollInterval,
    )
    flow = FlowService(ScenarioStore(config_dir() / "scenarios.json"), controller, bridge.location)
    flow_ref["flow"] = flow
    night = NightLightWatcher()
    windows: dict[str, object] = {}

    def open_settings(page: str) -> None:
        window = windows.get("settings")
        if window is not None:
            QMetaObject.invokeMethod(window, "showPage", Q_ARG("QVariant", page))

    tray = Tray(controller, flow, open_settings=open_settings, quit_app=app.quit)
    languages.apply(settings.language)
    engine, warnings = create_engine(
        {
            "monitor": controller,
            "flow": flow,
            "appSettings": bridge,
            "nightLight": night,
            "tray": tray,
            "appInfo": {"version": __version__},
        }
    )
    engine_ref["engine"] = engine
    if not engine.rootObjects():
        log.error("QML failed to load: %s", warnings)
        return 1
    root = engine.rootObjects()[0]
    windows["settings"] = root.property("settingsWindow")
    tray.attach_panel(root.property("panel"))

    app.screenAdded.connect(lambda _screen: controller.onScreensChanged())
    app.screenRemoved.connect(lambda _screen: controller.onScreensChanged())
    controller.start()
    flow.start()
    night.start()
    log.info("started %s", __version__)
    try:
        return app.exec()
    finally:
        executor.shutdown()
