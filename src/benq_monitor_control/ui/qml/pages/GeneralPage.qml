import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    padding: 20

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Label { text: qsTr("General"); font.pixelSize: 20; font.bold: true }

        Switch {
            text: qsTr("Start automatically after login")
            checked: appSettings.autostart
            onToggled: appSettings.setAutostart(checked)
        }

        RowLayout {
            Label { text: qsTr("Language") }
            ComboBox {
                objectName: "languageBox"
                model: [ { value: "en", text: "English" }, { value: "de", text: "Deutsch" } ]
                textRole: "text"
                valueRole: "value"
                currentIndex: count > 0 ? indexOfValue(appSettings.language) : -1
                onActivated: appSettings.setLanguage(currentValue)
            }
        }

        RowLayout {
            Label { text: qsTr("Quick panel position") }
            ComboBox {
                objectName: "cornerBox"
                model: [
                    { value: "auto", text: qsTr("Automatic (at the system tray)") },
                    { value: "bottom-right", text: qsTr("Bottom right") },
                    { value: "bottom-left", text: qsTr("Bottom left") },
                    { value: "top-right", text: qsTr("Top right") },
                    { value: "top-left", text: qsTr("Top left") }
                ]
                textRole: "text"
                valueRole: "value"
                currentIndex: count > 0 ? indexOfValue(appSettings.panelCorner) : -1
                onActivated: appSettings.setPanelCorner(currentValue)
            }
        }

        RowLayout {
            Label { text: qsTr("Sync interval (s)") }
            SpinBox {
                from: 2
                to: 60
                value: appSettings.syncInterval
                onValueModified: appSettings.setSyncInterval(value)
            }
        }

        Label { text: qsTr("Location for sunrise and sunset"); font.bold: true; Layout.topMargin: 10 }
        RowLayout {
            TextField { id: lat; placeholderText: qsTr("Latitude, e.g. 52.52"); text: appSettings.latitude }
            TextField { id: lon; placeholderText: qsTr("Longitude, e.g. 13.40"); text: appSettings.longitude }
            Button {
                text: qsTr("Save location")
                onClicked: locStatus.text = appSettings.setLocation(lat.text, lon.text)
                    ? qsTr("Location saved.") : qsTr("Invalid coordinates.")
            }
        }
        Button {
            text: qsTr("Import from KDE Night Light")
            onClicked: locStatus.text = appSettings.importFromKde()
                ? qsTr("Location imported.") : qsTr("KDE Night Light has no stored location.")
        }
        Label { id: locStatus; opacity: 0.8 }

        Item { Layout.fillHeight: true }
    }
}
