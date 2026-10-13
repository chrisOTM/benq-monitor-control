import pytest

from benq_monitor_control.ddc.backend import DdcUnavailable, MonitorHandle, Unreachable, WriteRejected
from benq_monitor_control.ddc.fake import FakeBackend


def test_detect_matches_model():
    fake = FakeBackend()
    assert fake.detect("BenQ MA320U") == MonitorHandle(15, "BenQ MA320U", "FAKE0001")
    assert fake.detect("Other") is None
    fake.present = False
    assert fake.detect("BenQ MA320U") is None


def test_read_returns_requested_known_codes():
    fake = FakeBackend()
    handle = fake.detect("BenQ MA320U")
    values = fake.read(handle, [0x10, 0xDC, 0x99])
    assert set(values) == {0x10, 0xDC}
    assert values[0x10].current == 65 and values[0x10].maximum == 100


def test_write_and_reject_per_mode():
    fake = FakeBackend()
    handle = fake.detect("BenQ MA320U")
    fake.write(handle, 0x10, 40)
    assert fake.value(0x10) == 40
    with pytest.raises(WriteRejected):
        fake.write(handle, 0x72, 0x50)  # gamma is locked in M-Book (0x0F)
    assert fake.writes == [(0x10, 40)]


def test_mode_switch_restores_per_mode_values():
    fake = FakeBackend()
    handle = fake.detect("BenQ MA320U")
    fake.write(handle, 0xDC, 0x0A)   # sRGB: brightness 38 as observed live
    assert fake.value(0x10) == 38
    fake.write(handle, 0xDC, 0x0F)   # back to M-Book: brightness 65 again
    assert fake.value(0x10) == 65
    with pytest.raises(WriteRejected):
        fake.write(handle, 0xDC, 0x23)  # HDR cannot be selected without HDR signal


def test_unreachable_and_unavailable():
    fake = FakeBackend()
    handle = fake.detect("BenQ MA320U")
    fake.reachable = False
    with pytest.raises(Unreachable):
        fake.read(handle, [0x10])
    fake.unavailable = DdcUnavailable("No permission", hint="fix it")
    with pytest.raises(DdcUnavailable):
        fake.detect("BenQ MA320U")
    assert str(fake.unavailable) == "No permission — fix it"


def test_verify_flag_is_recorded():
    fake = FakeBackend()
    handle = fake.detect("BenQ MA320U")
    fake.write(handle, 0x60, 0x11, verify=False)
    assert fake.verify_flags == [False]
