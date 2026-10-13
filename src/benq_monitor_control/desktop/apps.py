"""Installed applications from XDG desktop entries; launch them through gio."""

import os
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppEntry:
    desktop_id: str
    name: str
    path: Path


def application_dirs() -> list[Path]:
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    data_dirs = (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    return [data_home / "applications"] + [Path(d) / "applications" for d in data_dirs if d]


def _desktop_entry(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    fields: dict[str, str] = {}
    in_group = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_group = stripped == "[Desktop Entry]"
            continue
        if in_group and "=" in stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            fields.setdefault(key.strip(), value.strip())
    return fields


def list_apps(dirs: Sequence[Path] | None = None) -> list[AppEntry]:
    seen: dict[str, AppEntry | None] = {}  # first directory wins; None hides later copies
    for directory in dirs if dirs is not None else application_dirs():
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.desktop")):
            if path.name in seen:
                continue
            fields = _desktop_entry(path)
            visible = (
                fields.get("Type") == "Application"
                and fields.get("NoDisplay") != "true"
                and fields.get("Hidden") != "true"
                and "Name" in fields
            )
            seen[path.name] = AppEntry(path.name, fields["Name"], path) if visible else None
    return sorted((e for e in seen.values() if e is not None), key=lambda e: e.name.casefold())


def resolve(desktop_id: str, dirs: Sequence[Path] | None = None) -> Path | None:
    for directory in dirs if dirs is not None else application_dirs():
        candidate = directory / desktop_id
        if candidate.is_file():
            return candidate
    return None


def launch(
    desktop_id: str, dirs: Sequence[Path] | None = None, popen: Callable[..., object] = subprocess.Popen
) -> bool:
    path = resolve(desktop_id, dirs)
    if path is None:
        return False
    try:
        popen(
            ["gio", "launch", str(path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return False
    return True
