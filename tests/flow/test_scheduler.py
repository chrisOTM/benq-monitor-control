from dataclasses import replace
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from benq_monitor_control.flow.scenario import Schedule, ScheduleKind, new_scenario
from benq_monitor_control.flow.scheduler import active_at, next_start, start_on
from benq_monitor_control.flow.sun import Location

TZ = ZoneInfo("Europe/Berlin")
BERLIN = Location(52.52, 13.405)


def at(hh, mm, name):
    return replace(new_scenario(name), schedule=Schedule(ScheduleKind.TIME, time(hh, mm), 0))


DAY = at(7, 0, "Day")
EVENING = at(23, 30, "Evening")
MANUAL = new_scenario("Cinema")


def dt(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=TZ)


def test_active_during_day_and_evening():
    scenarios = [DAY, EVENING, MANUAL]
    assert active_at(scenarios, dt(2026, 10, 13, 12, 0), None) is DAY
    assert active_at(scenarios, dt(2026, 10, 13, 23, 45), None) is EVENING


def test_midnight_wrap():
    assert active_at([DAY, EVENING], dt(2026, 10, 14, 0, 30), None) is EVENING
    assert active_at([DAY, EVENING], dt(2026, 10, 14, 7, 1), None) is DAY


def test_only_manual_scenarios():
    assert active_at([MANUAL], dt(2026, 10, 13, 12, 0), None) is None
    assert next_start([MANUAL], dt(2026, 10, 13, 12, 0), None) is None


def test_tie_first_listed_wins():
    a, b = at(8, 0, "A"), at(8, 0, "B")
    assert active_at([a, b], dt(2026, 10, 13, 9, 0), None) is a
    assert next_start([a, b], dt(2026, 10, 13, 7, 0), None)[1] is a


def test_next_start_today_and_tomorrow():
    start, scenario = next_start([DAY, EVENING], dt(2026, 10, 13, 22, 0), None)
    assert scenario is EVENING and start == dt(2026, 10, 13, 23, 30)
    start, scenario = next_start([DAY, EVENING], dt(2026, 10, 13, 23, 31), None)
    assert scenario is DAY and start == dt(2026, 10, 14, 7, 0)


def test_spring_forward_day():
    # 2026-03-29 02:00 CET jumps to 03:00 CEST; 02:30 does not exist on that day.
    night = at(2, 30, "Night")
    early = at(1, 0, "Early")
    scenarios = [early, night]
    assert active_at(scenarios, dt(2026, 3, 29, 1, 30), None) is early
    assert active_at(scenarios, dt(2026, 3, 29, 4, 0), None) is night
    start, scenario = next_start(scenarios, dt(2026, 3, 29, 1, 30), None)
    assert scenario is night and start > dt(2026, 3, 29, 1, 30)


def test_sunset_with_offset():
    evening = replace(new_scenario("Evening"), schedule=Schedule(ScheduleKind.SUNSET, None, 30))
    start = start_on(evening, dt(2026, 6, 21, 0, 0).date(), TZ, BERLIN)
    expected = dt(2026, 6, 21, 22, 3)
    assert abs(start - expected) <= timedelta(minutes=2)


def test_sun_schedule_without_location_never_triggers():
    evening = replace(new_scenario("Evening"), schedule=Schedule(ScheduleKind.SUNSET, None, 0))
    assert active_at([evening], dt(2026, 6, 21, 23, 0), None) is None
    assert next_start([evening], dt(2026, 6, 21, 12, 0), None) is None


def test_polar_day_skips_sun_schedule():
    tromso = Location(69.6492, 18.9553)
    evening = replace(new_scenario("Evening"), schedule=Schedule(ScheduleKind.SUNSET, None, 0))
    oslo = ZoneInfo("Europe/Oslo")
    assert start_on(evening, dt(2026, 6, 21, 0, 0).date(), oslo, tromso) is None
