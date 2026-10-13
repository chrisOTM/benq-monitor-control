import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "pages"

ApplicationWindow {
    id: win
    title: qsTr("Settings")  // Qt appends the application display name
    width: 860
    height: 560
    minimumWidth: 720
    minimumHeight: 480
    visible: false

    readonly property var pageKeys: ["monitor", "flow", "general", "colour", "info"]

    function showPage(page) {
        const index = pageKeys.indexOf(page)
        nav.currentIndex = index >= 0 && page !== "colour" ? index : 0
        win.show()
        win.raise()
        win.requestActivate()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        ListView {
            id: nav
            Layout.preferredWidth: 170
            Layout.fillHeight: true
            model: [
                { key: "monitor", label: qsTr("Monitor") },
                { key: "flow", label: qsTr("FloW") },
                { key: "general", label: qsTr("General") },
                { key: "colour", label: qsTr("Colour (v2)") },
                { key: "info", label: qsTr("Info") }
            ]
            delegate: ItemDelegate {
                required property var modelData
                required property int index
                width: ListView.view.width
                text: modelData.label
                enabled: modelData.key !== "colour"
                highlighted: ListView.isCurrentItem
                onClicked: nav.currentIndex = index
            }
        }

        ToolSeparator { orientation: Qt.Vertical; Layout.fillHeight: true }

        StackLayout {
            currentIndex: nav.currentIndex
            Layout.fillWidth: true
            Layout.fillHeight: true
            MonitorPage {}
            FlowPage {}
            GeneralPage {}
            Item {}
            InfoPage {}
        }
    }
}
