from PySide6.QtCore import QObject, Signal

from benq_monitor_control.core.controller import MonitorController
from benq_monitor_control.core.executor import ImmediateExecutor
from benq_monitor_control.core.session import MonitorSession
from benq_monitor_control.ddc.fake import FakeBackend
from benq_monitor_control.flow.service import FlowService
from benq_monitor_control.flow.store import ScenarioStore
from benq_monitor_control.models.ma320u import MA320U
from benq_monitor_control.ui.tray import Tray


class FakePanel(QObject):
    visibleChanged = Signal(bool)

    def __init__(self):
        super().__init__()
        self.visible = False
        self.activations = 0

    def isVisible(self):
        return self.visible

    def show(self):
        self.visible = True
        self.visibleChanged.emit(True)

    def hide(self):
        self.visible = False
        self.visibleChanged.emit(False)

    def requestActivate(self):
        self.activations += 1


class Clock:
    t = 10.0

    def __call__(self):
        return self.t


def make(qapp, tmp_path):
    controller = MonitorController(MonitorSession(FakeBackend(), MA320U), ImmediateExecutor())
    controller.start()
    flow = FlowService(ScenarioStore(tmp_path / "s.json"), controller, lambda: None, list_apps=lambda: [], logind=False)
    clock = Clock()
    tray = Tray(controller, flow, open_settings=lambda page: None, quit_app=lambda: None, clock=clock)
    panel = FakePanel()
    tray.attach_panel(panel)
    return tray, panel, flow, clock


def test_toggle_shows_and_hides(qapp, tmp_path):
    tray, panel, _, _ = make(qapp, tmp_path)
    tray.toggle_panel()
    assert panel.visible and panel.activations == 1
    tray.toggle_panel()
    assert not panel.visible


def test_click_that_closed_the_panel_does_not_reopen_it(qapp, tmp_path):
    tray, panel, _, clock = make(qapp, tmp_path)
    tray.toggle_panel()
    panel.hide()  # focus loss caused by clicking the tray icon
    clock.t += 0.1
    tray.toggle_panel()
    assert not panel.visible
    clock.t += 0.5
    tray.toggle_panel()
    assert panel.visible


def test_menu_lists_scenarios_and_marks_active(qapp, tmp_path):
    tray, _, flow, _ = make(qapp, tmp_path)
    flow.create("Day")
    evening = flow.create("Evening")
    flow.activate(evening)
    assert tray.scenario_entries() == [("Day", False), ("Evening", True)]


def test_set_texts_relabels_menu(qapp, tmp_path):
    tray, _, _, _ = make(qapp, tmp_path)
    tray.setTexts({"open": "Panel öffnen", "scenarios": "FloW-Szenarien", "settings": "Einstellungen …", "quit": "Beenden"})
    labels = [a.text() for a in tray.menu.actions() if a.text()]
    assert labels == ["Panel öffnen", "FloW-Szenarien", "Einstellungen …", "Beenden"]
