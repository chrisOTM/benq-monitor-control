"""Sunrise/sunset from the NOAA solar calculator equations; no network needed."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, tzinfo
from math import acos, asin, cos, degrees, radians, sin, tan

ZENITH_DEG = 90.833  # official: refraction + solar disc radius


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class SunTimes:
    sunrise: datetime | None
    sunset: datetime | None


def sun_times(day: date, latitude: float, longitude: float, tz: tzinfo) -> SunTimes:
    # Julian day at local solar noon (approximation good to well under a minute).
    jd = day.toordinal() + 1721424.5 + 0.5 - longitude / 360.0
    t = (jd - 2451545.0) / 36525.0
    mean_long = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360
    mean_anom = radians(357.52911 + t * (35999.05029 - 0.0001537 * t))
    ecc = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    center = (
        sin(mean_anom) * (1.914602 - t * (0.004817 + 0.000014 * t))
        + sin(2 * mean_anom) * (0.019993 - 0.000101 * t)
        + sin(3 * mean_anom) * 0.000289
    )
    omega = radians(125.04 - 1934.136 * t)
    app_long = radians(mean_long + center - 0.00569 - 0.00478 * sin(omega))
    obliq0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
    obliq = radians(obliq0 + 0.00256 * cos(omega))
    decl = asin(sin(obliq) * sin(app_long))
    y = tan(obliq / 2) ** 2
    l0 = radians(mean_long)
    eq_time_min = 4 * degrees(
        y * sin(2 * l0)
        - 2 * ecc * sin(mean_anom)
        + 4 * ecc * y * sin(mean_anom) * cos(2 * l0)
        - 0.5 * y * y * sin(4 * l0)
        - 1.25 * ecc * ecc * sin(2 * mean_anom)
    )
    lat = radians(latitude)
    cos_ha = cos(radians(ZENITH_DEG)) / (cos(lat) * cos(decl)) - tan(lat) * tan(decl)
    if not -1.0 <= cos_ha <= 1.0:
        return SunTimes(None, None)  # polar night (> 1) or polar day (< -1)
    ha_min = 4 * degrees(acos(cos_ha))
    noon_utc_min = 720 - 4 * longitude - eq_time_min
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    return SunTimes(
        sunrise=(midnight + timedelta(minutes=noon_utc_min - ha_min)).astimezone(tz),
        sunset=(midnight + timedelta(minutes=noon_utc_min + ha_min)).astimezone(tz),
    )
