import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    padding: 20

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        Label { text: qsTr("Monitor"); font.pixelSize: 20; font.bold: true }

        GridLayout {
            columns: 2
            columnSpacing: 16
            rowSpacing: 6
            Layout.fillWidth: true
            Label { text: qsTr("Model") }
            Label { text: monitor.displayName }
            Label { text: qsTr("Status") }
            Label {
                text: monitor.reachable
                    ? qsTr("Connected")
                    : (monitor.errorText !== "" ? monitor.errorText : qsTr("Monitor not reachable"))
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Label { text: qsTr("I²C bus") }
            Label { text: monitor.bus >= 0 ? "/dev/i2c-" + monitor.bus : "–" }
            Label { text: qsTr("Firmware") }
            Label { text: monitor.firmware !== "" ? monitor.firmware : "–" }
        }

        Label { text: qsTr("Current values"); font.bold: true; Layout.topMargin: 10 }
        Repeater {
            model: Object.keys(monitor.rawValues)
            delegate: Label {
                required property string modelData
                text: modelData + ": " + monitor.rawValues[modelData]
                font.family: "monospace"
            }
        }

        Button { text: qsTr("Detect again"); onClicked: monitor.redetect() }
        Item { Layout.fillHeight: true }
    }
}
