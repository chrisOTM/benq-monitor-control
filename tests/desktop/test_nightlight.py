from benq_monitor_control.desktop.nightlight import NightLightState, NightLightWatcher, parse_night_light

DAY = {"available": True, "enabled": True, "running": True, "inhibited": False, "currentTemperature": 6500}


def test_missing_service():
    assert parse_night_light(None) == NightLightState()


def test_enabled_but_daylight_is_not_warming():
    assert parse_night_light(DAY) == NightLightState(available=True, enabled=True, warming=False)


def test_warming_at_night():
    state = parse_night_light({**DAY, "currentTemperature": 4000})
    assert state.enabled and state.warming


def test_inhibited_or_not_running_is_not_warming():
    assert not parse_night_light({**DAY, "currentTemperature": 4000, "inhibited": True}).warming
    assert not parse_night_light({**DAY, "currentTemperature": 4000, "running": False}).warming


def test_disabled():
    state = parse_night_light({**DAY, "enabled": False, "currentTemperature": 4000})
    assert not state.enabled and not state.warming


def test_garbage_temperature_is_neutral():
    assert not parse_night_light({**DAY, "currentTemperature": "warm"}).warming


def test_watcher_emits_on_change(qapp):
    props = {"value": None}
    watcher = NightLightWatcher(fetch=lambda: props["value"])
    seen = []
    watcher.changed.connect(lambda: seen.append((watcher.enabled, watcher.warming)))
    watcher.refresh()
    assert seen == []  # still the default state
    props["value"] = {**DAY, "currentTemperature": 4200}
    watcher.refresh()
    watcher.refresh()
    assert seen == [(True, True)]
