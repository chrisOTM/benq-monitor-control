from datetime import time

import pytest

from benq_monitor_control.flow.scenario import (
    Action,
    ActionType,
    Schedule,
    ScheduleKind,
    new_scenario,
    scenario_from_dict,
    scenario_to_dict,
)

EVENING = {
    "id": "6f1c2b9e-4d0a-4c55-9a39-0b7e2f61d2a4",
    "name": "Evening",
    "notify": True,
    "schedule": {"kind": "sunset", "offset_min": 0},
    "actions": [
        {"type": "picture_mode", "value": 15},
        {"type": "brightness", "value": 40},
        {"type": "low_blue_light", "value": 3},
        {"type": "open_app", "desktop_id": "spotify.desktop"},
    ],
}


def test_round_trip_spec_example():
    scenario = scenario_from_dict(EVENING)
    assert scenario.schedule == Schedule(ScheduleKind.SUNSET, None, 0)
    assert scenario.actions[3] == Action(ActionType.OPEN_APP, desktop_id="spotify.desktop")
    assert scenario_to_dict(scenario) == EVENING


def test_time_schedule_round_trip():
    data = {**EVENING, "schedule": {"kind": "time", "at": "07:05", "offset_min": -10}}
    scenario = scenario_from_dict(data)
    assert scenario.schedule.at == time(7, 5)
    assert scenario_to_dict(scenario)["schedule"] == {"kind": "time", "at": "07:05", "offset_min": -10}


def test_new_scenario_has_uuid_and_defaults():
    s = new_scenario("Day")
    assert len(s.id) == 36 and s.name == "Day" and s.notify and s.actions == ()
    assert s.schedule.kind is ScheduleKind.MANUAL


@pytest.mark.parametrize(
    "patch, message",
    [
        ({"name": "  "}, "name"),
        ({"id": ""}, "id"),
        ({"notify": "yes"}, "notify"),
        ({"schedule": {"kind": "weekly"}}, "schedule kind"),
        ({"schedule": {"kind": "time"}}, "at"),
        ({"schedule": {"kind": "time", "at": "25:00"}}, "HH:MM"),
        ({"schedule": {"kind": "sunset", "offset_min": 121}}, "offset_min"),
        ({"actions": [{"type": "explode"}]}, "action type"),
        ({"actions": [{"type": "brightness"}]}, "integer"),
        ({"actions": [{"type": "brightness", "value": True}]}, "integer"),
        ({"actions": [{"type": "open_app", "desktop_id": "spotify"}]}, ".desktop"),
        ({"actions": "nope"}, "list"),
    ],
)
def test_validation_errors(patch, message):
    with pytest.raises(ValueError, match=message):
        scenario_from_dict({**EVENING, **patch})
