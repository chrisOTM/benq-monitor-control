from benq_monitor_control.desktop.autostart import autostart_enabled, autostart_file, set_autostart


def test_enable_and_disable(tmp_path):
    assert not autostart_enabled(tmp_path)
    set_autostart(True, tmp_path)
    path = autostart_file(tmp_path)
    assert path == tmp_path / "autostart" / "benq-monitor-control.desktop"
    assert "Exec=benq-monitor-control" in path.read_text()
    assert autostart_enabled(tmp_path)
    set_autostart(False, tmp_path)
    assert not autostart_enabled(tmp_path)
    set_autostart(False, tmp_path)  # idempotent
