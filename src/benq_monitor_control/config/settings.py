"""User settings in settings.json; every field is validated on its own."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..flow.sun import Location
from .atomic import write_json_atomic

LANGUAGES = ("en", "de")
CORNERS = ("auto", "bottom-right", "bottom-left", "top-right", "top-left")
# "auto": the corner at the edge of the Plasma panel that holds the system tray.
_EDGE_CORNER = {"top": "top-right", "bottom": "bottom-right", "left": "bottom-left", "right": "bottom-right"}
SYNC_RANGE = (2, 60)


@dataclass
class Settings:
    autostart: bool = False
    language: str = "en"
    latitude: float | None = None
    longitude: float | None = None
    sync_interval_s: int = 5
    panel_corner: str = "auto"

    def location(self) -> Location | None:
        if self.latitude is None or self.longitude is None:
            return None
        return Location(self.latitude, self.longitude)


def valid_coordinates(lat: float, lon: float) -> bool:
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def load_settings(path: Path) -> Settings:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Settings()
    if not isinstance(data, dict):
        return Settings()
    s = Settings()
    if isinstance(data.get("autostart"), bool):
        s.autostart = data["autostart"]
    if data.get("language") in LANGUAGES:
        s.language = data["language"]
    lat, lon = data.get("latitude"), data.get("longitude")
    if _is_number(lat) and _is_number(lon) and valid_coordinates(lat, lon):
        s.latitude, s.longitude = float(lat), float(lon)
    sync = data.get("sync_interval_s")
    if isinstance(sync, int) and not isinstance(sync, bool) and SYNC_RANGE[0] <= sync <= SYNC_RANGE[1]:
        s.sync_interval_s = sync
    if data.get("panel_corner") in CORNERS:
        s.panel_corner = data["panel_corner"]
    return s


def save_settings(path: Path, settings: Settings) -> None:
    write_json_atomic(path, asdict(settings))


def resolve_corner(setting: str, tray_edge: str | None) -> str:
    """Concrete corner for the quick panel; "auto" follows the tray panel's edge."""
    if setting != "auto":
        return setting
    return _EDGE_CORNER.get(tray_edge or "", "bottom-right")
