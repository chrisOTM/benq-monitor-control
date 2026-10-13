import json
import re
from pathlib import Path

UI = Path(__file__).parents[2] / "src" / "benq_monitor_control" / "ui"
QSTR = re.compile(r'qsTr\("([^"]*)"')


def qml_strings() -> set[str]:
    found = set()
    for path in (UI / "qml").rglob("*.qml"):
        found.update(QSTR.findall(path.read_text(encoding="utf-8")))
    return found


def test_every_qml_string_has_a_german_translation():
    german = json.loads((UI / "i18n" / "de.json").read_text(encoding="utf-8"))
    missing = sorted(qml_strings() - set(german))
    assert missing == []


def test_no_stale_translations():
    german = json.loads((UI / "i18n" / "de.json").read_text(encoding="utf-8"))
    assert sorted(set(german) - qml_strings()) == []


def test_placeholders_match():
    german = json.loads((UI / "i18n" / "de.json").read_text(encoding="utf-8"))
    for source, target in german.items():
        assert sorted(re.findall(r"%\d", source)) == sorted(re.findall(r"%\d", target)), source
