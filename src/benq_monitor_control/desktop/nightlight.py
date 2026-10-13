"""Read KDE Night Light (KWin) state over the session D-Bus."""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

log = logging.getLogger(__name__)

NEUTRAL_K = 6500
SERVICE = "org.kde.KWin"
PATH = "/org/kde/KWin/NightLight"
INTERFACE = "org.kde.KWin.NightLight"


@dataclass(frozen=True)
class NightLightState:
    available: bool = False
    enabled: bool = False
    warming: bool = False


def _unwrap(value: Any) -> Any:
    variant = getattr(value, "variant", None)
    return variant() if callable(variant) else value


def parse_night_light(props: Mapping[str, Any] | None) -> NightLightState:
    if not props:
        return NightLightState()
    p = {k: _unwrap(v) for k, v in props.items()}
    enabled = bool(p.get("enabled", False))
    running = bool(p.get("running", False))
    inhibited = bool(p.get("inhibited", False))
    try:
        temperature = int(p.get("currentTemperature", NEUTRAL_K))
    except (TypeError, ValueError):
        temperature = NEUTRAL_K
    warming = enabled and running and not inhibited and temperature < NEUTRAL_K
    return NightLightState(available=True, enabled=enabled, warming=warming)


def fetch_kwin_night_light() -> dict[str, Any] | None:
    from PySide6.QtDBus import QDBus, QDBusConnection, QDBusMessage

    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        return None
    # GetAll returns an a{sv} that PySide6 hands back as an opaque QDBusArgument,
    # so read the four properties with Get, whose QDBusVariant replies unwrap cleanly.
    props: dict[str, Any] = {}
    for name in ("enabled", "running", "inhibited", "currentTemperature"):
        message = QDBusMessage.createMethodCall(SERVICE, PATH, "org.freedesktop.DBus.Properties", "Get")
        message.setArguments([INTERFACE, name])
        reply = bus.call(message, QDBus.CallMode.Block, 500)
        if reply.type() != QDBusMessage.MessageType.ReplyMessage or not reply.arguments():
            return None
        props[name] = _unwrap(reply.arguments()[0])
    return props


class NightLightWatcher(QObject):
    changed = Signal()

    def __init__(
        self,
        fetch: Callable[[], Mapping[str, Any] | None] = fetch_kwin_night_light,
        interval_s: int = 30,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._fetch = fetch
        self._state = NightLightState()
        self._timer = QTimer(self)
        self._timer.setInterval(interval_s * 1000)
        self._timer.timeout.connect(self.refresh)

    def start(self) -> None:
        self.refresh()
        self._timer.start()

    @Slot()
    def refresh(self) -> None:
        try:
            state = parse_night_light(self._fetch())
        except Exception:
            log.exception("reading Night Light state failed")
            state = NightLightState()
        if state != self._state:
            self._state = state
            self.changed.emit()

    def _get_enabled(self) -> bool:
        return self._state.enabled

    def _get_warming(self) -> bool:
        return self._state.warming

    enabled = Property(bool, _get_enabled, notify=changed)
    warming = Property(bool, _get_warming, notify=changed)
