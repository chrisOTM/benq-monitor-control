"""DdcBackend implementation that shells out to the ddcutil CLI."""

import subprocess
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from .backend import DdcUnavailable, MonitorHandle, Unreachable, WriteRejected
from .parse import ErrorKind, VcpValue, classify_error, parse_detect_terse, parse_getvcp_terse

TIMEOUT_RC = 124
PERMISSION_HINT = (
    "Grant access to /dev/i2c-*: install ddcutil's udev rule or add your user "
    "to the i2c group, then log in again."
)


@dataclass(frozen=True)
class RunResult:
    returncode: int
    output: str


Runner = Callable[[Sequence[str], float], RunResult]


def subprocess_runner(args: Sequence[str], timeout: float) -> RunResult:
    try:
        proc = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise DdcUnavailable("ddcutil is not installed", hint="sudo pacman -S ddcutil") from exc
    except subprocess.TimeoutExpired:
        return RunResult(TIMEOUT_RC, "timeout")
    return RunResult(proc.returncode, proc.stdout + proc.stderr)


class DdcutilCli:
    def __init__(self, runner: Runner = subprocess_runner, binary: str = "ddcutil", timeout_s: float = 10.0) -> None:
        self._runner = runner
        self._binary = binary
        self._timeout = timeout_s

    def detect(self, model_name: str) -> MonitorHandle | None:
        result = self._run("detect", "--terse")
        displays = parse_detect_terse(result.output)
        for display in displays:
            if display.model == model_name:
                return MonitorHandle(display.bus, display.model, display.serial)
        if not displays and classify_error(result.output) is ErrorKind.PERMISSION:
            raise DdcUnavailable("No permission for /dev/i2c-*", hint=PERMISSION_HINT)
        return None

    def read(self, handle: MonitorHandle, codes: Iterable[int]) -> dict[int, VcpValue]:
        result = self._run("--bus", str(handle.bus), "--terse", "getvcp", *(f"{c:02X}" for c in codes))
        values = parse_getvcp_terse(result.output)
        if values:
            return values
        if classify_error(result.output) is ErrorKind.PERMISSION:
            raise DdcUnavailable("No permission for /dev/i2c-*", hint=PERMISSION_HINT)
        raise Unreachable(result.output.strip() or f"no reply on bus {handle.bus}")

    def write(self, handle: MonitorHandle, code: int, value: int, verify: bool = True) -> None:
        args = ["--bus", str(handle.bus), "--permit-unknown-feature"]
        if not verify:
            args.append("--noverify")
        result = self._run(*args, "setvcp", f"{code:02X}", f"0x{value:X}")
        if result.returncode == 0:
            return
        kind = classify_error(result.output)
        if kind in (ErrorKind.VERIFY_FAILED, ErrorKind.UNSUPPORTED_FEATURE):
            raise WriteRejected(result.output.strip())
        if kind is ErrorKind.PERMISSION:
            raise DdcUnavailable("No permission for /dev/i2c-*", hint=PERMISSION_HINT)
        raise Unreachable(result.output.strip() or "setvcp failed")

    def _run(self, *args: str) -> RunResult:
        command = [self._binary, *args]
        result = self._runner(command, self._timeout)
        if result.returncode == TIMEOUT_RC and result.output == "timeout":
            result = self._runner(command, self._timeout)
        return result
