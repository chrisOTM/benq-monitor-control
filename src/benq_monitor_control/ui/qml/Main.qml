import QtQuick

QtObject {
    id: root

    // Typed as QtObject: PySide6 has no converter for QML window types (see ui.app.as_window).
    property QtObject panel: QuickPanel {
        onOpenSettings: function(page) { root.settingsWindow.showPage(page) }
    }
    property QtObject settingsWindow: SettingsWindow {}

    property var trayTexts: ({
        "open": qsTr("Open panel"),
        "scenarios": qsTr("FloW scenarios"),
        "settings": qsTr("Settings…"),
        "quit": qsTr("Quit"),
        "unreachable": qsTr("Monitor not reachable")
    })
    onTrayTextsChanged: tray.setTexts(trayTexts)
    Component.onCompleted: tray.setTexts(trayTexts)

    property Connections notifications: Connections {
        target: flow
        function onActivated(name, skipped) {
            const body = skipped > 0
                ? qsTr("Scenario %1 activated · %2 action(s) skipped").arg(name).arg(skipped)
                : qsTr("Scenario %1 activated").arg(name)
            tray.notify(qsTr("FloW"), body)
        }
    }
}
