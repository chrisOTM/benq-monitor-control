from benq_monitor_control.core.session import ApplyResult, MonitorSession
from benq_monitor_control.ddc.backend import DdcUnavailable
from benq_monitor_control.ddc.fake import FakeBackend
from benq_monitor_control.models.ma320u import MA320U
from benq_monitor_control.models.model import Feature


def connected(fake=None):
    fake = fake or FakeBackend()
    session = MonitorSession(fake, MA320U)
    assert session.connect()
    return session, fake


def test_connect_reads_all_and_firmware():
    session, _ = connected()
    snap = session.snapshot()
    assert snap.reachable and snap.bus == 15
    assert snap.values[Feature.BRIGHTNESS] == 65
    assert snap.values[Feature.PICTURE_MODE] == 0x0F
    assert snap.maxima[Feature.VOLUME] == 50
    assert snap.maxima[Feature.LOW_BLUE_LIGHT] == 5
    assert snap.firmware == "1.2"
    assert snap.error is None


def test_connect_without_monitor():
    fake = FakeBackend()
    fake.present = False
    session = MonitorSession(fake, MA320U)
    assert not session.connect()
    assert not session.snapshot().reachable


def test_connect_unavailable_sets_error():
    fake = FakeBackend()
    fake.unavailable = DdcUnavailable("No permission for /dev/i2c-*", hint="add udev rule")
    session = MonitorSession(fake, MA320U)
    assert not session.connect()
    assert session.snapshot().error == "No permission for /dev/i2c-* — add udev rule"


def test_apply_brightness():
    session, fake = connected()
    assert session.apply(Feature.BRIGHTNESS, 40) is ApplyResult.APPLIED
    assert fake.value(0x10) == 40
    assert session.snapshot().values[Feature.BRIGHTNESS] == 40


def test_apply_invalid_values():
    session, fake = connected()
    assert session.apply(Feature.BRIGHTNESS, 101) is ApplyResult.INVALID
    assert session.apply(Feature.PICTURE_MODE, 0x23) is ApplyResult.INVALID
    assert session.apply(Feature.BRIGHTNESS_INTELLIGENCE, 2) is ApplyResult.INVALID
    assert session.apply(Feature.LOW_BLUE_LIGHT, 6) is ApplyResult.INVALID
    assert fake.writes == []


def test_rejection_learns_lock_for_current_mode_only():
    session, fake = connected(FakeBackend(rejects={(0x0F, 0x19)}))
    assert session.apply(Feature.LOW_BLUE_LIGHT, 3) is ApplyResult.REJECTED
    assert session.is_locked(Feature.LOW_BLUE_LIGHT)
    assert session.apply(Feature.LOW_BLUE_LIGHT, 3) is ApplyResult.LOCKED
    assert session.apply(Feature.PICTURE_MODE, 0x12) is ApplyResult.APPLIED
    assert not session.is_locked(Feature.LOW_BLUE_LIGHT)
    assert session.apply(Feature.LOW_BLUE_LIGHT, 3) is ApplyResult.APPLIED


def test_picture_mode_rejection_does_not_lock_picture_mode():
    session, _ = connected(FakeBackend(rejects={(0x0F, 0xDC)}))
    assert session.apply(Feature.PICTURE_MODE, 0x0A) is ApplyResult.REJECTED
    assert not session.is_locked(Feature.PICTURE_MODE)


def test_picture_mode_change_rereads_per_mode_values():
    session, _ = connected()
    assert session.apply(Feature.PICTURE_MODE, 0x0A) is ApplyResult.APPLIED
    snap = session.snapshot()
    assert snap.values[Feature.PICTURE_MODE] == 0x0A
    assert snap.values[Feature.BRIGHTNESS] == 38


def test_input_switch_writes_without_verify_and_marks_unreachable():
    session, fake = connected()
    assert session.apply(Feature.INPUT_SOURCE, 0x11) is ApplyResult.APPLIED
    assert fake.verify_flags == [False]
    assert not session.reachable


def test_unreachable_then_reconnect():
    session, fake = connected()
    fake.reachable = False
    assert session.apply(Feature.BRIGHTNESS, 10) is ApplyResult.UNREACHABLE
    assert not session.reachable
    assert session.apply(Feature.BRIGHTNESS, 10) is ApplyResult.UNREACHABLE
    fake.reachable = True
    assert session.connect()


def test_hdr_state_locks_features():
    session, fake = connected()
    fake.external_set(0xDC, 0x23)
    session.read_polled()
    snap = session.snapshot()
    assert snap.hdr_active
    assert snap.locked[Feature.BRIGHTNESS] and snap.locked[Feature.PICTURE_MODE]
    assert not snap.locked[Feature.VOLUME]
    assert session.apply(Feature.BRIGHTNESS, 10) is ApplyResult.LOCKED
