from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from benq_monitor_control.flow.sun import SunTimes, sun_times

BERLIN = (52.52, 13.405)
TZ = ZoneInfo("Europe/Berlin")


def close(actual: datetime, hh: int, mm: int, tolerance_min: int = 2) -> bool:
    expected = actual.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return abs(actual - expected) <= timedelta(minutes=tolerance_min)


def test_berlin_summer_solstice():
    st = sun_times(date(2026, 6, 21), *BERLIN, TZ)
    assert close(st.sunrise, 4, 43) and close(st.sunset, 21, 33)


def test_berlin_winter_solstice():
    st = sun_times(date(2026, 12, 21), *BERLIN, TZ)
    assert close(st.sunrise, 8, 15) and close(st.sunset, 15, 54)


def test_berlin_equinox_day_length():
    st = sun_times(date(2026, 3, 20), *BERLIN, TZ)
    length = st.sunset - st.sunrise
    # About 12 h plus refraction/disc effects at 52° N.
    assert timedelta(hours=12, minutes=5) <= length <= timedelta(hours=12, minutes=15)


def test_results_are_in_requested_zone():
    st = sun_times(date(2026, 6, 21), *BERLIN, TZ)
    assert st.sunrise.tzinfo is TZ


def test_polar_day_in_tromso():
    assert sun_times(date(2026, 6, 21), 69.6492, 18.9553, ZoneInfo("Europe/Oslo")) == SunTimes(None, None)


def test_polar_night_in_tromso():
    assert sun_times(date(2026, 12, 21), 69.6492, 18.9553, ZoneInfo("Europe/Oslo")) == SunTimes(None, None)
