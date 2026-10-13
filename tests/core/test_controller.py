import pytest

from benq_monitor_control.core.controller import MonitorController
from benq_monitor_control.core.executor import ImmediateExecutor
from benq_monitor_control.core.session import MonitorSession
from benq_monitor_control.ddc.backend import DdcUnavailable
from benq_monitor_control.ddc.fake import FakeBackend
from benq_monitor_control.models.ma320u import MA320U


class Clock:
    def __init__(self) -> None:
        self.t = 100.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


@pytest.fixture
def make(qapp):
    def _make(fake=None):
        fake = fake or FakeBackend()
        clock = Clock()
        controller = MonitorController(MonitorSession(fake, MA320U), ImmediateExecutor(), clock=clock)
        failures = []
        controller.writeFailed.connect(lambda f, r: failures.append((f, r)))
        controller.start()
        return controller, fake, clock, failures

    return _make


def test_start_connects_and_publishes(make):
    c, _, _, _ = make()
    assert c.reachable
    assert c.brightness == 65 and c.pictureMode == 0x0F and c.volume == 20
    assert c.bus == 15 and c.firmware == "1.2"
    assert c.maxima["volume"] == 50
    assert c.pictureModes[0] == {"value": 0x0F, "label": "Tux-Book"}
    assert c.displayName == "BenQ MA320U"


def test_set_value_is_coalesced(make):
    c, fake, _, _ = make()
    states = []
    c.stateChanged.connect(lambda: states.append(c.brightness))
    for v in (10, 20, 30):
        c.setValue("brightness", v)
    c.tick_flush()
    assert fake.writes == [(0x10, 30)]
    assert c.brightness == 30 and states[-1] == 30


def test_flush_respects_interval(make):
    c, fake, clock, _ = make()
    c.setValue("brightness", 10)
    c.tick_flush()
    c.setValue("brightness", 20)
    c.tick_flush()
    assert fake.writes == [(0x10, 10)]
    clock.advance(0.2)
    c.tick_flush()
    assert fake.writes == [(0x10, 10), (0x10, 20)]


def test_rejected_write_emits_and_reverts(make):
    c, _, _, failures = make(FakeBackend(rejects={(0x0F, 0x19)}))
    c.setValue("low_blue_light", 3)
    c.tick_flush()
    assert failures == [("low_blue_light", "rejected")]
    assert c.lowBlueLight == 0
    assert c.locked["low_blue_light"] is True


def test_poll_paused_during_drag_and_quiet_period(make):
    c, fake, clock, _ = make()
    clock.advance(10)
    fake.external_set(0x10, 40)
    c.beginDrag("brightness")
    c.tick_poll()
    assert c.brightness == 65
    c.endDrag("brightness")
    c.tick_poll()
    assert c.brightness == 65  # quiet period after the drag
    clock.advance(2.1)
    c.tick_poll()
    assert c.brightness == 40


def test_unreachable_mid_drag_then_reconnects(make):
    c, fake, clock, failures = make()
    c.beginDrag("brightness")
    c.setValue("brightness", 30)
    fake.reachable = False
    c.tick_flush()
    c.endDrag("brightness")
    assert not c.reachable
    assert failures == [("brightness", "unreachable")]
    clock.advance(5)
    fake.reachable = True
    c.tick_poll()
    assert not c.reachable  # retry interval (10 s) not yet over
    clock.advance(6)
    c.tick_poll()
    assert c.reachable and c.brightness == 65


def test_hdr_state_is_published(make):
    c, fake, clock, _ = make()
    fake.external_set(0xDC, 0x23)
    clock.advance(3)
    c.tick_poll()
    assert c.hdrActive
    assert c.locked["brightness"] is True


def test_picture_mode_change_rereads_values(make):
    c, _, _, _ = make()
    c.setValue("picture_mode", 0x0A)
    c.tick_flush()
    assert c.pictureMode == 0x0A and c.brightness == 38


def test_unavailable_shows_error_text(make):
    fake = FakeBackend()
    fake.unavailable = DdcUnavailable("No permission for /dev/i2c-*", hint="add the udev rule")
    c, _, _, _ = make(fake)
    assert not c.reachable
    assert "No permission" in c.errorText


def test_run_job_delivers_result_and_publishes(make):
    c, fake, _, _ = make()
    results = []
    c.run_job(lambda s: s.snapshot().values, results.append)
    assert results and results[0]
    fake.external_set(0x62, 30)
    c.refresh()
    assert c.volume == 30


def test_pending_value_is_shown_until_written(make):
    c, fake, _, _ = make()
    c.setValue("brightness", 30)
    assert c.brightness == 30  # the slider must not jump back before the write lands
    c.tick_flush()
    assert c.brightness == 30 and fake.value(0x10) == 30


def test_failed_write_reverts_displayed_value(make):
    c, _, _, _ = make(FakeBackend(rejects={(0x0F, 0x19)}))
    seen = []
    c.stateChanged.connect(lambda: seen.append(c.lowBlueLight))
    c.setValue("low_blue_light", 3)
    assert c.lowBlueLight == 3
    c.tick_flush()
    assert c.lowBlueLight == 0 and seen[-1] == 0


def test_dragged_value_survives_intermediate_snapshots(make):
    c, _, _, _ = make()
    c.beginDrag("brightness")
    c.setValue("brightness", 10)
    c.tick_flush()
    c.setValue("brightness", 20)  # pending: the throttle interval is not over yet
    c.refresh()  # another job publishes a snapshot that still says 10
    assert c.brightness == 20


def test_unreachable_clears_a_stuck_drag(make):
    c, fake, clock, _ = make()
    c.beginDrag("brightness")  # the release never arrives
    fake.reachable = False
    clock.advance(6)
    c.refresh()
    fake.reachable = True
    clock.advance(11)
    c.tick_poll()
    assert c.reachable


def test_cancel_drags_resumes_polling(make):
    c, fake, clock, _ = make()
    c.beginDrag("brightness")
    c.cancelDrags()
    clock.advance(3)
    fake.external_set(0x10, 40)
    c.tick_poll()
    assert c.brightness == 40
