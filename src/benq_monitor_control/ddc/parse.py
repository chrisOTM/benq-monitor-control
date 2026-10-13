"""Parsers for ddcutil's terse output and error messages."""

import re
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class VcpValue:
    code: int
    current: int
    maximum: int


@dataclass(frozen=True)
class DetectedDisplay:
    bus: int
    connector: str
    manufacturer: str
    model: str
    serial: str


_CONTINUOUS = re.compile(r"^VCP ([0-9A-Fa-f]{2}) C (\d+) (\d+)$")
_SIMPLE_NC = re.compile(r"^VCP ([0-9A-Fa-f]{2}) SNC x([0-9A-Fa-f]{2})$")
_COMPLEX_NC = re.compile(
    r"^VCP ([0-9A-Fa-f]{2}) CNC x([0-9A-Fa-f]{2}) x([0-9A-Fa-f]{2}) x([0-9A-Fa-f]{2}) x([0-9A-Fa-f]{2})$"
)
# Simple non-continuous features report no maximum; any byte value is possible.
SNC_MAXIMUM = 0xFF


def parse_getvcp_terse(text: str) -> dict[int, VcpValue]:
    values: dict[int, VcpValue] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if m := _CONTINUOUS.match(line):
            code = int(m[1], 16)
            values[code] = VcpValue(code, int(m[2]), int(m[3]))
        elif m := _SIMPLE_NC.match(line):
            code = int(m[1], 16)
            values[code] = VcpValue(code, int(m[2], 16), SNC_MAXIMUM)
        elif m := _COMPLEX_NC.match(line):
            code = int(m[1], 16)
            mh, ml, sh, sl = (int(m[i], 16) for i in range(2, 6))
            values[code] = VcpValue(code, (sh << 8) | sl, (mh << 8) | ml)
    return values


def parse_detect_terse(text: str) -> list[DetectedDisplay]:
    displays: list[DetectedDisplay] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or not lines[0].startswith("Display "):
            continue
        fields: dict[str, str] = {}
        for line in lines[1:]:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
        bus = re.search(r"i2c-(\d+)", fields.get("I2C bus", ""))
        if bus is None:
            continue
        manufacturer, model, serial = (fields.get("Monitor", "") + "::").split(":")[:3]
        displays.append(
            DetectedDisplay(
                bus=int(bus[1]),
                connector=fields.get("DRM connector", ""),
                manufacturer=manufacturer,
                model=model,
                serial=serial,
            )
        )
    return displays


class ErrorKind(Enum):
    VERIFY_FAILED = "verify_failed"
    UNSUPPORTED_FEATURE = "unsupported_feature"
    NO_DISPLAY = "no_display"
    PERMISSION = "permission"
    OTHER = "other"


def classify_error(text: str) -> ErrorKind:
    t = text.lower()
    if "verification failed" in t:
        return ErrorKind.VERIFY_FAILED
    if "unrecognized vcp feature" in t or "unsupported feature" in t:
        return ErrorKind.UNSUPPORTED_FEATURE
    if "permission denied" in t or "eacces" in t:
        return ErrorKind.PERMISSION
    if any(s in t for s in ("no monitor detected", "display not found", "ddc communication failed", "invalid display")):
        return ErrorKind.NO_DISPLAY
    return ErrorKind.OTHER
