"""XDG autostart entry for the tray app."""

import os
from pathlib import Path

ENTRY = (
    "[Desktop Entry]\n"
    "Type=Application\n"
    "Name=BenQ Monitor Control\n"
    "Exec=benq-monitor-control\n"
    "Icon=benq-monitor-control\n"
    "X-KDE-autostart-after=panel\n"
)


def autostart_file(config_home: Path | None = None) -> Path:
    base = config_home or Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "autostart" / "benq-monitor-control.desktop"


def set_autostart(enabled: bool, config_home: Path | None = None) -> None:
    path = autostart_file(config_home)
    if enabled:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ENTRY, encoding="utf-8")
    else:
        path.unlink(missing_ok=True)


def autostart_enabled(config_home: Path | None = None) -> bool:
    return autostart_file(config_home).is_file()
