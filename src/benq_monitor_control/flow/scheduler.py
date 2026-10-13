"""Which scenario is active now, and which one starts next (spec §7.3)."""

import os
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .scenario import Scenario, ScheduleKind
from .sun import Location, sun_times


def local_zone() -> tzinfo:
    """The system's IANA zone (needed for correct DST handling across days)."""
    key = (os.environ.get("TZ") or "").lstrip(":")
    if not key:
        try:
            key = os.readlink("/etc/localtime").split("zoneinfo/", 1)[1]
        except (OSError, IndexError):
            key = ""
    try:
        return ZoneInfo(key) if key else datetime.now().astimezone().tzinfo
    except (ZoneInfoNotFoundError, ValueError):
        return datetime.now().astimezone().tzinfo


def to_utc(moment: datetime) -> datetime:
    return moment.astimezone(timezone.utc)


def start_on(scenario: Scenario, day: date, tz: tzinfo, location: Location | None) -> datetime | None:
    schedule = scenario.schedule
    if schedule.kind is ScheduleKind.MANUAL:
        return None
    if schedule.kind is ScheduleKind.TIME:
        base = datetime.combine(day, schedule.at, tzinfo=tz)
    else:
        if location is None:
            return None
        sun = sun_times(day, location.latitude, location.longitude, tz)
        base = sun.sunrise if schedule.kind is ScheduleKind.SUNRISE else sun.sunset
        if base is None:
            return None
    return base + timedelta(minutes=schedule.offset_min)


def active_at(scenarios: Sequence[Scenario], now: datetime, location: Location | None) -> Scenario | None:
    tz = now.tzinfo
    now_utc = to_utc(now)
    best: tuple[datetime, Scenario] | None = None
    for day in (now.date() - timedelta(days=1), now.date()):
        for scenario in scenarios:
            start = start_on(scenario, day, tz, location)
            if start is None:
                continue
            start_utc = to_utc(start)
            if start_utc <= now_utc and (best is None or start_utc > best[0]):
                best = (start_utc, scenario)
    return best[1] if best else None


def next_start(
    scenarios: Sequence[Scenario], now: datetime, location: Location | None
) -> tuple[datetime, Scenario] | None:
    tz = now.tzinfo
    now_utc = to_utc(now)
    best: tuple[datetime, Scenario] | None = None
    for offset in (0, 1, 2):
        day = now.date() + timedelta(days=offset)
        for scenario in scenarios:
            start = start_on(scenario, day, tz, location)
            if start is None:
                continue
            start_utc = to_utc(start)
            if start_utc > now_utc and (best is None or start_utc < best[0]):
                best = (start_utc, scenario)
    return (best[0].astimezone(tz), best[1]) if best else None
