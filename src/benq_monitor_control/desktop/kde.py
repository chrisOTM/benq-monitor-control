"""Read the location KDE Night Light stores in kwinrc."""

import configparser
import os
import re
from pathlib import Path

from ..config.settings import valid_coordinates
from ..flow.sun import Location


def kwinrc_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "kwinrc"


def night_light_location(kwinrc: Path | None = None) -> Location | None:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str  # keep key case
    try:
        read = parser.read(kwinrc or kwinrc_path(), encoding="utf-8")
    except configparser.Error:
        return None
    if not read or not parser.has_section("NightColor"):
        return None
    section = parser["NightColor"]
    for suffix in ("Fixed", "Auto"):
        try:
            lat = float(section[f"Latitude{suffix}"])
            lon = float(section[f"Longitude{suffix}"])
        except (KeyError, ValueError):
            continue
        if valid_coordinates(lat, lon):
            return Location(lat, lon)
    return None


# Plasma panel containment "location" values.
_EDGES = {"3": "top", "4": "bottom", "5": "left", "6": "right"}


def appletsrc_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "plasma-org.kde.plasma.desktop-appletsrc"


def tray_panel_edge(appletsrc: Path | None = None) -> str | None:
    """Edge ("top", "bottom", "left", "right") of the Plasma panel holding the system tray."""
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    try:
        if not parser.read(appletsrc or appletsrc_path(), encoding="utf-8"):
            return None
    except configparser.Error:
        return None
    for section in parser.sections():
        m = re.fullmatch(r"Containments\]\[(\d+)\]\[Applets\]\[\d+", section)
        if m is None or parser[section].get("plugin") != "org.kde.plasma.systemtray":
            continue
        panel = f"Containments][{m[1]}"
        if parser.has_section(panel):
            return _EDGES.get(parser[panel].get("location", ""))
    return None
