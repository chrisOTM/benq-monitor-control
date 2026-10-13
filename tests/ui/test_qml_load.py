import json

from benq_monitor_control.config.settings import Settings
from benq_monitor_control.core.controller import MonitorController
from benq_monitor_control.core.executor import ImmediateExecutor
from benq_monitor_control.core.session import MonitorSession
from benq_monitor_control.ddc.fake import FakeBackend
from benq_monitor_control.desktop.nightlight import NightLightWatcher
from benq_monitor_control.flow.service import FlowService
from benq_monitor_control.flow.store import ScenarioStore
from benq_monitor_control.models.ma320u import MA320U
from benq_monitor_control.ui.app import create_engine
from benq_monitor_control.ui.settings_bridge import SettingsBridge
from benq_monitor_control.ui.tray import Tray

ALL_ACTIONS = [
    {"type": "picture_mode", "value": 15},
    {"type": "brightness", "value": 40},
    {"type": "volume", "value": 10},
    {"type": "low_blue_light", "value": 3},
    {"type": "brightness_intelligence", "value": 1},
    {"type": "open_app", "desktop_id": "org.kde.konsole.desktop"},
]


def build(tmp_path):
    controller = MonitorController(MonitorSession(FakeBackend(), MA320U), ImmediateExecutor())
    controller.start()
    flow = FlowService(
        ScenarioStore(tmp_path / "s.json"), controller, lambda: None,
        list_apps=lambda: [], launch=lambda d: True, logind=False,
    )
    scenario_id = flow.create("Evening")
    data = dict(flow.scenarios[0], actions=ALL_ACTIONS, schedule={"kind": "time", "at": "20:00", "offset_min": 0})
    flow.update(json.dumps(data))
    flow.activate(scenario_id)
    bridge = SettingsBridge(
        Settings(), tmp_path / "settings.json", autostart_fn=lambda e: None, autostart_state=lambda: False
    )
    night = NightLightWatcher(fetch=lambda: None)
    tray = Tray(controller, flow, open_settings=lambda page: None, quit_app=lambda: None)
    context = {
        "monitor": controller, "flow": flow, "appSettings": bridge,
        "nightLight": night, "tray": tray, "appInfo": {"version": "0.1.0"},
    }
    return context


def test_main_qml_loads_without_warnings(qapp, tmp_path):
    engine, warnings = create_engine(build(tmp_path))
    assert engine.rootObjects(), warnings
    root = engine.rootObjects()[0]
    assert root.property("panel") is not None
    assert root.property("settingsWindow") is not None
    # The offscreen test platform has no layer-shell; such warnings are expected here.
    relevant = [w for w in warnings if "layershell" not in w.lower() and "layer shell" not in w.lower()]
    assert relevant == []


def test_flow_page_editor_gets_the_space(qapp, tmp_path):
    from PySide6.QtCore import Q_ARG, QMetaObject
    from PySide6.QtQuick import QQuickItem

    context = build(tmp_path)
    engine, _ = create_engine(context)
    window = engine.rootObjects()[0].property("settingsWindow")
    QMetaObject.invokeMethod(window, "showPage", Q_ARG("QVariant", "flow"))
    for _ in range(5):
        qapp.processEvents()
    scenario_list = window.findChild(QQuickItem, "flowList")
    editor = window.findChild(QQuickItem, "flowEditor")
    assert scenario_list.width() <= 240
    assert editor.width() > 400
    window.close()


def test_comboboxes_show_their_current_value(qapp, tmp_path):
    from PySide6.QtCore import Q_ARG, QMetaObject, QObject

    context = build(tmp_path)
    engine, _ = create_engine(context)
    root = engine.rootObjects()[0]
    window = root.property("settingsWindow")
    QMetaObject.invokeMethod(window, "showPage", Q_ARG("QVariant", "general"))
    for _ in range(5):
        qapp.processEvents()
    assert window.findChild(QObject, "languageBox").property("currentIndex") == 0  # English
    assert window.findChild(QObject, "cornerBox").property("currentIndex") == 0  # Automatic
    panel = root.property("panel")
    # The fake monitor reports input 0x13 (USB-C), the 4th entry.
    assert panel.findChild(QObject, "inputBox").property("currentIndex") == 3
    window.close()
