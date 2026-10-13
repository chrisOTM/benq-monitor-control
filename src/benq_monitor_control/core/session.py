"""Synchronous monitor session. Not thread-safe: use it from one worker thread only."""

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from ..ddc.backend import DdcBackend, DdcError, DdcUnavailable, MonitorHandle, Unreachable, WriteRejected
from ..models.model import Feature, FeatureSpec, Kind, MonitorModel

log = logging.getLogger(__name__)

# Rejections of these features depend on the value, not on the picture mode.
_NOT_LEARNED = frozenset({Feature.PICTURE_MODE, Feature.INPUT_SOURCE})


class ApplyResult(StrEnum):
    APPLIED = "applied"
    LOCKED = "locked"
    REJECTED = "rejected"
    UNREACHABLE = "unreachable"
    INVALID = "invalid"


@dataclass(frozen=True)
class Snapshot:
    reachable: bool
    values: Mapping[Feature, int]
    maxima: Mapping[Feature, int]
    locked: Mapping[Feature, bool]
    hdr_active: bool
    firmware: str | None
    bus: int | None
    error: str | None


class MonitorSession:
    def __init__(self, backend: DdcBackend, model: MonitorModel) -> None:
        self.backend = backend
        self.model = model
        self._handle: MonitorHandle | None = None
        self._values: dict[Feature, int] = {}
        self._maxima: dict[Feature, int] = {}
        self._learned: set[tuple[int | None, Feature]] = set()
        self._firmware: str | None = None
        self._error: str | None = None

    @property
    def reachable(self) -> bool:
        return self._handle is not None

    @property
    def handle(self) -> MonitorHandle | None:
        return self._handle

    @property
    def mode(self) -> int | None:
        return self._values.get(Feature.PICTURE_MODE)

    def connect(self) -> bool:
        try:
            self._handle = self.backend.detect(self.model.model_name)
        except DdcUnavailable as exc:
            self._fail(exc)
            return False
        self._error = None
        if self._handle is None:
            return False
        self.read_all()
        if self._handle is not None and self._firmware is None:
            self._read_firmware()
        return self.reachable

    def read_all(self) -> None:
        self._read(self.model.codes())

    def read_polled(self) -> None:
        self._read(self.model.codes(polled_only=True))

    def is_locked(self, feature: Feature) -> bool:
        return self.model.is_locked(feature, self.mode) or (self.mode, feature) in self._learned

    def apply(self, feature: Feature, value: int) -> ApplyResult:
        if self._handle is None:
            return ApplyResult.UNREACHABLE
        spec = self.model.spec(feature)
        if not self._valid(spec, value):
            return ApplyResult.INVALID
        if self.is_locked(feature):
            return ApplyResult.LOCKED
        is_input = feature is Feature.INPUT_SOURCE
        try:
            self.backend.write(self._handle, spec.code, value, verify=not is_input)
        except WriteRejected:
            log.info("monitor rejected %s=%s in mode %s", feature, value, self.mode)
            if feature not in _NOT_LEARNED:
                self._learned.add((self.mode, feature))
            self._read([spec.code])
            return ApplyResult.REJECTED
        except Unreachable:
            self._handle = None
            return ApplyResult.UNREACHABLE
        except DdcUnavailable as exc:
            self._fail(exc)
            return ApplyResult.UNREACHABLE
        if feature is Feature.PICTURE_MODE:
            self.read_all()
        else:
            self._values[feature] = value  # ddcutil verified the write by reading it back
        if is_input:
            self._handle = None  # the monitor now shows another source
        return ApplyResult.APPLIED

    def snapshot(self) -> Snapshot:
        return Snapshot(
            reachable=self.reachable,
            values=dict(self._values),
            maxima=dict(self._maxima),
            locked={s.feature: self.is_locked(s.feature) for s in self.model.features},
            hdr_active=self.mode in self.model.hdr_modes,
            firmware=self._firmware,
            bus=self._handle.bus if self._handle else None,
            error=self._error,
        )

    def _read(self, codes: Iterable[int]) -> None:
        if self._handle is None:
            return
        try:
            raw = self.backend.read(self._handle, list(codes))
        except Unreachable:
            self._handle = None
            return
        except DdcUnavailable as exc:
            self._fail(exc)
            return
        for spec in self.model.features:
            value = raw.get(spec.code)
            if value is None:
                continue
            self._values[spec.feature] = value.current
            self._maxima[spec.feature] = spec.maximum if spec.maximum is not None else value.maximum

    def _read_firmware(self) -> None:
        try:
            raw = self.backend.read(self._handle, [self.model.firmware_code])
        except DdcError:
            return
        value = raw.get(self.model.firmware_code)
        if value is not None:
            self._firmware = f"{value.current >> 8}.{value.current & 0xFF}"

    def _valid(self, spec: FeatureSpec, value: int) -> bool:
        if spec.kind is Kind.CHOICE:
            return any(c.value == value for c in spec.choices)
        if spec.kind is Kind.TOGGLE:
            return value in (0, 1)
        maximum = self._maxima.get(spec.feature, spec.maximum if spec.maximum is not None else 100)
        return spec.minimum <= value <= maximum

    def _fail(self, exc: DdcUnavailable) -> None:
        log.warning("DDC unavailable: %s", exc)
        self._error = str(exc)
        self._handle = None
