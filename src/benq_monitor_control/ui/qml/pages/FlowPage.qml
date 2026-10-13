import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    id: page
    padding: 0

    property string selectedId: flow.scenarios.length > 0 ? flow.scenarios[0].id : ""
    property var draft: null

    readonly property var actionTypes: [
        { type: "picture_mode", label: qsTr("Picture mode") },
        { type: "brightness", label: qsTr("Brightness") },
        { type: "volume", label: qsTr("Volume") },
        { type: "low_blue_light", label: qsTr("Low Blue Light") },
        { type: "brightness_intelligence", label: qsTr("Brightness Intelligence") },
        { type: "open_app", label: qsTr("Open application") }
    ]

    function findScenario(id) {
        for (const s of flow.scenarios)
            if (s.id === id) return s
        return null
    }
    function reload() {
        const s = findScenario(selectedId)
        draft = s ? JSON.parse(JSON.stringify(s)) : null
    }
    function edit(mutator) {
        if (!draft) return
        const d = JSON.parse(JSON.stringify(draft))
        mutator(d)
        errorLabel.text = ""
        flow.update(JSON.stringify(d))
    }
    function actionLabel(type) {
        for (const t of actionTypes)
            if (t.type === type) return t.label
        return type
    }
    function maxFor(type) {
        if (type === "volume") return monitor.maxima.volume || 50
        if (type === "low_blue_light") return monitor.maxima.low_blue_light || 5
        return 100
    }
    function defaultAction(type) {
        switch (type) {
        case "picture_mode": return { type: type, value: 15 }
        case "brightness": return { type: type, value: 50 }
        case "volume": return { type: type, value: 20 }
        case "low_blue_light": return { type: type, value: 3 }
        case "brightness_intelligence": return { type: type, value: 1 }
        default: return { type: "open_app", desktop_id: flow.apps.length > 0 ? flow.apps[0].desktop_id : "org.kde.konsole.desktop" }
        }
    }

    onSelectedIdChanged: reload()
    Component.onCompleted: reload()

    Connections {
        target: flow
        function onScenariosChanged() {
            if (!page.findScenario(page.selectedId))
                page.selectedId = flow.scenarios.length > 0 ? flow.scenarios[0].id : ""
            page.reload()
        }
        function onEditError(message) { errorLabel.text = message }
    }

    component ModeEditor: ComboBox {
        property var entry
        property int actionIndex
        model: monitor.pictureModes
        textRole: "label"
        valueRole: "value"
        currentIndex: count > 0 && entry ? indexOfValue(entry.value) : -1
        onActivated: { const i = actionIndex; const v = currentValue; page.edit(d => d.actions[i].value = v) }
    }

    component NumberEditor: ColumnLayout {
        id: numberEditor
        property var entry
        property int actionIndex
        SpinBox {
            from: 0
            to: numberEditor.entry ? page.maxFor(numberEditor.entry.type) : 100
            value: numberEditor.entry ? numberEditor.entry.value : 0
            onValueModified: { const i = numberEditor.actionIndex; const v = value; page.edit(d => d.actions[i].value = v) }
        }
        Label {
            visible: !!numberEditor.entry && numberEditor.entry.type === "low_blue_light"
                     && numberEditor.entry.value > 0 && nightLight.enabled
            text: qsTr("KDE Night Light is enabled — at night both filters add up.")
            wrapMode: Text.WordWrap
            font.pixelSize: 11
            opacity: 0.8
            Layout.fillWidth: true
        }
    }

    component ToggleEditor: Switch {
        property var entry
        property int actionIndex
        checked: entry ? entry.value !== 0 : false
        onToggled: { const i = actionIndex; const v = checked ? 1 : 0; page.edit(d => d.actions[i].value = v) }
    }

    component AppEditor: ComboBox {
        property var entry
        property int actionIndex
        model: flow.apps
        textRole: "name"
        valueRole: "desktop_id"
        currentIndex: count > 0 && entry ? indexOfValue(entry.desktop_id) : -1
        displayText: currentIndex >= 0 ? currentText
                     : (entry ? qsTr("%1 (not installed)").arg(entry.desktop_id) : "")
        onActivated: { const i = actionIndex; const v = currentValue; page.edit(d => d.actions[i].desktop_id = v) }
    }

    Component { id: modeEditor; ModeEditor {} }
    Component { id: numberEditorComponent; NumberEditor {} }
    Component { id: toggleEditor; ToggleEditor {} }
    Component { id: appEditor; AppEditor {} }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        ColumnLayout {
            objectName: "flowList"
            // The ListView fills its column; without these the column would take the whole row.
            Layout.fillWidth: false
            Layout.preferredWidth: 220
            Layout.maximumWidth: 220
            Layout.fillHeight: true
            Layout.margins: 12
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 4
                model: flow.scenarios
                delegate: ItemDelegate {
                    required property var modelData
                    width: ListView.view.width
                    highlighted: modelData.id === page.selectedId
                    text: modelData.name + (modelData.id === flow.activeId ? "  ●" : "")
                    onClicked: page.selectedId = modelData.id
                }
            }
            Button {
                text: qsTr("Add scenario")
                Layout.fillWidth: true
                onClicked: page.selectedId = flow.create(qsTr("New scenario"))
            }
        }

        ToolSeparator { orientation: Qt.Vertical; Layout.fillHeight: true }

        Item {
            objectName: "flowEditor"
            Layout.fillWidth: true
            Layout.fillHeight: true

            Label {
                anchors.centerIn: parent
                visible: page.draft === null
                text: qsTr("No scenario yet. Add one on the left.")
                opacity: 0.7
            }

            ScrollView {
                id: scroll
                anchors.fill: parent
                visible: page.draft !== null
                contentWidth: availableWidth

                ColumnLayout {
                    x: 16
                    width: scroll.availableWidth - 32
                    spacing: 8

                    Label { text: qsTr("Name"); font.bold: true; Layout.topMargin: 16 }
                    TextField {
                        Layout.fillWidth: true
                        text: page.draft ? page.draft.name : ""
                        onEditingFinished: {
                            const name = text.trim()
                            if (page.draft && name !== "" && name !== page.draft.name)
                                page.edit(d => d.name = name)
                        }
                    }

                    Label { text: qsTr("Actions"); font.bold: true; Layout.topMargin: 8 }
                    Label {
                        text: qsTr("Applied from top to bottom; the picture mode always comes first.")
                        wrapMode: Text.WordWrap
                        font.pixelSize: 11
                        opacity: 0.7
                        Layout.fillWidth: true
                    }
                    Repeater {
                        model: page.draft ? page.draft.actions : []
                        delegate: RowLayout {
                            id: row
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            Label { text: page.actionLabel(row.modelData.type); Layout.preferredWidth: 170 }
                            Loader {
                                Layout.fillWidth: true
                                sourceComponent: row.modelData.type === "picture_mode" ? modeEditor
                                    : row.modelData.type === "open_app" ? appEditor
                                    : row.modelData.type === "brightness_intelligence" ? toggleEditor
                                    : numberEditorComponent
                                onLoaded: {
                                    item.entry = Qt.binding(() => row.modelData)
                                    item.actionIndex = Qt.binding(() => row.index)
                                }
                            }
                            ToolButton {
                                text: "↑"
                                enabled: row.index > 0
                                onClicked: { const i = row.index; page.edit(d => d.actions.splice(i - 1, 0, d.actions.splice(i, 1)[0])) }
                            }
                            ToolButton {
                                text: "↓"
                                enabled: page.draft && row.index < page.draft.actions.length - 1
                                onClicked: { const i = row.index; page.edit(d => d.actions.splice(i + 1, 0, d.actions.splice(i, 1)[0])) }
                            }
                            ToolButton {
                                text: "✕"
                                onClicked: { const i = row.index; page.edit(d => d.actions.splice(i, 1)) }
                            }
                        }
                    }
                    RowLayout {
                        ComboBox { id: addType; model: page.actionTypes; textRole: "label"; valueRole: "type" }
                        Button {
                            text: qsTr("Add action")
                            onClicked: { const t = addType.currentValue; page.edit(d => d.actions.push(page.defaultAction(t))) }
                        }
                    }

                    Label { text: qsTr("Schedule"); font.bold: true; Layout.topMargin: 8 }
                    RowLayout {
                        Repeater {
                            model: [
                                { kind: "manual", label: qsTr("Manual") },
                                { kind: "time", label: qsTr("Time") },
                                { kind: "sunset", label: qsTr("Sunset") },
                                { kind: "sunrise", label: qsTr("Sunrise") }
                            ]
                            delegate: RadioButton {
                                required property var modelData
                                text: modelData.label
                                checked: !!page.draft && page.draft.schedule.kind === modelData.kind
                                onToggled: {
                                    if (!checked) return
                                    const k = modelData.kind
                                    page.edit(d => {
                                        d.schedule.kind = k
                                        if (k === "time" && !d.schedule.at) d.schedule.at = "20:00"
                                        if (k !== "time") delete d.schedule.at
                                    })
                                }
                            }
                        }
                    }
                    RowLayout {
                        visible: !!page.draft && page.draft.schedule.kind === "time"
                        Label { text: qsTr("At (HH:MM)") }
                        TextField {
                            text: page.draft && page.draft.schedule.at ? page.draft.schedule.at : ""
                            inputMask: "99:99"
                            onEditingFinished: {
                                const v = text
                                if (/^([01]\d|2[0-3]):[0-5]\d$/.test(v)) page.edit(d => d.schedule.at = v)
                            }
                        }
                    }
                    RowLayout {
                        visible: !!page.draft && page.draft.schedule.kind !== "manual"
                        Label { text: qsTr("Offset (minutes)") }
                        SpinBox {
                            from: -120
                            to: 120
                            value: page.draft ? page.draft.schedule.offset_min : 0
                            onValueModified: { const v = value; page.edit(d => d.schedule.offset_min = v) }
                        }
                    }
                    Label {
                        visible: !!page.draft && (page.draft.schedule.kind === "sunset" || page.draft.schedule.kind === "sunrise")
                        text: flow.sunToday.available
                            ? qsTr("Today: sunrise %1, sunset %2").arg(flow.sunToday.sunrise).arg(flow.sunToday.sunset)
                            : qsTr("Set a location under General to use sunrise and sunset.")
                        wrapMode: Text.WordWrap
                        opacity: 0.8
                        Layout.fillWidth: true
                    }

                    Switch {
                        text: qsTr("Notify me when this scenario is activated")
                        checked: page.draft ? page.draft.notify : false
                        onToggled: { const v = checked; page.edit(d => d.notify = v) }
                    }

                    RowLayout {
                        Layout.topMargin: 8
                        Button { text: qsTr("Activate now"); highlighted: true; onClicked: flow.activate(page.selectedId) }
                        Button { text: qsTr("Delete"); onClicked: confirmDelete.open() }
                    }
                    Label {
                        id: errorLabel
                        visible: text !== ""
                        color: "#d9822b"
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Item { Layout.preferredHeight: 16 }
                }
            }
        }
    }

    Dialog {
        id: confirmDelete
        title: qsTr("Delete scenario?")
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        x: (page.width - width) / 2
        y: (page.height - height) / 2
        onAccepted: flow.remove(page.selectedId)
    }
}
