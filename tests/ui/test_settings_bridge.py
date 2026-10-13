from benq_monitor_control.config.settings import Settings, load_settings
from benq_monitor_control.flow.sun import Location
from benq_monitor_control.ui.settings_bridge import SettingsBridge


def make(tmp_path, **kwargs):
    calls = {"language": [], "location": 0, "sync": [], "autostart": []}
    bridge = SettingsBridge(
        Settings(),
        tmp_path / "settings.json",
        on_language=calls["language"].append,
        on_location=lambda: calls.__setitem__("location", calls["location"] + 1),
        on_sync_interval=calls["sync"].append,
        autostart_fn=calls["autostart"].append,
        autostart_state=lambda: False,
        **kwargs,
    )
    return bridge, calls


def test_set_location_accepts_comma_and_persists(qapp, tmp_path):
    bridge, calls = make(tmp_path)
    assert bridge.setLocation("52,52", " 13.405 ")
    assert bridge.location() == Location(52.52, 13.405)
    assert bridge.latitude == "52.52" and bridge.hasLocation
    assert load_settings(tmp_path / "settings.json").location() == Location(52.52, 13.405)
    assert calls["location"] == 1


def test_set_location_rejects_invalid_and_clears(qapp, tmp_path):
    bridge, calls = make(tmp_path)
    assert not bridge.setLocation("abc", "13")
    assert not bridge.setLocation("95", "13")
    assert calls["location"] == 0
    assert bridge.setLocation("52.5", "13.4")
    assert bridge.setLocation("", "")
    assert bridge.location() is None and bridge.latitude == ""


def test_import_from_kde(qapp, tmp_path):
    rc = tmp_path / "kwinrc"
    rc.write_text("[NightColor]\nLatitudeFixed=48.1\nLongitudeFixed=11.6\n")
    bridge, calls = make(tmp_path, kwinrc=rc)
    assert bridge.importFromKde()
    assert bridge.location() == Location(48.1, 11.6) and calls["location"] == 1
    rc.write_text("[NightColor]\nActive=true\n")
    assert not bridge.importFromKde()


def test_language_sync_corner_autostart(qapp, tmp_path):
    bridge, calls = make(tmp_path)
    bridge.setLanguage("de")
    bridge.setLanguage("fr")
    assert calls["language"] == ["de"] and bridge.language == "de"
    bridge.setSyncInterval(100)
    assert bridge.syncInterval == 60 and calls["sync"] == [60]
    bridge.setPanelCorner("top-left")
    bridge.setPanelCorner("middle")
    assert bridge.panelCorner == "top-left"
    bridge.setAutostart(True)
    assert calls["autostart"] == [True] and bridge.autostart
    saved = load_settings(tmp_path / "settings.json")
    assert (saved.language, saved.sync_interval_s, saved.panel_corner, saved.autostart) == ("de", 60, "top-left", True)


def test_effective_corner_follows_tray_edge(qapp, tmp_path):
    edge = {"value": "top"}
    bridge, _ = make(tmp_path, panel_edge=lambda: edge["value"])
    assert bridge.panelCorner == "auto" and bridge.effectiveCorner == "top-right"
    changes = []
    bridge.changed.connect(lambda: changes.append(1))
    bridge.refreshPanelEdge()
    assert changes == []  # unchanged edge, no signal
    edge["value"] = "bottom"
    bridge.refreshPanelEdge()
    assert bridge.effectiveCorner == "bottom-right" and changes == [1]
    bridge.setPanelCorner("top-left")
    assert bridge.effectiveCorner == "top-left"
