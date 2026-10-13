from benq_monitor_control.desktop.kde import night_light_location
from benq_monitor_control.flow.sun import Location


def test_fixed_location(tmp_path):
    rc = tmp_path / "kwinrc"
    rc.write_text("[NightColor]\nActive=true\nLatitudeFixed=52.52\nLongitudeFixed=13.405\nMode=Location\n")
    assert night_light_location(rc) == Location(52.52, 13.405)


def test_auto_location_fallback(tmp_path):
    rc = tmp_path / "kwinrc"
    rc.write_text("[NightColor]\nLatitudeAuto=48.1\nLongitudeAuto=11.6\n")
    assert night_light_location(rc) == Location(48.1, 11.6)


def test_no_location_stored(tmp_path):
    rc = tmp_path / "kwinrc"
    rc.write_text("[NightColor]\nActive=true\nNightTemperature=4000\n\n[Plugins]\ncubeEnabled=true\n")
    assert night_light_location(rc) is None


def test_missing_or_broken_file(tmp_path):
    assert night_light_location(tmp_path / "nope") is None
    rc = tmp_path / "kwinrc"
    rc.write_text("[NightColor]\nLatitudeFixed=abc\nLongitudeFixed=13\n")
    assert night_light_location(rc) is None


APPLETSRC = """[Containments][144]
formfactor=2
location=3
plugin=org.kde.panel

[Containments][144][Applets][150]
plugin=org.kde.plasma.systemtray

[Containments][168]
formfactor=2
location=4
plugin=org.kde.panel

[Containments][168][Applets][170]
plugin=org.kde.plasma.pager

[Containments][1]
location=0
plugin=org.kde.plasma.folder
"""


def test_tray_panel_edge_finds_panel_with_system_tray(tmp_path):
    from benq_monitor_control.desktop.kde import tray_panel_edge

    rc = tmp_path / "appletsrc"
    rc.write_text(APPLETSRC)
    assert tray_panel_edge(rc) == "top"
    rc.write_text(APPLETSRC.replace("location=3", "location=6"))
    assert tray_panel_edge(rc) == "right"


def test_tray_panel_edge_unknown(tmp_path):
    from benq_monitor_control.desktop.kde import tray_panel_edge

    assert tray_panel_edge(tmp_path / "missing") is None
    rc = tmp_path / "appletsrc"
    rc.write_text(APPLETSRC.replace("org.kde.plasma.systemtray", "org.kde.plasma.clock"))
    assert tray_panel_edge(rc) is None
