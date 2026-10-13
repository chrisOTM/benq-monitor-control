"""System tray icon (StatusNotifierItem on Plasma) with the quick-panel toggle and menu."""

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

ICON_DIR = Path(__file__).parent / "icons"
# A click on the tray icon first hides the open panel (focus loss), then arrives here.
REOPEN_GUARD_S = 0.3


class Tray(QObject):
    def __init__(
        self,
        controller: Any,
        flow: Any,
        *,
        open_settings: Callable[[str], None],
        quit_app: Callable[[], None],
        icon_dir: Path = ICON_DIR,
        clock: Callable[[], float] = time.monotonic,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._flow = flow
        self._open_settings = open_settings
        self._quit = quit_app
        self._clock = clock
        self._panel: Any = None
        self._last_hidden = float("-inf")
        self._texts = {
            "open": "Open panel",
            "scenarios": "FloW scenarios",
            "settings": "Settings…",
            "quit": "Quit",
            "unreachable": "Monitor not reachable",
        }
        self._icons = {
            True: QIcon(str(icon_dir / "monitor.svg")),
            False: QIcon(str(icon_dir / "monitor-offline.svg")),
        }
        self.menu = QMenu()
        self._scenario_menu = QMenu()
        self._icon = QSystemTrayIcon(self._icons[False], self)
        self._icon.setContextMenu(self.menu)
        self._icon.activated.connect(self._on_activated)
        controller.stateChanged.connect(self._update_icon)
        flow.scenariosChanged.connect(self._rebuild_menu)
        flow.activeChanged.connect(self._rebuild_menu)
        self._rebuild_menu()
        self._update_icon()
        self._icon.show()

    def attach_panel(self, panel: Any) -> None:
        self._panel = panel
        panel.visibleChanged.connect(self._on_panel_visible)

    def toggle_panel(self) -> None:
        if self._panel is None:
            return
        if self._panel.isVisible():
            self._panel.hide()
            return
        if self._clock() - self._last_hidden < REOPEN_GUARD_S:
            return
        self._panel.show()
        self._panel.requestActivate()

    def scenario_entries(self) -> list[tuple[str, bool]]:
        return [(a.text(), a.isChecked()) for a in self._scenario_menu.actions()]

    @Slot("QVariantMap")
    def setTexts(self, texts: dict[str, Any]) -> None:
        self._texts.update({str(k): str(v) for k, v in texts.items()})
        self._rebuild_menu()
        self._update_icon()

    @Slot(str, str)
    def notify(self, title: str, body: str) -> None:
        self._icon.showMessage(title, body, self._icons[True], 5000)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason is QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_panel()

    def _on_panel_visible(self, visible: bool) -> None:
        if not visible:
            self._last_hidden = self._clock()

    def _update_icon(self) -> None:
        reachable = bool(self._controller.reachable)
        self._icon.setIcon(self._icons[reachable])
        name = self._controller.displayName
        self._icon.setToolTip(name if reachable else f"{name} — {self._texts['unreachable']}")

    def _rebuild_menu(self) -> None:
        self.menu.clear()
        self.menu.addAction(self._texts["open"], self.toggle_panel)
        self._scenario_menu.clear()
        self._scenario_menu.setTitle(self._texts["scenarios"])
        for scenario in self._flow.scenarios:
            action = self._scenario_menu.addAction(scenario["name"])
            action.setCheckable(True)
            action.setChecked(scenario["id"] == self._flow.activeId)
            action.triggered.connect(lambda _checked=False, sid=scenario["id"]: self._flow.activate(sid))
        self._scenario_menu.setEnabled(bool(self._flow.scenarios))
        self.menu.addMenu(self._scenario_menu)
        self.menu.addSeparator()
        self.menu.addAction(self._texts["settings"], lambda: self._open_settings("monitor"))
        self.menu.addAction(self._texts["quit"], self._quit)
