import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    padding: 20

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        Label { text: "BenQ Monitor Control " + appInfo.version; font.pixelSize: 20; font.bold: true }
        Label { text: qsTr("Made by chrisOTM.") }
        Label {
            text: "<a href=\"https://github.com/chrisOTM\">github.com/chrisOTM</a>"
            onLinkActivated: function(link) { Qt.openUrlExternally(link) }
        }
        Label { text: qsTr("License: MIT") }
        Label {
            text: qsTr("Not affiliated with BenQ. BenQ and MA320U are trademarks of BenQ Corporation.")
            wrapMode: Text.WordWrap
            opacity: 0.8
            Layout.fillWidth: true
        }
        Item { Layout.fillHeight: true }
    }
}
