from dataclasses import replace

from benq_monitor_control.core.session import ApplyResult
from benq_monitor_control.flow.runner import activate
from benq_monitor_control.flow.scenario import Action, ActionType, new_scenario
from benq_monitor_control.models.model import Feature


def scenario(*actions):
    return replace(new_scenario("Evening"), actions=tuple(actions))


class Recorder:
    def __init__(self, results=None, launch_ok=True):
        self.calls = []
        self.results = results or {}
        self.launch_ok = launch_ok

    def apply(self, feature, value):
        self.calls.append((feature, value))
        return self.results.get(feature, ApplyResult.APPLIED)

    def launch(self, desktop_id):
        self.calls.append(("launch", desktop_id))
        return self.launch_ok


def test_picture_mode_first_then_list_order():
    rec = Recorder()
    sc = scenario(
        Action(ActionType.BRIGHTNESS, 40),
        Action(ActionType.OPEN_APP, desktop_id="spotify.desktop"),
        Action(ActionType.PICTURE_MODE, 0x0F),
        Action(ActionType.LOW_BLUE_LIGHT, 3),
    )
    report = activate(sc, rec.apply, rec.launch, include_apps=True)
    assert rec.calls == [
        (Feature.PICTURE_MODE, 0x0F),
        (Feature.BRIGHTNESS, 40),
        ("launch", "spotify.desktop"),
        (Feature.LOW_BLUE_LIGHT, 3),
    ]
    assert report.skipped == ()
    assert report.name == "Evening"


def test_locked_action_is_skipped_rest_applies():
    rec = Recorder(results={Feature.LOW_BLUE_LIGHT: ApplyResult.LOCKED})
    sc = scenario(Action(ActionType.LOW_BLUE_LIGHT, 3), Action(ActionType.VOLUME, 10))
    report = activate(sc, rec.apply, rec.launch, include_apps=True)
    assert report.skipped == ((ActionType.LOW_BLUE_LIGHT, "locked"),)
    assert report.applied == (ActionType.VOLUME,)


def test_missing_app_is_skipped_and_others_apply():
    rec = Recorder(launch_ok=False)
    sc = scenario(Action(ActionType.OPEN_APP, desktop_id="gone.desktop"), Action(ActionType.BRIGHTNESS, 40))
    report = activate(sc, rec.apply, rec.launch, include_apps=True)
    assert report.skipped == ((ActionType.OPEN_APP, "launch_failed"),)
    assert report.applied == (ActionType.BRIGHTNESS,)


def test_apps_left_out_on_reapply():
    rec = Recorder()
    sc = scenario(Action(ActionType.OPEN_APP, desktop_id="spotify.desktop"), Action(ActionType.BRIGHTNESS, 40))
    report = activate(sc, rec.apply, rec.launch, include_apps=False)
    assert ("launch", "spotify.desktop") not in rec.calls
    assert report.skipped == () and report.applied == (ActionType.BRIGHTNESS,)
