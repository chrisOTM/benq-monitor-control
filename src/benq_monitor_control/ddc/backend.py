"""Monitor access protocol and the errors every backend raises."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from .parse import VcpValue


class DdcError(Exception):
    """Base class for monitor communication errors."""


class Unreachable(DdcError):
    """The monitor did not answer (absent, other input active, standby)."""


class WriteRejected(DdcError):
    """The monitor refused a value (verify failed or feature unsupported)."""


class DdcUnavailable(DdcError):
    """DDC/CI cannot be used at all (ddcutil missing, no permission)."""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.hint = hint

    def __str__(self) -> str:
        base = super().__str__()
        return f"{base} — {self.hint}" if self.hint else base


@dataclass(frozen=True)
class MonitorHandle:
    bus: int
    model: str
    serial: str


class DdcBackend(Protocol):
    def detect(self, model_name: str) -> MonitorHandle | None: ...

    def read(self, handle: MonitorHandle, codes: Iterable[int]) -> dict[int, VcpValue]: ...

    def write(self, handle: MonitorHandle, code: int, value: int, verify: bool = True) -> None: ...
