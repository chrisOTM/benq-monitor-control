"""QObject exposing user settings to QML."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..config.settings import (
    CORNERS,
    LANGUAGES,
    SYNC_RANGE,
    Settings,
    resolve_corner,
    save_settings,
    valid_coordinates,
)
from ..desktop.autostart import autostart_enabled, set_autostart
from ..desktop.kde import night_light_location, tray_panel_edge
from ..flow.sun import Location


class SettingsBridge(QObject):
    changed = Signal()

    def __init__(
        self,
        settings: Settings,
        path: Path,
        *,
        on_language: Callable[[str], None] = lambda language: None,
        on_location: Callable[[], None] = lambda: None,
        on_sync_interval: Callable[[int], None] = lambda seconds: None,
        autostart_fn: Callable[[bool], None] = set_autostart,
        autostart_state: Callable[[], bool] = autostart_enabled,
        kwinrc: Path | None = None,
        panel_edge: Callable[[], str | None] = tray_panel_edge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._path = path
        self._on_language = on_language
        self._on_location = on_location
        self._on_sync_interval = on_sync_interval
        self._autostart_fn = autostart_fn
        self._kwinrc = kwinrc
        self._panel_edge = panel_edge
        self._edge = panel_edge()
        self._settings.autostart = autostart_state()  # the file on disk is the truth

    def location(self) -> Location | None:
        return self._settings.location()

    @Slot(bool)
    def setAutostart(self, enabled: bool) -> None:
        self._autostart_fn(enabled)
        self._settings.autostart = enabled
        self._save()

    @Slot(str)
    def setLanguage(self, language: str) -> None:
        if language not in LANGUAGES:
            return
        self._settings.language = language
        self._save()
        self._on_language(language)

    @Slot(str, str, result=bool)
    def setLocation(self, latitude: str, longitude: str) -> bool:
        lat_text = latitude.strip().replace(",", ".")
        lon_text = longitude.strip().replace(",", ".")
        if not lat_text and not lon_text:
            self._settings.latitude = self._settings.longitude = None
        else:
            try:
                lat, lon = float(lat_text), float(lon_text)
            except ValueError:
                return False
            if not valid_coordinates(lat, lon):
                return False
            self._settings.latitude, self._settings.longitude = lat, lon
        self._save()
        self._on_location()
        return True

    @Slot(result=bool)
    def importFromKde(self) -> bool:
        location = night_light_location(self._kwinrc)
        if location is None:
            return False
        self._settings.latitude, self._settings.longitude = location.latitude, location.longitude
        self._save()
        self._on_location()
        return True

    @Slot(int)
    def setSyncInterval(self, seconds: int) -> None:
        seconds = max(SYNC_RANGE[0], min(SYNC_RANGE[1], int(seconds)))
        self._settings.sync_interval_s = seconds
        self._save()
        self._on_sync_interval(seconds)

    @Slot(str)
    def setPanelCorner(self, corner: str) -> None:
        if corner in CORNERS:
            self._settings.panel_corner = corner
            self._save()

    @Slot()
    def refreshPanelEdge(self) -> None:
        edge = self._panel_edge()
        if edge != self._edge:
            self._edge = edge
            self.changed.emit()

    def _save(self) -> None:
        save_settings(self._path, self._settings)
        self.changed.emit()

    @staticmethod
    def _fmt(value: float | None) -> str:
        return "" if value is None else f"{value:g}"

    def _get_autostart(self) -> bool:
        return self._settings.autostart

    def _get_language(self) -> str:
        return self._settings.language

    def _get_latitude(self) -> str:
        return self._fmt(self._settings.latitude)

    def _get_longitude(self) -> str:
        return self._fmt(self._settings.longitude)

    def _get_sync_interval(self) -> int:
        return self._settings.sync_interval_s

    def _get_panel_corner(self) -> str:
        return self._settings.panel_corner

    def _get_effective_corner(self) -> str:
        return resolve_corner(self._settings.panel_corner, self._edge)

    def _get_has_location(self) -> bool:
        return self._settings.location() is not None

    autostart = Property(bool, _get_autostart, notify=changed)
    language = Property(str, _get_language, notify=changed)
    latitude = Property(str, _get_latitude, notify=changed)
    longitude = Property(str, _get_longitude, notify=changed)
    syncInterval = Property(int, _get_sync_interval, notify=changed)
    panelCorner = Property(str, _get_panel_corner, notify=changed)
    hasLocation = Property(bool, _get_has_location, notify=changed)
    effectiveCorner = Property(str, _get_effective_corner, notify=changed)
