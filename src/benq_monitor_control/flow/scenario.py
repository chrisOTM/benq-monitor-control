"""FloW scenarios: named action lists with an optional daily schedule."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import StrEnum
from typing import Any

from ..models.model import Feature

MAX_OFFSET_MIN = 120


class ActionType(StrEnum):
    PICTURE_MODE = "picture_mode"
    BRIGHTNESS = "brightness"
    VOLUME = "volume"
    LOW_BLUE_LIGHT = "low_blue_light"
    BRIGHTNESS_INTELLIGENCE = "brightness_intelligence"
    OPEN_APP = "open_app"


ACTION_FEATURE: dict[ActionType, Feature] = {
    ActionType.PICTURE_MODE: Feature.PICTURE_MODE,
    ActionType.BRIGHTNESS: Feature.BRIGHTNESS,
    ActionType.VOLUME: Feature.VOLUME,
    ActionType.LOW_BLUE_LIGHT: Feature.LOW_BLUE_LIGHT,
    ActionType.BRIGHTNESS_INTELLIGENCE: Feature.BRIGHTNESS_INTELLIGENCE,
}


class ScheduleKind(StrEnum):
    MANUAL = "manual"
    TIME = "time"
    SUNRISE = "sunrise"
    SUNSET = "sunset"


@dataclass(frozen=True)
class Action:
    type: ActionType
    value: int | None = None
    desktop_id: str | None = None


@dataclass(frozen=True)
class Schedule:
    kind: ScheduleKind = ScheduleKind.MANUAL
    at: time | None = None
    offset_min: int = 0


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    notify: bool = True
    schedule: Schedule = field(default_factory=Schedule)
    actions: tuple[Action, ...] = ()


def new_scenario(name: str) -> Scenario:
    return Scenario(id=str(uuid.uuid4()), name=name)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def action_to_dict(action: Action) -> dict[str, Any]:
    if action.type is ActionType.OPEN_APP:
        return {"type": action.type.value, "desktop_id": action.desktop_id}
    return {"type": action.type.value, "value": action.value}


def action_from_dict(data: Any) -> Action:
    _require(isinstance(data, dict), "each action must be an object")
    try:
        kind = ActionType(data.get("type"))
    except ValueError:
        raise ValueError(f"unknown action type: {data.get('type')!r}") from None
    if kind is ActionType.OPEN_APP:
        desktop_id = data.get("desktop_id")
        _require(
            isinstance(desktop_id, str) and desktop_id.endswith(".desktop"),
            "open_app needs a desktop_id ending in .desktop",
        )
        return Action(kind, desktop_id=desktop_id)
    value = data.get("value")
    _require(_is_int(value), f"{kind.value} needs an integer value")
    return Action(kind, value=value)


def schedule_to_dict(schedule: Schedule) -> dict[str, Any]:
    data: dict[str, Any] = {"kind": schedule.kind.value}
    if schedule.at is not None:
        data["at"] = schedule.at.strftime("%H:%M")
    data["offset_min"] = schedule.offset_min
    return data


def schedule_from_dict(data: Any) -> Schedule:
    _require(isinstance(data, dict), "schedule must be an object")
    try:
        kind = ScheduleKind(data.get("kind", "manual"))
    except ValueError:
        raise ValueError(f"unknown schedule kind: {data.get('kind')!r}") from None
    offset = data.get("offset_min", 0)
    _require(
        _is_int(offset) and -MAX_OFFSET_MIN <= offset <= MAX_OFFSET_MIN,
        f"offset_min must be between -{MAX_OFFSET_MIN} and {MAX_OFFSET_MIN}",
    )
    at = None
    if kind is ScheduleKind.TIME:
        raw = data.get("at")
        _require(isinstance(raw, str), "a time schedule needs 'at'")
        try:
            at = datetime.strptime(raw, "%H:%M").time()
        except ValueError:
            raise ValueError(f"'at' must be HH:MM, got {raw!r}") from None
    return Schedule(kind, at, offset)


def scenario_to_dict(scenario: Scenario) -> dict[str, Any]:
    return {
        "id": scenario.id,
        "name": scenario.name,
        "notify": scenario.notify,
        "schedule": schedule_to_dict(scenario.schedule),
        "actions": [action_to_dict(a) for a in scenario.actions],
    }


def scenario_from_dict(data: Any) -> Scenario:
    _require(isinstance(data, dict), "a scenario must be an object")
    scenario_id = data.get("id")
    _require(isinstance(scenario_id, str) and scenario_id != "", "a scenario needs an id")
    name = data.get("name")
    _require(isinstance(name, str) and name.strip() != "", "a scenario needs a name")
    notify = data.get("notify", True)
    _require(isinstance(notify, bool), "notify must be true or false")
    actions = data.get("actions", [])
    _require(isinstance(actions, list), "actions must be a list")
    return Scenario(
        id=scenario_id,
        name=name.strip(),
        notify=notify,
        schedule=schedule_from_dict(data.get("schedule") or {}),
        actions=tuple(action_from_dict(a) for a in actions),
    )
