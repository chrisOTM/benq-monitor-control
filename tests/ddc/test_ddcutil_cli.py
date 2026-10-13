from pathlib import Path

import pytest

from benq_monitor_control.ddc.backend import DdcUnavailable, MonitorHandle, Unreachable, WriteRejected
from benq_monitor_control.ddc.ddcutil_cli import TIMEOUT_RC, DdcutilCli, RunResult, subprocess_runner

FIXTURES = Path(__file__).parents[1] / "fixtures" / "ddcutil-2026-10-13"
HANDLE = MonitorHandle(15, "BenQ MA320U", "SN0000000001")


class FakeRunner:
    def __init__(self, *results: RunResult) -> None:
        self.results = list(results)
        self.calls: list[list[str]] = []

    def __call__(self, args, timeout):
        self.calls.append(list(args))
        return self.results.pop(0)


def test_detect_finds_model():
    runner = FakeRunner(RunResult(0, (FIXTURES / "detect.txt").read_text()))
    assert DdcutilCli(runner).detect("BenQ MA320U") == HANDLE
    assert runner.calls == [["ddcutil", "detect", "--terse"]]


def test_detect_other_model_returns_none():
    runner = FakeRunner(RunResult(0, (FIXTURES / "detect.txt").read_text()))
    assert DdcutilCli(runner).detect("BenQ RD280U") is None


def test_detect_permission_problem():
    runner = FakeRunner(RunResult(1, "Open failed for /dev/i2c-15: errno=EACCES(13): Permission denied"))
    with pytest.raises(DdcUnavailable):
        DdcutilCli(runner).detect("BenQ MA320U")


def test_read_builds_command_and_parses():
    runner = FakeRunner(RunResult(0, "VCP 10 C 65 100\nVCP DC SNC x0f\n"))
    values = DdcutilCli(runner).read(HANDLE, [0x10, 0xDC])
    assert runner.calls == [["ddcutil", "--bus", "15", "--terse", "getvcp", "10", "DC"]]
    assert values[0x10].current == 65 and values[0xDC].current == 0x0F


def test_read_without_values_is_unreachable():
    runner = FakeRunner(RunResult(1, "No monitor detected on bus /dev/i2c-15"))
    with pytest.raises(Unreachable):
        DdcutilCli(runner).read(HANDLE, [0x10])


def test_read_permission_denied_is_unavailable():
    runner = FakeRunner(RunResult(1, "errno=EACCES(13): Permission denied"))
    with pytest.raises(DdcUnavailable):
        DdcutilCli(runner).read(HANDLE, [0x10])


def test_write_command_success():
    runner = FakeRunner(RunResult(0, ""))
    DdcutilCli(runner).write(HANDLE, 0x19, 3)
    assert runner.calls == [["ddcutil", "--bus", "15", "--permit-unknown-feature", "setvcp", "19", "0x3"]]


def test_write_without_verify():
    runner = FakeRunner(RunResult(0, ""))
    DdcutilCli(runner).write(HANDLE, 0x60, 0x11, verify=False)
    assert runner.calls == [
        ["ddcutil", "--bus", "15", "--permit-unknown-feature", "--noverify", "setvcp", "60", "0x11"]
    ]


def test_write_16bit_value():
    runner = FakeRunner(RunResult(0, ""))
    DdcutilCli(runner).write(HANDLE, 0xFD, 0x0104)
    assert runner.calls[0][-1] == "0x104"


def test_write_verify_failure_is_rejected():
    runner = FakeRunner(RunResult(1, "Verification failed for feature fd\n    Try errors: DDCRC_VERIFY"))
    with pytest.raises(WriteRejected):
        DdcutilCli(runner).write(HANDLE, 0xFD, 1)


def test_write_communication_failure_is_unreachable():
    runner = FakeRunner(RunResult(1, "DDC communication failed"))
    with pytest.raises(Unreachable):
        DdcutilCli(runner).write(HANDLE, 0x10, 1)


def test_timeout_is_retried_once():
    runner = FakeRunner(RunResult(TIMEOUT_RC, "timeout"), RunResult(0, "VCP 10 C 65 100\n"))
    assert DdcutilCli(runner).read(HANDLE, [0x10])[0x10].current == 65
    assert len(runner.calls) == 2


def test_subprocess_runner_missing_binary():
    with pytest.raises(DdcUnavailable):
        subprocess_runner(["definitely-not-installed-ddcutil-xyz"], 1.0)
