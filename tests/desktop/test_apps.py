from benq_monitor_control.desktop.apps import AppEntry, launch, list_apps, resolve


def write(directory, name, body):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(body)


ENTRY = "[Desktop Entry]\nType=Application\nName={name}\nExec=x\n{extra}"


def test_list_apps_filters_and_sorts(tmp_path):
    user, system = tmp_path / "user", tmp_path / "system"
    write(system, "b.desktop", ENTRY.format(name="Bravo", extra=""))
    write(system, "a.desktop", ENTRY.format(name="alpha", extra=""))
    write(system, "hidden.desktop", ENTRY.format(name="Hidden", extra="NoDisplay=true\n"))
    write(system, "link.desktop", "[Desktop Entry]\nType=Link\nName=Link\n")
    write(system, "shadowed.desktop", ENTRY.format(name="System copy", extra=""))
    write(user, "shadowed.desktop", ENTRY.format(name="User copy", extra=""))
    write(system, "removed.desktop", ENTRY.format(name="Removed", extra=""))
    write(user, "removed.desktop", ENTRY.format(name="Removed", extra="Hidden=true\n"))
    write(system, "actions.desktop", ENTRY.format(name="Main", extra="[Desktop Action new]\nName=Other\n"))
    apps = list_apps([user, system])
    assert [a.name for a in apps] == ["alpha", "Bravo", "Main", "User copy"]
    assert apps[0] == AppEntry("a.desktop", "alpha", system / "a.desktop")


def test_resolve_and_launch(tmp_path):
    write(tmp_path, "spotify.desktop", ENTRY.format(name="Spotify", extra=""))
    calls = []
    assert resolve("spotify.desktop", [tmp_path]) == tmp_path / "spotify.desktop"
    assert launch("spotify.desktop", [tmp_path], popen=lambda args, **kw: calls.append(args))
    assert calls == [["gio", "launch", str(tmp_path / "spotify.desktop")]]


def test_launch_missing_or_failing(tmp_path):
    assert not launch("gone.desktop", [tmp_path], popen=lambda *a, **k: None)
    write(tmp_path, "x.desktop", ENTRY.format(name="X", extra=""))

    def broken(*args, **kwargs):
        raise OSError("gio missing")

    assert not launch("x.desktop", [tmp_path], popen=broken)
