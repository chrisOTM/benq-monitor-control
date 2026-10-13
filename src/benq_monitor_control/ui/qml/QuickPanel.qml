import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.layershell as LayerShell

Window {
    id: panel

    signal openSettings(string page)
    property int pendingInput: -1

    width: 340
    height: content.implicitHeight + 40
    visible: false
    color: "transparent"
    flags: Qt.FramelessWindowHint
    title: "BenQ Monitor Control"

    LayerShell.Window.scope: "benq-monitor-control-panel"
    LayerShell.Window.layer: LayerShell.Window.LayerTop
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityOnDemand
    LayerShell.Window.anchors: cornerAnchors(appSettings.effectiveCorner)

    function cornerAnchors(corner) {
        const W = LayerShell.Window
        switch (corner) {
        case "bottom-left": return W.AnchorBottom | W.AnchorLeft
        case "top-right": return W.AnchorTop | W.AnchorRight
        case "top-left": return W.AnchorTop | W.AnchorLeft
        default: return W.AnchorBottom | W.AnchorRight
        }
    }

    onActiveChanged: if (!active) visible = false
    onVisibleChanged: {
        if (visible) { nightLight.refresh(); appSettings.refreshPanelEdge() }
        else monitor.cancelDrags()  // a release lost while hiding must not block polling
    }

    SystemPalette { id: sys; colorGroup: SystemPalette.Active }
    Shortcut { sequence: "Esc"; onActivated: panel.visible = false }

    component SectionLabel: Label {
        font.pixelSize: 11
        font.capitalization: Font.AllUppercase
        opacity: 0.7
        Layout.topMargin: 6
    }

    component FeatureSlider: RowLayout {
        id: fs
        required property string feature
        required property string caption
        property int current: 0
        property int maximum: 100
        property bool locked: false
        property var formatValue: function(v) { return String(v) }
        Layout.fillWidth: true
        Label { text: fs.caption; Layout.preferredWidth: 120 }
        Slider {
            id: slider
            Layout.fillWidth: true
            from: 0
            to: fs.maximum
            stepSize: 1
            snapMode: Slider.SnapAlways
            enabled: monitor.reachable && !fs.locked
            value: fs.current
            onMoved: monitor.setValue(fs.feature, Math.round(value))
            onPressedChanged: pressed ? monitor.beginDrag(fs.feature) : monitor.endDrag(fs.feature)
        }
        Connections {
            target: monitor
            // Re-attach the binding so a refused value snaps back to what the monitor reports.
            function onWriteFailed(feature, reason) {
                if (feature === fs.feature) slider.value = Qt.binding(() => fs.current)
            }
        }
        Label {
            text: fs.formatValue(Math.round(slider.value))
            Layout.preferredWidth: 32
            horizontalAlignment: Text.AlignRight
        }
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 8
        radius: 10
        color: sys.window
        border.color: Qt.darker(sys.window, 1.3)

        ColumnLayout {
            id: content
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
            spacing: 6

            RowLayout {
                Layout.fillWidth: true
                Rectangle { width: 8; height: 8; radius: 4; color: monitor.reachable ? "#3ccf6e" : "#9aa0a6" }
                Label { text: monitor.displayName; font.bold: true; Layout.fillWidth: true }
                ComboBox {
                    id: inputBox
                    objectName: "inputBox"
                    enabled: monitor.reachable
                    model: monitor.inputs
                    textRole: "label"
                    valueRole: "value"
                    currentIndex: count > 0 ? indexOfValue(monitor.inputSource) : -1
                    onActivated: function(index) {
                        if (valueAt(index) !== monitor.inputSource)
                            panel.pendingInput = valueAt(index)
                        currentIndex = Qt.binding(() => count > 0 ? indexOfValue(monitor.inputSource) : -1)
                    }
                }
            }

            RowLayout {
                visible: panel.pendingInput >= 0
                Layout.fillWidth: true
                Label {
                    text: qsTr("Switch input? This computer loses control of the monitor.")
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                Button {
                    text: qsTr("Switch")
                    onClicked: { monitor.setValue("input_source", panel.pendingInput); panel.pendingInput = -1 }
                }
                Button { text: qsTr("Cancel"); onClicked: panel.pendingInput = -1 }
            }

            Label {
                visible: !monitor.reachable
                text: monitor.errorText !== "" ? monitor.errorText : qsTr("Monitor not reachable")
                color: "#d9822b"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            SectionLabel { text: qsTr("Picture mode") }
            GridLayout {
                columns: 3
                columnSpacing: 5
                rowSpacing: 5
                Layout.fillWidth: true
                Repeater {
                    model: monitor.pictureModes
                    delegate: Button {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.label
                        // org.kde.desktop draws neither "highlighted" nor "checked" on non-checkable buttons.
                        checkable: true
                        checked: monitor.pictureMode === modelData.value
                        enabled: monitor.reachable && !monitor.locked.picture_mode
                        onClicked: {
                            monitor.setValue("picture_mode", modelData.value)
                            checked = Qt.binding(() => monitor.pictureMode === modelData.value)  // clicking toggled it
                        }
                    }
                }
            }
            Label { visible: monitor.hdrActive; text: qsTr("HDR signal active"); font.bold: true }

            SectionLabel { text: qsTr("Picture & sound") }
            FeatureSlider {
                feature: "brightness"
                caption: qsTr("Brightness")
                current: monitor.brightness
                maximum: monitor.maxima.brightness || 100
                locked: !!monitor.locked.brightness
            }
            FeatureSlider {
                feature: "volume"
                caption: qsTr("Volume")
                current: monitor.volume
                maximum: monitor.maxima.volume || 50
                locked: !!monitor.locked.volume
            }

            SectionLabel { text: qsTr("Eye care") }
            FeatureSlider {
                feature: "low_blue_light"
                caption: qsTr("Low Blue Light")
                current: monitor.lowBlueLight
                maximum: monitor.maxima.low_blue_light || 5
                locked: !!monitor.locked.low_blue_light
                formatValue: function(v) { return v === 0 ? qsTr("Off") : String(v) }
            }
            Label {
                visible: nightLight.warming && monitor.lowBlueLight > 0
                text: qsTr("KDE Night Light is active — the effects add up.")
                wrapMode: Text.WordWrap
                font.pixelSize: 11
                opacity: 0.8
                Layout.fillWidth: true
            }
            RowLayout {
                Layout.fillWidth: true
                Label { text: qsTr("Brightness Intelligence"); Layout.fillWidth: true }
                Switch {
                    id: biSwitch
                    enabled: monitor.reachable && !monitor.locked.brightness_intelligence
                    checked: monitor.brightnessIntelligence !== 0
                    onToggled: monitor.setValue("brightness_intelligence", checked ? 1 : 0)
                    Connections {
                        target: monitor
                        function onWriteFailed(feature, reason) {
                            if (feature === "brightness_intelligence")
                                biSwitch.checked = Qt.binding(() => monitor.brightnessIntelligence !== 0)
                        }
                    }
                }
            }

            Label {
                id: hint
                visible: text !== ""
                color: "#d9822b"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Timer { id: hintTimer; interval: 3000; onTriggered: hint.text = "" }
            }
            Connections {
                target: monitor
                function onWriteFailed(feature, reason) {
                    hint.text = (reason === "locked" || reason === "rejected")
                        ? qsTr("Not available in the current picture mode.")
                        : qsTr("The monitor did not accept the change.")
                    hintTimer.restart()
                }
            }

            SectionLabel { text: qsTr("FloW") }
            Flow {
                Layout.fillWidth: true
                spacing: 5
                Repeater {
                    model: flow.scenarios
                    delegate: Button {
                        required property var modelData
                        text: modelData.name
                        checkable: true
                        checked: flow.activeId === modelData.id
                        onClicked: {
                            flow.activate(modelData.id)
                            checked = Qt.binding(() => flow.activeId === modelData.id)
                        }
                    }
                }
                Button { text: "+"; onClicked: { panel.visible = false; panel.openSettings("flow") } }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 6
                Button {
                    text: qsTr("Settings")
                    flat: true
                    onClicked: { panel.visible = false; panel.openSettings("monitor") }
                }
                Item { Layout.fillWidth: true }
                Label {
                    visible: flow.activeName !== ""
                    text: flow.activeUntil !== ""
                        ? qsTr("FloW: %1 until %2").arg(flow.activeName).arg(flow.activeUntil)
                        : qsTr("FloW: %1").arg(flow.activeName)
                    font.pixelSize: 11
                    opacity: 0.7
                }
            }
        }
    }
}
