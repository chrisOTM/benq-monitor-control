import json
from dataclasses import replace
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pytest

from benq_monitor_control.core.controller import MonitorController
from benq_monitor_control.core.executor import ImmediateExecutor
from benq_monitor_control.core.session import MonitorSession
from benq_monitor_control.ddc.fake import FakeBackend
from benq_monitor_control.flow.scenario import Action, ActionType, Schedule, ScheduleKind, new_scenario
from benq_monitor_control.flow.service import FlowService
from benq_monitor_control.flow.store import ScenarioStore
from benq_monitor_control.models.ma320u import MA320U

TZ = ZoneInfo("Europe/Berlin")


class Clocks:
    def __init__(self):
        self.now = datetime(2026, 10, 13, 12, 0, tzinfo=TZ)
        self.wall = 1_000_000.0
        self.mono = 500.0

    def advance(self, seconds, suspended=False):
        from datetime import timedelta

        self.now += timedelta(seconds=seconds)
        self.wall += seconds
        if not suspended:
            self.mono += seconds


def timed(name, hh, mm, *actions, notify=True):
    return replace(
        new_scenario(name),
        notify=notify,
        schedule=Schedule(ScheduleKind.TIME, time(hh, mm), 0),
        actions=tuple(actions),
    )


@pytest.fixture
def env(qapp, tmp_path):
    def _env(scenarios):
        fake = FakeBackend()
        controller = MonitorController(MonitorSession(fake, MA320U), ImmediateExecutor())
        controller.start()
        store = ScenarioStore(tmp_path / "scenarios.json")
        store.save(scenarios)
        clocks = Clocks()
        launched, notes = [], []
        service = FlowService(
            store,
            controller,
            lambda: None,
            launch=lambda desktop_id: launched.append(desktop_id) or True,
            list_apps=lambda: [],
            now=lambda: clocks.now,
            wall=lambda: clocks.wall,
            mono=lambda: clocks.mono,
            logind=False,
        )
        service.activated.connect(lambda name, skipped: notes.append((name, skipped)))
        return service, fake, clocks, launched, notes

    return _env


DAY = timed("Day", 7, 0, Action(ActionType.BRIGHTNESS, 70))
EVENING = timed(
    "Evening", 20, 0,
    Action(ActionType.BRIGHTNESS, 30),
    Action(ActionType.OPEN_APP, desktop_id="spotify.desktop"),
)


def test_start_reapplies_current_without_apps_or_notification(env):
    service, fake, _, launched, notes = env([DAY, EVENING])
    service.start()
    assert fake.value(0x10) == 70
    assert service.activeId == DAY.id and service.activeName == "Day"
    assert service.activeUntil == "20:00"
    assert launched == [] and notes == []


def test_scheduled_start_fires_with_apps_and_notification(env):
    service, fake, clocks, launched, notes = env([DAY, EVENING])
    service.start()
    clocks.advance(8 * 3600)  # 20:00
    service.tick()
    assert fake.value(0x10) == 30
    assert launched == ["spotify.desktop"]
    assert notes == [("Evening", 0)]
    assert service.activeUntil == "07:00"


def test_clock_jump_reapplies_without_apps_or_notification(env):
    service, fake, clocks, launched, notes = env([DAY, EVENING])
    service.start()
    clocks.advance(20 * 3600, suspended=True)  # resume next day 08:00, past Evening and Day
    fake.external_set(0x10, 5)
    service.tick()
    assert fake.value(0x10) == 70
    assert launched == [] and notes == []
    assert service.activeName == "Day"


def test_manual_activation(env):
    cinema = replace(new_scenario("Cinema"), actions=(Action(ActionType.PICTURE_MODE, 0x32),))
    service, fake, _, _, notes = env([DAY, cinema])
    service.start()
    service.activate(cinema.id)
    assert fake.value(0xDC) == 0x32
    assert service.activeId == cinema.id
    assert notes == [("Cinema", 0)]


def test_notification_reports_skipped_actions(env):
    sc = replace(new_scenario("Night"), actions=(Action(ActionType.BRIGHTNESS, 500),))
    service, _, _, _, notes = env([sc])
    service.start()
    service.activate(sc.id)
    assert notes == [("Night", 1)]


def test_notify_false_is_silent(env):
    sc = replace(new_scenario("Quiet"), notify=False, actions=(Action(ActionType.BRIGHTNESS, 10),))
    service, _, _, _, notes = env([sc])
    service.start()
    service.activate(sc.id)
    assert notes == []


def test_create_update_move_remove_persist(env, tmp_path):
    service, _, _, _, _ = env([])
    new_id = service.create("Focus")
    assert [s["name"] for s in service.scenarios] == ["Focus"]
    data = dict(service.scenarios[0])
    data["name"] = "Deep focus"
    data["actions"] = [{"type": "volume", "value": 0}]
    service.update(json.dumps(data))
    other = service.create("Other")
    service.move(other, 0)
    assert [s["name"] for s in service.scenarios] == ["Other", "Deep focus"]
    stored = json.loads((tmp_path / "scenarios.json").read_text())
    assert [s["name"] for s in stored["scenarios"]] == ["Other", "Deep focus"]
    service.remove(new_id)
    assert [s["name"] for s in service.scenarios] == ["Other"]


def test_invalid_update_emits_edit_error(env):
    service, _, _, _, _ = env([DAY])
    errors = []
    service.editError.connect(errors.append)
    bad = dict(service.scenarios[0], name="")
    service.update(json.dumps(bad))
    assert errors and "name" in errors[0]
    assert service.scenarios[0]["name"] == "Day"


def test_sun_today_without_location(env):
    service, _, _, _, _ = env([])
    assert service.sunToday == {"available": False, "sunrise": "", "sunset": ""}


def test_reapply_is_retried_when_the_monitor_comes_back(env):
    service, fake, _, launched, notes = env([DAY, EVENING])
    fake.reachable = False
    service.start()  # monitor still waking up / on another input
    assert fake.value(0x10) == 65
    fake.reachable = True
    service._controller.redetect()
    assert fake.value(0x10) == 70
    assert launched == [] and notes == []
