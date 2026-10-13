"""QObject bridge between QML and the monitor session (which lives on the worker)."""

import logging
import time
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from ..models.model import Feature
from .executor import Executor
from .session import ApplyResult, MonitorSession, Snapshot
from .throttle import Coalescer

log = logging.getLogger(__name__)


class MonitorController(QObject):
    stateChanged = Signal()
    writeFailed = Signal(str, str)

    def __init__(
        self,
        session: MonitorSession,
        executor: Executor,
        *,
        poll_interval_s: float = 5.0,
        retry_interval_s: float = 10.0,
        quiet_after_write_s: float = 2.0,
        clock: Callable[[], float] = time.monotonic,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._model = session.model
        self._executor = executor
        self._clock = clock
        self._retry_interval = retry_interval_s
        self._quiet_after = quiet_after_write_s
        self._snap: Snapshot = session.snapshot()
        self._coalescer = Coalescer(0.2)
        self._dragging: set[Feature] = set()
        # Values the user just set, shown until the monitor confirms or rejects them,
        # so sliders neither jump back mid-drag nor keep a refused value.
        self._shown: dict[Feature, int] = {}
        self._inflight: dict[Feature, int] = {}
        self._quiet_until = float("-inf")
        self._last_retry = float("-inf")
        self._poll_busy = False
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(int(poll_interval_s * 1000))
        self._poll_timer.timeout.connect(self.tick_poll)
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(50)
        self._flush_timer.timeout.connect(self.tick_flush)

    # --- lifecycle -------------------------------------------------------
    def start(self) -> None:
        self._last_retry = self._clock()
        self.run_job(lambda s: s.connect())
        self._poll_timer.start()
        self._flush_timer.start()

    def run_job(
        self, job: Callable[[MonitorSession], Any], done: Callable[[Any], None] | None = None
    ) -> None:
        session = self._session

        def work() -> tuple[Any, Snapshot]:
            try:
                result = job(session)
            except Exception:
                log.exception("monitor job failed")
                result = None
            return result, session.snapshot()

        def finish(pair: tuple[Any, Snapshot] | None) -> None:
            result = None
            if pair is not None:
                result, snap = pair
                self._publish(snap)
            if done is not None:
                done(result)

        self._executor.submit(work, finish)

    def tick_poll(self) -> None:
        now = self._clock()
        if self._poll_busy or self._dragging or now < self._quiet_until or self._coalescer.has_pending():
            return
        if self._snap.reachable:
            job = lambda s: s.read_polled()  # noqa: E731
        elif now - self._last_retry >= self._retry_interval:
            self._last_retry = now
            job = lambda s: s.connect()  # noqa: E731
        else:
            return
        self._poll_busy = True
        self.run_job(job, self._poll_done)

    def tick_flush(self) -> None:
        for feature, value in self._coalescer.due(self._clock()):
            self._inflight[feature] = self._inflight.get(feature, 0) + 1
            self.run_job(
                lambda s, f=feature, v=value: s.apply(f, v),
                lambda result, f=feature: self._after_write(f, result),
            )

    # --- QML slots -------------------------------------------------------
    @Slot(str, int)
    def setValue(self, feature: str, value: int) -> None:
        f = Feature(feature)
        self._coalescer.push(f, int(value))
        self._shown[f] = int(value)
        self._quiet_until = self._clock() + self._quiet_after
        self.stateChanged.emit()

    @Slot(str)
    def beginDrag(self, feature: str) -> None:
        self._dragging.add(Feature(feature))

    @Slot(str)
    def endDrag(self, feature: str) -> None:
        f = Feature(feature)
        self._dragging.discard(f)
        self._quiet_until = self._clock() + self._quiet_after
        self._release(f)

    @Slot()
    def cancelDrags(self) -> None:
        """Safety net when a release never arrives (panel hidden mid-drag)."""
        for f in list(self._dragging):
            self.endDrag(f.value)

    @Slot()
    def refresh(self) -> None:
        self.run_job(lambda s: s.read_all() if s.reachable else s.connect())

    @Slot()
    def redetect(self) -> None:
        self.run_job(lambda s: s.connect())

    @Slot()
    def onScreensChanged(self) -> None:
        self._last_retry = self._clock()
        self.run_job(lambda s: s.connect())

    @Slot(int)
    def setPollInterval(self, seconds: int) -> None:
        self._poll_timer.setInterval(int(seconds) * 1000)

    # --- internals -------------------------------------------------------
    def _publish(self, snap: Snapshot) -> None:
        self._snap = snap
        if not snap.reachable:
            self._dragging.clear()  # a stuck drag must not block reconnecting
        self.stateChanged.emit()
        if not snap.reachable:
            for f in list(self._shown):
                self._release(f)

    def _release(self, feature: Feature) -> None:
        if (
            self._inflight.get(feature, 0) == 0
            and not self._coalescer.is_pending(feature)
            and feature not in self._dragging
            and self._shown.pop(feature, None) is not None
        ):
            self.stateChanged.emit()

    def _poll_done(self, _result: Any) -> None:
        self._poll_busy = False

    def _after_write(self, feature: Feature, result: ApplyResult | None) -> None:
        self._inflight[feature] = max(0, self._inflight.get(feature, 0) - 1)
        self._quiet_until = self._clock() + self._quiet_after
        self._release(feature)
        if result is not ApplyResult.APPLIED:
            reason = result.value if result is not None else "error"
            log.info("write %s failed: %s", feature, reason)
            self.writeFailed.emit(feature.value, reason)

    def _value(self, feature: Feature) -> int:
        if feature in self._shown:
            return self._shown[feature]
        return int(self._snap.values.get(feature, 0))

    def _choices(self, feature: Feature) -> list[dict[str, Any]]:
        return [{"value": c.value, "label": c.label} for c in self._model.spec(feature).choices]

    # --- QML properties --------------------------------------------------
    def _get_reachable(self) -> bool:
        return self._snap.reachable

    def _get_picture_mode(self) -> int:
        return self._value(Feature.PICTURE_MODE)

    def _get_brightness(self) -> int:
        return self._value(Feature.BRIGHTNESS)

    def _get_volume(self) -> int:
        return self._value(Feature.VOLUME)

    def _get_input_source(self) -> int:
        return self._value(Feature.INPUT_SOURCE)

    def _get_low_blue_light(self) -> int:
        return self._value(Feature.LOW_BLUE_LIGHT)

    def _get_brightness_intelligence(self) -> int:
        return self._value(Feature.BRIGHTNESS_INTELLIGENCE)

    def _get_hdr_active(self) -> bool:
        return self._snap.hdr_active

    def _get_error_text(self) -> str:
        return self._snap.error or ""

    def _get_firmware(self) -> str:
        return self._snap.firmware or ""

    def _get_bus(self) -> int:
        return self._snap.bus if self._snap.bus is not None else -1

    def _get_maxima(self) -> dict[str, int]:
        return {f.value: v for f, v in self._snap.maxima.items()}

    def _get_locked(self) -> dict[str, bool]:
        return {f.value: bool(v) for f, v in self._snap.locked.items()}

    def _get_raw_values(self) -> dict[str, int]:
        return {f.value: v for f, v in self._snap.values.items()}

    def _get_display_name(self) -> str:
        return self._model.display_name

    def _get_picture_modes(self) -> list[dict[str, Any]]:
        return self._choices(Feature.PICTURE_MODE)

    def _get_inputs(self) -> list[dict[str, Any]]:
        return self._choices(Feature.INPUT_SOURCE)

    reachable = Property(bool, _get_reachable, notify=stateChanged)
    pictureMode = Property(int, _get_picture_mode, notify=stateChanged)
    brightness = Property(int, _get_brightness, notify=stateChanged)
    volume = Property(int, _get_volume, notify=stateChanged)
    inputSource = Property(int, _get_input_source, notify=stateChanged)
    lowBlueLight = Property(int, _get_low_blue_light, notify=stateChanged)
    brightnessIntelligence = Property(int, _get_brightness_intelligence, notify=stateChanged)
    hdrActive = Property(bool, _get_hdr_active, notify=stateChanged)
    errorText = Property(str, _get_error_text, notify=stateChanged)
    firmware = Property(str, _get_firmware, notify=stateChanged)
    bus = Property(int, _get_bus, notify=stateChanged)
    maxima = Property("QVariantMap", _get_maxima, notify=stateChanged)
    locked = Property("QVariantMap", _get_locked, notify=stateChanged)
    rawValues = Property("QVariantMap", _get_raw_values, notify=stateChanged)
    displayName = Property(str, _get_display_name, constant=True)
    pictureModes = Property("QVariantList", _get_picture_modes, constant=True)
    inputs = Property("QVariantList", _get_inputs, constant=True)
