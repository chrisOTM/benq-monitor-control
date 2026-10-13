"""In-memory MA320U used by tests; mirrors behaviour observed on 2026-10-13."""

from collections.abc import Iterable

from .backend import DdcUnavailable, MonitorHandle, Unreachable, WriteRejected
from .parse import VcpValue

MODE_CODE = 0xDC
DEFAULT_VALUES = {
    0xDC: 0x0F, 0x10: 65, 0x12: 50, 0x14: 0x0B, 0x19: 0, 0x5F: 2, 0x60: 0x13,
    0x62: 20, 0x72: 0x78, 0x81: 0, 0x87: 6, 0xC9: 0x0102, 0xFD: 0,
}
DEFAULT_MAXIMA = {
    0xDC: 0xFF, 0x10: 100, 0x12: 100, 0x14: 0x0B, 0x19: 5, 0x5F: 3, 0x60: 0xFF,
    0x62: 50, 0x72: 0xA0, 0x81: 2, 0x87: 10, 0xC9: 0xFFFF, 0xFD: 0x0A04,
}
# Values the monitor stores per picture mode.
PER_MODE_CODES = frozenset({0x10, 0x14, 0x5F, 0x87})
SELECTABLE_MODES = frozenset({0x0A, 0x0F, 0x12, 0x22, 0x28, 0x32})
# Per-mode values seen in the live mode sweep.
DEFAULT_MODE_VALUES = {
    0x0A: {0x10: 38, 0x14: 0x00, 0x5F: 0x00},
    0x12: {0x10: 100, 0x14: 0x05, 0x5F: 0x02},
    0x22: {0x10: 100, 0x14: 0x00, 0x5F: 0x03},
}
# (mode, code) pairs the monitor rejects: gamma and colour weakness in M-Book.
DEFAULT_REJECTS = frozenset({(0x0F, 0x72), (0x0F, 0xFD)})


class FakeBackend:
    def __init__(
        self,
        *,
        model_name: str = "BenQ MA320U",
        bus: int = 15,
        values: dict[int, int] | None = None,
        mode_values: dict[int, dict[int, int]] | None = None,
        rejects: Iterable[tuple[int, int]] = DEFAULT_REJECTS,
    ) -> None:
        self.model_name = model_name
        self.bus = bus
        self.present = True
        self.reachable = True
        self.unavailable: DdcUnavailable | None = None
        self.maxima = dict(DEFAULT_MAXIMA)
        self.rejects = set(rejects)
        self.writes: list[tuple[int, int]] = []
        self.verify_flags: list[bool] = []
        self._values = dict(DEFAULT_VALUES)
        self._values.update(values or {})
        source = DEFAULT_MODE_VALUES if mode_values is None else mode_values
        self._mode_store = {mode: dict(v) for mode, v in source.items()}

    def detect(self, model_name: str) -> MonitorHandle | None:
        if self.unavailable is not None:
            raise self.unavailable
        if not self.present or model_name != self.model_name:
            return None
        return MonitorHandle(self.bus, self.model_name, "FAKE0001")

    def read(self, handle: MonitorHandle, codes: Iterable[int]) -> dict[int, VcpValue]:
        self._check()
        return {c: VcpValue(c, self._values[c], self.maxima[c]) for c in codes if c in self._values}

    def write(self, handle: MonitorHandle, code: int, value: int, verify: bool = True) -> None:
        self._check()
        mode = self._values[MODE_CODE]
        if (mode, code) in self.rejects:
            raise WriteRejected(f"Verification failed for feature {code:02x}")
        if code == MODE_CODE:
            if value not in SELECTABLE_MODES:
                raise WriteRejected(f"Verification failed for feature {code:02x}")
            self._switch_mode(value)
        else:
            self._values[code] = value
        self.writes.append((code, value))
        self.verify_flags.append(verify)

    def external_set(self, code: int, value: int) -> None:
        """Simulate a change made on the monitor itself (OSD, HDR signal)."""
        self._values[code] = value

    def value(self, code: int) -> int:
        return self._values[code]

    def _switch_mode(self, new_mode: int) -> None:
        old_mode = self._values[MODE_CODE]
        self._mode_store[old_mode] = {c: self._values[c] for c in PER_MODE_CODES}
        self._values.update(self._mode_store.get(new_mode, {}))
        self._values[MODE_CODE] = new_mode

    def _check(self) -> None:
        if self.unavailable is not None:
            raise self.unavailable
        if not (self.present and self.reachable):
            raise Unreachable("fake monitor unreachable")
