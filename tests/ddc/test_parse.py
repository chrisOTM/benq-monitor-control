from pathlib import Path

from benq_monitor_control.ddc.parse import (
    DetectedDisplay,
    ErrorKind,
    VcpValue,
    classify_error,
    parse_detect_terse,
    parse_getvcp_terse,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "ddcutil-2026-10-13"


def test_parse_getvcp_snapshot_fixture():
    values = parse_getvcp_terse((FIXTURES / "snap0.txt").read_text())
    assert len(values) == 33
    assert values[0x10] == VcpValue(0x10, 65, 100)          # continuous
    assert values[0xDC] == VcpValue(0xDC, 0x0F, 255)        # simple NC
    assert values[0x60].current == 0x13
    assert values[0x62] == VcpValue(0x62, 20, 50)           # complex NC: x00 x32 x00 x14
    assert values[0xFD] == VcpValue(0xFD, 0, 0x0A04)        # 16-bit maximum
    assert values[0x81] == VcpValue(0x81, 0, 2)


def test_parse_getvcp_ignores_noise_and_errors():
    text = "VCP 10 C 50 100\nVCP 19 ERR\nsome warning\nVCP DC SNC x0a\n"
    assert parse_getvcp_terse(text) == {
        0x10: VcpValue(0x10, 50, 100),
        0xDC: VcpValue(0xDC, 0x0A, 255),
    }


def test_parse_detect_fixture_skips_invalid_display():
    displays = parse_detect_terse((FIXTURES / "detect.txt").read_text())
    assert displays == [
        DetectedDisplay(
            bus=15,
            connector="card0-DP-1",
            manufacturer="BNQ",
            model="BenQ MA320U",
            serial="SN0000000001",
        )
    ]


def test_parse_detect_empty():
    assert parse_detect_terse("No displays found.\n") == []


def test_classify_error():
    assert classify_error("Verification failed for feature fd\n    Try errors: DDCRC_VERIFY") is ErrorKind.VERIFY_FAILED
    assert classify_error("Unrecognized VCP feature code: 0x19") is ErrorKind.UNSUPPORTED_FEATURE
    assert classify_error("Open failed for /dev/i2c-15: errno=EACCES(13): Permission denied") is ErrorKind.PERMISSION
    assert classify_error("No monitor detected on bus /dev/i2c-15") is ErrorKind.NO_DISPLAY
    assert classify_error("DDC communication failed") is ErrorKind.NO_DISPLAY
    assert classify_error("something else") is ErrorKind.OTHER
