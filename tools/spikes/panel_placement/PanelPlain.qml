import QtQuick
import QtQuick.Controls

Window {
    id: panel
    width: 340
    height: 420
    visible: false
    color: "transparent"
    flags: Qt.FramelessWindowHint


    onActiveChanged: if (!active) visible = false
    Shortcut { sequence: "Esc"; onActivated: panel.visible = false }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 8
        radius: 10
        color: "#1f2329"
        Column {
            anchors.centerIn: parent
            spacing: 8
            Label { text: "Layer-shell spike"; color: "white" }
            TextField { placeholderText: "type here (keyboard focus?)" }
        }
    }
}
