"""QObject bridge for FloW: scenario editing, activation and scheduling."""

import json
import logging
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from PySide6.QtCore import SLOT, Property, QObject, QTimer, Signal, Slot

from ..desktop import apps as desktop_apps
from .clock import ClockWatch
from .runner import ActivationReport
from .runner import activate as run_activation
from .scenario import Scenario, new_scenario, scenario_from_dict, scenario_to_dict
from .scheduler import active_at, local_zone, next_start, to_utc
from .store import ScenarioStore
from .sun import Location, sun_times

log = logging.getLogger(__name__)


class FlowService(QObject):
    scenariosChanged = Signal()
    activeChanged = Signal()
    activated = Signal(str, int)
    editError = Signal(str)

    def __init__(
        self,
        store: ScenarioStore,
        controller: Any,
        location: Callable[[], Location | None],
        *,
        launch: Callable[[str], bool] = desktop_apps.launch,
        list_apps: Callable[[], list[desktop_apps.AppEntry]] = desktop_apps.list_apps,
        now: Callable[[], datetime] | None = None,
        wall: Callable[[], float] = time.time,
        mono: Callable[[], float] = time.monotonic,
        tick_interval_s: int = 60,
        logind: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._controller = controller
        self._location = location
        self._launch = launch
        self._list_apps = list_apps
        self._now = now or (lambda: datetime.now(local_zone()))
        self._wall = wall
        self._mono = mono
        self._use_logind = logind
        self._scenarios: list[Scenario] = store.load()
        self._active_id = ""
        self._next: tuple[datetime, Scenario] | None = None
        self._apps_cache: list[dict[str, str]] | None = None
        self._retry_id = ""  # scenario to re-apply once the monitor answers again
        if hasattr(controller, "stateChanged"):
            controller.stateChanged.connect(self._on_monitor_state)
        self._clock = ClockWatch()
        self._timer = QTimer(self)
        self._timer.setInterval(tick_interval_s * 1000)
        self._timer.timeout.connect(self.tick)

    # --- lifecycle -------------------------------------------------------
    def start(self) -> None:
        self._clock.tick(self._wall(), self._mono())
        self.reapply_current()
        self._plan_next()
        self._timer.start()
        if self._use_logind:
            self._connect_logind()

    @Slot()
    def tick(self) -> None:
        if self._clock.tick(self._wall(), self._mono()):
            log.info("clock jump detected; re-applying the current scenario")
            self.reapply_current()
            self._plan_next()
            return
        if self._next is not None and to_utc(self._now()) >= to_utc(self._next[0]):
            scenario = self._next[1]
            self._activate(scenario, include_apps=True, notify=True)
            self._plan_next()

    def reapply_current(self) -> None:
        scenario = active_at(self._scenarios, self._now(), self._location())
        if scenario is not None:
            self._activate(scenario, include_apps=False, notify=False)

    def replan(self) -> None:
        self._plan_next()

    # --- QML slots -------------------------------------------------------
    @Slot(str)
    def activate(self, scenario_id: str) -> None:
        scenario = self._find(scenario_id)
        if scenario is not None:
            self._activate(scenario, include_apps=True, notify=True)

    @Slot(str, result=str)
    def create(self, name: str) -> str:
        scenario = new_scenario(name.strip() or "Scenario")
        self._scenarios.append(scenario)
        self._save()
        return scenario.id

    @Slot(str)
    def update(self, json_text: str) -> None:
        try:
            scenario = scenario_from_dict(json.loads(json_text))
        except ValueError as exc:  # includes json.JSONDecodeError
            self.editError.emit(str(exc))
            return
        index = self._index(scenario.id)
        if index is None:
            self.editError.emit(f"unknown scenario {scenario.id}")
            return
        self._scenarios[index] = scenario
        self._save()

    @Slot(str)
    def remove(self, scenario_id: str) -> None:
        index = self._index(scenario_id)
        if index is None:
            return
        del self._scenarios[index]
        if self._active_id == scenario_id:
            self._active_id = ""
        self._save()

    @Slot(str, int)
    def move(self, scenario_id: str, new_index: int) -> None:
        index = self._index(scenario_id)
        if index is None:
            return
        scenario = self._scenarios.pop(index)
        self._scenarios.insert(max(0, min(new_index, len(self._scenarios))), scenario)
        self._save()

    @Slot()
    def refreshApps(self) -> None:
        self._apps_cache = None
        self.scenariosChanged.emit()

    @Slot(bool)
    def onPrepareForSleep(self, sleeping: bool) -> None:
        if not sleeping:
            self.reapply_current()
            self._plan_next()

    # --- internals -------------------------------------------------------
    def _activate(self, scenario: Scenario, *, include_apps: bool, notify: bool) -> None:
        self._active_id = scenario.id
        self.activeChanged.emit()
        launch = self._launch
        self._controller.run_job(
            lambda session: run_activation(scenario, session.apply, launch, include_apps=include_apps),
            lambda report: self._after_activation(scenario, report, notify),
        )

    def _after_activation(self, scenario: Scenario, report: ActivationReport | None, notify: bool) -> None:
        if report is None:
            return
        if any(reason == "unreachable" for _, reason in report.skipped):
            self._retry_id = scenario.id
        if report.skipped:
            log.info("scenario %s skipped %s", scenario.name, report.skipped)
        if notify and scenario.notify:
            self.activated.emit(scenario.name, len(report.skipped))

    def _on_monitor_state(self) -> None:
        if not self._retry_id or not self._controller.reachable:
            return
        scenario = self._find(self._retry_id)
        self._retry_id = ""
        if scenario is not None:
            self._activate(scenario, include_apps=False, notify=False)

    def _plan_next(self) -> None:
        self._next = next_start(self._scenarios, self._now(), self._location())
        self.activeChanged.emit()

    def _save(self) -> None:
        self._store.save(self._scenarios)
        self._plan_next()
        self.scenariosChanged.emit()

    def _find(self, scenario_id: str) -> Scenario | None:
        index = self._index(scenario_id)
        return self._scenarios[index] if index is not None else None

    def _index(self, scenario_id: str) -> int | None:
        for i, scenario in enumerate(self._scenarios):
            if scenario.id == scenario_id:
                return i
        return None

    def _connect_logind(self) -> None:
        from PySide6.QtDBus import QDBusConnection

        bus = QDBusConnection.systemBus()
        ok = bus.isConnected() and bus.connect(
            "org.freedesktop.login1",
            "/org/freedesktop/login1",
            "org.freedesktop.login1.Manager",
            "PrepareForSleep",
            self,
            SLOT("onPrepareForSleep(bool)"),
        )
        if not ok:
            log.info("logind PrepareForSleep unavailable; relying on clock-jump detection")

    # --- QML properties --------------------------------------------------
    def _get_scenarios(self) -> list[dict[str, Any]]:
        return [scenario_to_dict(s) for s in self._scenarios]

    def _get_apps(self) -> list[dict[str, str]]:
        if self._apps_cache is None:
            self._apps_cache = [{"desktop_id": a.desktop_id, "name": a.name} for a in self._list_apps()]
        return self._apps_cache

    def _get_active_id(self) -> str:
        return self._active_id

    def _get_active_name(self) -> str:
        scenario = self._find(self._active_id)
        return scenario.name if scenario else ""

    def _get_active_until(self) -> str:
        return self._next[0].strftime("%H:%M") if self._next else ""

    def _get_sun_today(self) -> dict[str, Any]:
        location = self._location()
        if location is None:
            return {"available": False, "sunrise": "", "sunset": ""}
        now = self._now()
        sun = sun_times(now.date(), location.latitude, location.longitude, now.tzinfo)
        if sun.sunrise is None:
            return {"available": False, "sunrise": "", "sunset": ""}
        return {"available": True, "sunrise": sun.sunrise.strftime("%H:%M"), "sunset": sun.sunset.strftime("%H:%M")}

    scenarios = Property("QVariantList", _get_scenarios, notify=scenariosChanged)
    apps = Property("QVariantList", _get_apps, notify=scenariosChanged)
    activeId = Property(str, _get_active_id, notify=activeChanged)
    activeName = Property(str, _get_active_name, notify=activeChanged)
    activeUntil = Property(str, _get_active_until, notify=activeChanged)
    sunToday = Property("QVariantMap", _get_sun_today, notify=activeChanged)
