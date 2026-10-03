"""overlay 补丁 ops —— 随功能包版本走（原来放在加载器 integrations.py 里）。

本文件由 ast 从 integrations.py 精确抽取，未改一个字符。
加载器不再持有这些锚点：功能包自己带着它对应主程序版本的补丁。
"""

_ADD_MEMBER_OLD = """                    text: qsTr("Add Member")
                    onClicked: addOverlayMemberDialog.open()"""

_ADD_MEMBER_NEW = """                    text: qsTr("Add Member")
                    onClicked: {
                        // 正在编辑的堆叠组件实例 → 成员加到该实例下
                        addOverlayMemberDialog.overlayInstanceId = model.instanceId
                        addOverlayMemberDialog.open()
                    }"""

_OVERLAY_LAYOUT_OPS = [
    ("import ClassWidgets.Easing",
     'import ClassWidgets.Easing\nimport "dialogs"'),
    ("    property bool editMode: false",
     "    property bool editMode: false\n"
     "    // 堆叠插件集成：正在编辑的堆叠组件实例 id（按实例隔离）\n"
     "    property string overlayEditingId: ''"),
    ("""            host: layoutRoot
            settingsDialog: settingsDialogInstance""",
     """            host: layoutRoot
            // 堆叠插件集成：成员选择窗口按属性注入（跨组件文件不能用 id 直引）
            overlayMemberDialog: overlayMemberDialogInstance
            settingsDialog: settingsDialogInstance"""),
    ("""    WidgetSettingsDialog {
        // 独立 id，避免与 delegate 的同名属性形成自引用
        id: settingsDialogInstance
    }""",
     """    WidgetSettingsDialog {
        // 独立 id，避免与 delegate 的同名属性形成自引用
        id: settingsDialogInstance
    }

    // 堆叠插件集成：成员选择窗口（按需加载，窗口缺失/不兼容也不影响主界面启动）
    Loader {
        id: overlayMemberDialogInstance
        source: "dialogs/AddOverlayMemberDialog.qml"
        active: false
    }"""),
]

_OVERLAY_DELEGATE_OPS = [
    ("import QtQuick.Controls\nimport RinUI",
     "import QtQuick.Controls\nimport QtQuick.Layouts\nimport RinUI"),
    ("    property bool initialized: false   // 入场只播一次，避免切主题重播",
     "    property bool initialized: false   // 入场只播一次，避免切主题重播\n"
     "    // 堆叠插件集成：本实例是不是堆叠组件、是不是正在编辑它的成员\n"
     '    property bool isOverlay: model.typeId === "com.overlay"\n'
     "    property bool overlayEditing: isOverlay && host.overlayEditingId === model.instanceId\n"
     "    property var overlayMemberDialog: null"),
    ("    rotation: host.editMode ? shakeAngle : 0",
     "    rotation: (host.editMode && !widgetContainer.overlayEditing) ? shakeAngle : 0"),
    ("""        function onVisibleChanged() { widgetContainer.syncNaturalSize() }
        function onWidthChanged()   { widgetContainer.syncNaturalSize() }
        function onHeightChanged()  { widgetContainer.syncNaturalSize() }
    }""",
     """        function onVisibleChanged() { widgetContainer.syncNaturalSize() }
        function onWidthChanged()   { widgetContainer.syncNaturalSize() }
        function onHeightChanged()  { widgetContainer.syncNaturalSize() }
    }

    // 堆叠插件集成：编辑状态变化时，把 overlayListMode 通知给组件实例
    onOverlayEditingChanged: {
        if (widgetContainer.isOverlay && loader.item)
            loader.item.overlayListMode = widgetContainer.overlayEditing
    }"""),
    ("""        MenuItem {
            icon.name: "ic_fluent_delete_20_regular"
            text: qsTr("Delete")""",
     """        MenuItem {
            // 堆叠插件集成：编辑其内部成员
            visible: widgetContainer.isOverlay
            icon.name: "ic_fluent_layers_20_regular"
            text: qsTr("编辑成员组件")
            onTriggered: {
                widgetMenu.close()
                host.editRequested()
                host.overlayEditingId = model.instanceId
            }
        }
        MenuItem {
            icon.name: "ic_fluent_delete_20_regular"
            text: qsTr("Delete")"""),
    ("""    ToolButton {
        id: deleteBtn""",
     """    // 堆叠插件集成：成员编辑行（Add Member / Done）
    RowLayout {
        id: editRow
        objectName: "editRow"
        visible: widgetContainer.overlayEditing
        anchors.top: loader.bottom
        anchors.topMargin: 10
        anchors.horizontalCenter: parent.horizontalCenter
        width: implicitWidth
        height: implicitHeight
        spacing: 8

        Button {
            id: addOverlayMemberButton
            icon.name: "ic_fluent_add_20_regular"
            text: qsTr("Add Member")
            onClicked: {
                var dlg = widgetContainer.overlayMemberDialog
                if (dlg) {
                    dlg.active = true
                    if (dlg.item) {
                        dlg.item.overlayInstanceId = model.instanceId
                        dlg.item.open()
                    }
                }
            }
        }

        Button {
            id: acceptOverlayButton
            highlighted: true
            icon.name: "ic_fluent_checkmark_20_regular"
            text: qsTr("Done")
            onClicked: { host.editMode = false; host.overlayEditingId = '' }
        }
    }

    ToolButton {
        id: deleteBtn"""),
    ("""    TapHandler {
        acceptedButtons: Qt.RightButton""",
     """    TapHandler {
        acceptedButtons: Qt.RightButton
        // 堆叠插件集成：编辑成员时禁用（成员自己的右键交给 overlay 处理）
        enabled: !widgetContainer.overlayEditing"""),
    ("""    SequentialAnimation on shakeAngle {
        running: host.editMode""",
     """    SequentialAnimation on shakeAngle {
        running: host.editMode && !widgetContainer.overlayEditing"""),
]

_CONTAINER_OVERLAY_OPS = [
    ("import ClassWidgets.Easing",
     "import ClassWidgets.Easing\nimport \"dialogs\""),
    ("    property bool editMode: false",
     """    property bool editMode: false
    // 堆叠插件集成：正在编辑的堆叠组件实例 id（按实例隔离，就地展开）
    property string overlayEditingId: ''"""),
    (["""                MenuItem {
                    icon.name: "ic_fluent_delete_20_regular"
                    text: qsTr("Delete")""",
      """                    MenuItem {
                        icon.name: "ic_fluent_delete_20_regular"
                        text: qsTr("Delete")"""],
     """                MenuItem {
                    // 堆叠插件集成：编辑其内部成员
                    visible: model.typeId === "com.overlay"
                    icon.name: "ic_fluent_layers_20_regular"
                    text: qsTr("编辑成员组件")
                    onTriggered: {
                        widgetMenu.close()
                        widgetsContainer.editMode = true
                        widgetsContainer.overlayEditingId = model.instanceId
                    }
                }
                MenuItem {
                    icon.name: "ic_fluent_delete_20_regular"
                    text: qsTr("Delete")"""),
    (["""            property real visualScale: scaleFactor
            width: loader.width * visualScale
            height: loader.height * visualScale""",
      """                property real visualScale: scaleFactor
                width: loader.width * visualScale
                height: loader.height * visualScale"""],
     """            // 堆叠插件集成：编辑时独占一行（大组件），下方展开编辑行
            property bool isOverlay: model.typeId === "com.overlay"
            property bool overlayEditing: widgetsContainer.overlayEditingId === model.instanceId && isOverlay
            property real visualScale: scaleFactor
            width: overlayEditing
                ? Math.max((widgetsContainer.parent ? widgetsContainer.parent.width - 16 : 0),
                           loader.width * visualScale)
                : loader.width * visualScale
            height: loader.height * visualScale
                + (overlayEditing ? editRow.height + 10 : 0)"""),
    (["""            ToolButton {
                id: deleteBtn""",
      """                ToolButton {
                    id: deleteBtn"""],
     """            // 堆叠插件集成：成员编辑行（Add Member / Done）
            RowLayout {
                id: editRow
                objectName: "editRow"
                visible: widgetContainer.overlayEditing
                anchors.top: loader.bottom
                anchors.topMargin: 10
                anchors.horizontalCenter: parent.horizontalCenter
                width: implicitWidth
                height: implicitHeight
                spacing: 8

                Button {
                    id: addOverlayMemberButton
                    icon.name: "ic_fluent_add_20_regular"
                    text: qsTr("Add Member")
                    onClicked: {
                        // 正在编辑的堆叠组件实例 → 成员加到该实例下
                        addOverlayMemberDialog.overlayInstanceId = model.instanceId
                        addOverlayMemberDialog.open()
                    }
                }

                Button {
                    id: acceptOverlayButton
                    highlighted: true
                    icon.name: "ic_fluent_checkmark_20_regular"
                    text: qsTr("Done")
                    onClicked: {
                        widgetsContainer.overlayEditingId = ''
                    }
                }
            }

            ToolButton {
                id: deleteBtn"""),
    ("            rotation: editMode",
     "            rotation: editMode && !widgetContainer.overlayEditing"),
    ("                running: editMode",
     "                running: editMode && !widgetContainer.overlayEditing"),
    (["""            // 鼠标右键打开设置
            TapHandler {
                acceptedButtons: Qt.RightButton""",
      """                // 鼠标右键打开设置
                TapHandler {
                    acceptedButtons: Qt.RightButton"""],
     """            // 鼠标右键打开设置（编辑堆叠时禁用，成员右键由 overlay 内部处理）
            TapHandler {
                acceptedButtons: Qt.RightButton
                enabled: !widgetContainer.overlayEditing"""),
    ("onClicked: widgetsContainer.editMode = false",
     "onClicked: { widgetsContainer.editMode = false; widgetsContainer.overlayEditingId = '' }"),
    ("""    // 小组件设置窗口
    WidgetSettingsDialog {
        id: settingsDialog
    }""",
     """    // 小组件设置窗口
    WidgetSettingsDialog {
        id: settingsDialog
    }

    // 堆叠插件集成：成员选择窗口
    AddOverlayMemberDialog {
        id: addOverlayMemberDialog
    }"""),
    ("""            visible: widgetsContainer.editMode
            id: acceptButton""",
     """            visible: widgetsContainer.editMode && widgetsContainer.overlayEditingId === ''
            id: acceptButton"""),
    ("""        visible: widgetsContainer.editMode || widgetRepeater.count === 0""",
     """        visible: (widgetsContainer.editMode || widgetRepeater.count === 0)
            && widgetsContainer.overlayEditingId === ''"""),
    (_ADD_MEMBER_OLD, _ADD_MEMBER_NEW),
]

_OVERLAY_CONTAINER_V2_OPS = [
    ("""            visible: widgetsContainer.editMode
            id: acceptButton""",
     """            visible: widgetsContainer.editMode && widgetsLayout.overlayEditingId === ''
            id: acceptButton"""),
    ("""        visible: widgetsContainer.editMode || widgetsLayout.count === 0""",
     """        visible: (widgetsContainer.editMode || widgetsLayout.count === 0)
            && widgetsLayout.overlayEditingId === ''"""),
]

_WLOADER_OPS = [
    # v2（2.0.0.dev20260928 起）：WidgetLoader.qml 里 editMode 是属性、onEditModeChanged 是信号，
    # 且没有 host/widgetsContainer/anim.start()。给加载器补一个 overlayEditingId 属性 + 处理器，
    # 并在 Ready 时把 overlayListMode 传给组件本体。锚点整段带后续行，保证重复应用不叠加。
    ("""    property bool editMode: false

    signal contentLoading()""",
     """    property bool editMode: false
    property string overlayEditingId: ""

    onOverlayEditingIdChanged: {
        if (loader.item && loader.item.hasOwnProperty("overlayListMode"))
            loader.item.overlayListMode = overlayEditingId === model.instanceId
    }

    signal contentLoading()"""),
    ("""            if (item && item.hasOwnProperty("editMode")) {
                item.editMode = editMode
            }
            contentLoaded()""",
     """            if (item && item.hasOwnProperty("editMode")) {
                item.editMode = editMode
            }
            if (item && item.hasOwnProperty("overlayListMode")) {
                item.overlayListMode = overlayEditingId === model.instanceId
            }
            contentLoaded()"""),
]
