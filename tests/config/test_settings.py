import json

from benq_monitor_control.config.settings import Settings, load_settings, save_settings
from benq_monitor_control.flow.sun import Location


def test_defaults_when_missing(tmp_path):
    assert load_settings(tmp_path / "settings.json") == Settings()


def test_round_trip(tmp_path):
    path = tmp_path / "cfg" / "settings.json"
    s = Settings(autostart=True, language="de", latitude=52.52, longitude=13.405, sync_interval_s=10, panel_corner="top-right")
    save_settings(path, s)
    assert load_settings(path) == s
    assert s.location() == Location(52.52, 13.405)


def test_invalid_values_fall_back_per_field(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({
        "autostart": "yes", "language": "fr", "latitude": 95, "longitude": 13,
        "sync_interval_s": 1, "panel_corner": "middle",
    }))
    assert load_settings(path) == Settings()


def test_half_location_is_ignored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"latitude": 52.5}))
    assert load_settings(path).location() is None


def test_corrupt_file_gives_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("[1, 2")
    assert load_settings(path) == Settings()


def test_panel_corner_defaults_to_auto():
    assert Settings().panel_corner == "auto"


def test_resolve_corner():
    from benq_monitor_control.config.settings import resolve_corner

    assert resolve_corner("auto", "top") == "top-right"
    assert resolve_corner("auto", "bottom") == "bottom-right"
    assert resolve_corner("auto", "left") == "bottom-left"
    assert resolve_corner("auto", "right") == "bottom-right"
    assert resolve_corner("auto", None) == "bottom-right"
    assert resolve_corner("top-left", "bottom") == "top-left"
