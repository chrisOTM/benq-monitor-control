import QtQuick
import QtQuick.Controls
import org.kde.layershell as LayerShell

Window {
    id: panel
    width: 340
    height: 420
    visible: false
    color: "transparent"
    flags: Qt.FramelessWindowHint

    LayerShell.Window.scope: "benq-spike"
    LayerShell.Window.layer: LayerShell.Window.LayerTop
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorRight
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityOnDemand

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
