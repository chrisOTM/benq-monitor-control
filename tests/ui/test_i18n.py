import json

from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from benq_monitor_control.ui.i18n import DictTranslator, LanguageManager, load_mapping


def test_dict_translator_python_and_qml(qapp):
    translator = DictTranslator({"Settings": "Einstellungen", "Scenario %1 activated": "Szenario %1 aktiviert"})
    qapp.installTranslator(translator)
    try:
        assert QCoreApplication.translate("ctx", "Settings") == "Einstellungen"
        assert QCoreApplication.translate("ctx", "Untranslated") == "Untranslated"
        engine = QQmlEngine()
        component = QQmlComponent(engine)
        component.setData(
            b'import QtQml\nQtObject { property string a: qsTr("Scenario %1 activated").arg("Abend") }',
            QUrl("inline.qml"),
        )
        obj = component.create()
        assert obj.property("a") == "Szenario Abend aktiviert"
    finally:
        qapp.removeTranslator(translator)


def test_language_manager_switches(qapp, tmp_path):
    (tmp_path / "de.json").write_text(json.dumps({"Quit": "Beenden"}))
    manager = LanguageManager(qapp, directory=tmp_path)
    manager.apply("de")
    assert QCoreApplication.translate("ctx", "Quit") == "Beenden"
    manager.apply("en")
    assert QCoreApplication.translate("ctx", "Quit") == "Quit"
    assert manager.language == "en"


def test_load_mapping_missing_or_broken(tmp_path):
    assert load_mapping("de", tmp_path) == {}
    (tmp_path / "de.json").write_text("{broken")
    assert load_mapping("de", tmp_path) == {}
    assert load_mapping("en", tmp_path) == {}
