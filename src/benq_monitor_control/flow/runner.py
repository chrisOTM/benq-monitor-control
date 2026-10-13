"""Apply a scenario's actions in the order the spec defines (§7.2)."""

from collections.abc import Callable
from dataclasses import dataclass

from ..core.session import ApplyResult
from ..models.model import Feature
from .scenario import ACTION_FEATURE, ActionType, Scenario

ApplyFn = Callable[[Feature, int], ApplyResult]
LaunchFn = Callable[[str], bool]


@dataclass(frozen=True)
class ActivationReport:
    scenario_id: str
    name: str
    applied: tuple[ActionType, ...]
    skipped: tuple[tuple[ActionType, str], ...]


def activate(scenario: Scenario, apply: ApplyFn, launch: LaunchFn, *, include_apps: bool) -> ActivationReport:
    applied: list[ActionType] = []
    skipped: list[tuple[ActionType, str]] = []
    # Picture mode first: it changes which settings the monitor accepts. sorted() is stable.
    ordered = sorted(scenario.actions, key=lambda a: a.type is not ActionType.PICTURE_MODE)
    for action in ordered:
        if action.type is ActionType.OPEN_APP:
            if not include_apps:
                continue
            if launch(action.desktop_id):
                applied.append(action.type)
            else:
                skipped.append((action.type, "launch_failed"))
            continue
        result = apply(ACTION_FEATURE[action.type], action.value)
        if result is ApplyResult.APPLIED:
            applied.append(action.type)
        else:
            skipped.append((action.type, result.value))
    return ActivationReport(scenario.id, scenario.name, tuple(applied), tuple(skipped))
