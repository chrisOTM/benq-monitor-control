"""Live round-trip on a real MA320U. Run: .venv/bin/pytest -m hardware -s tests/hardware"""

import pytest

from benq_monitor_control.core.session import ApplyResult, MonitorSession
from benq_monitor_control.ddc.ddcutil_cli import DdcutilCli
from benq_monitor_control.models.ma320u import MA320U
from benq_monitor_control.models.model import Feature

pytestmark = pytest.mark.hardware

SDR_MODES = (0x0F, 0x0A, 0x22, 0x32, 0x28, 0x12)
COMPARED_CODES = (0xDC, 0x10, 0x62, 0x60, 0x19, 0x81, 0x14, 0x5F, 0x87)


@pytest.fixture(scope="module")
def session():
    s = MonitorSession(DdcutilCli(), MA320U)
    assert s.connect(), "MA320U not reachable — switch the monitor to this computer's input"
    return s


def current(session):
    raw = session.backend.read(session.handle, COMPARED_CODES)
    return {code: value.current for code, value in raw.items()}


def test_detect_and_read(session):
    snap = session.snapshot()
    assert snap.reachable
    for feature in Feature:
        assert feature in snap.values, feature


def test_round_trip_in_every_sdr_mode(session):
    before = current(session)
    original_mode = session.mode
    report = {}
    try:
        for mode in SDR_MODES:
            assert session.apply(Feature.PICTURE_MODE, mode) is ApplyResult.APPLIED, hex(mode)
            for feature in (Feature.BRIGHTNESS, Feature.VOLUME, Feature.LOW_BLUE_LIGHT, Feature.BRIGHTNESS_INTELLIGENCE):
                value = session.snapshot().values[feature]
                if feature in (Feature.LOW_BLUE_LIGHT, Feature.BRIGHTNESS_INTELLIGENCE):
                    probe = 0 if value else 1
                else:
                    probe = value - 1 if value > 0 else value + 1
                result = session.apply(feature, probe)
                report[(hex(mode), feature.value)] = result.value
                if result is ApplyResult.APPLIED:
                    assert session.apply(feature, value) is ApplyResult.APPLIED
    finally:
        session.apply(Feature.PICTURE_MODE, original_mode)
    for key, value in sorted(report.items()):
        print(key, value)
    assert current(session) == before
    assert set(report.values()) <= {"applied", "rejected"}
