import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import RinUI


// 「组件增强」功能的设置页 —— 装了它才会出现。
// 这些开关原本长在插件主设置页里，会让人以为它们是插件自带功能；现在跟
// 「组件动画」「时间组件」一样，归到功能自己名下：装了才有、才有意义。
ColumnLayout {
    id: root
    spacing: 0

    // 宿主在 Loader 加载后注入插件对象（见 settings.qml 的 onLoaded）
    property var backend: null

    property var info: ({})
    property bool syncingControls: false
    // 排除科目（按课表所选科目判定，与课程标题无关）
    property bool excludedEnabled: false
    property var excludedSubjects: []
    property var subjectChoices: []

    Component.onCompleted: Qt.callLater(reload)
    onBackendChanged: { if (backend) Qt.callLater(reload) }

    Connections {
        target: backend
        function onConfigChanged() { root.reload() }
    }

    function reload() {
        if (!backend) return
        var newInfo = backend.getConfig()
        if (newInfo) info = newInfo
        syncControls()
        reloadExcluded()
    }

    function syncControls() {
        root.syncingControls = true
        var d = info.display_height
        displaySlider.value = (d !== undefined && d !== null && d >= 0)
            ? d : (Configs.data.preferences.widgets_offset_y || 0)
        var hd = info.hide_depth
        hideSlider.value = (hd !== undefined && hd !== null) ? hd : 24
        root.syncingControls = false
    }

    function saveExcluded() {
        if (backend) backend.setExcludedLessonConfig(
            excludedEnabledSwitch.checked, root.excludedSubjects)
    }

    function reloadExcluded() {
        if (!backend) return
        var cfg = backend.getExcludedLessonConfig()
        root.excludedEnabled = cfg ? (cfg.enabled === true) : false
        root.excludedSubjects = (cfg && cfg.subjects) ? cfg.subjects.slice() : []
    }

    function allSubjectNames() {
        var out = []
        try {
            var s = AppCentral.scheduleRuntime.subjects || []
            for (var i = 0; i < s.length; i++) out.push(s[i].name)
        } catch (e) {}
        return out
    }

    function refreshSubjectMenu() {
        var picked = root.excludedSubjects
        root.subjectChoices = root.allSubjectNames().filter(function (n) {
            return picked.indexOf(n) < 0
        })
    }

    function addExcludedSubject(name) {
        if (!name || root.excludedSubjects.indexOf(name) >= 0) return
        if (root.excludedSubjects.length >= 20) return
        var arr = root.excludedSubjects.slice()
        arr.push(name)
        root.excludedSubjects = arr
        saveExcluded()
    }

    function removeExcludedSubject(name) {
        root.excludedSubjects = root.excludedSubjects.filter(function (n) {
            return n !== name
        })
        saveExcluded()
    }

    function subjectColor(name) {
        try {
            var s = AppCentral.scheduleRuntime.subjects || []
            for (var i = 0; i < s.length; i++) {
                if (s[i].name === name) return s[i].color || "#888888"
            }
        } catch (e) {}
        return "#888888"
    }

    SettingItem {
        color: "transparent"
        title: qsTr("展示高度")
        description: qsTr("组件距屏幕顶部的距离（顶部停靠时生效）。")

        ColumnLayout {
            Layout.preferredWidth: 300
            Layout.fillWidth: true
            Slider {
                primaryColor: Colors.proxy.textColor
                id: displaySlider
                Layout.fillWidth: true
                from: 0
                to: 200
                stepSize: 4
                tickmarks: true
                tickFrequency: 50
                toolTip.text: Math.round(value) + " px"
                onValueChanged: {
                    if (pressed && !root.syncingControls && backend)
                        backend.setDisplayHeight(value)
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { typography: Typography.Caption; text: qsTr("跟随默认偏移") }
                Item { Layout.fillWidth: true }
                Text { typography: Typography.Caption; text: Math.round(displaySlider.value) + " px" }
            }
        }
    }

    SettingItem {
        showDivider: false
        color: "transparent"
        title: qsTr("隐藏深度")
        description: qsTr("隐藏时保留在屏幕边缘的可点击宽度（默认 24 px）。")

        ColumnLayout {
            Layout.preferredWidth: 300
            Layout.fillWidth: true
            Slider {
                primaryColor: Colors.proxy.textColor
                id: hideSlider
                Layout.fillWidth: true
                from: 0
                to: 200
                stepSize: 4
                tickmarks: true
                tickFrequency: 50
                toolTip.text: Math.round(value) + " px"
                onValueChanged: {
                    if (pressed && !root.syncingControls && backend)
                        backend.setHideDepth(value)
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { typography: Typography.Caption; text: "0 px" }
                Item { Layout.fillWidth: true }
                Text { typography: Typography.Caption; text: Math.round(hideSlider.value) + " px" }
            }
        }
    }

    SettingCard {
        color: "transparent"
        border.color: "transparent"
        Layout.topMargin: 10
        Layout.bottomMargin: 10
        Layout.fillWidth: true
        icon.name: "ic_fluent_eye_off_20_regular"
        title: qsTr("特定课程不隐藏")
        description: qsTr("开启后，当前课表科目在下方列表中时，主程序“在课堂中隐藏”不触发。按课程表编辑时该时间段所选科目判定，与课程标题无关。最多添加 20 个。")

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
            Switch {
                primaryColor: Colors.proxy.controlStrongColor
                id: excludedEnabledSwitch
                text: qsTr("启用")
                checked: root.excludedEnabled
                onToggled: saveExcluded()
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        visible: root.excludedSubjects.length === 0
                        typography: Typography.Caption
                        text: qsTr("尚未添加科目")
                    }

                    Repeater {
                        model: root.excludedSubjects
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Rectangle {
                                width: 6
                                height: 20
                                radius: 3
                                color: root.subjectColor(modelData)
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData
                                elide: Text.ElideRight
                            }
                            ToolButton {
                                icon.name: "ic_fluent_delete_20_regular"
                                onClicked: root.removeExcludedSubject(modelData)
                            }
                        }
                    }
                }

                ToolButton {
                    Layout.alignment: Qt.AlignTop
                    icon.name: "ic_fluent_add_20_regular"
                    enabled: root.excludedSubjects.length < 20
                    onClicked: subjectMenu.open()
                }
            }

            Menu {
                id: subjectMenu
                height: implicitHeight
                onAboutToShow: root.refreshSubjectMenu()
                // 预置固定数量项、用 visible 控制显隐：不动态增删 items。
                // RinUI 的 Menu 在动态插入项的布局/生命周期上不稳，固定项最稳（同官方 FilterToolbar）。
                // 上限 20 个科目，与加号按钮的 enabled 一致。
                Repeater {
                    model: 20
                    MenuItem {
                        required property int index
                        visible: index < root.subjectChoices.length
                        text: index < root.subjectChoices.length ? root.subjectChoices[index] : ""
                        onTriggered: {
                            if (index < root.subjectChoices.length) {
                                root.addExcludedSubject(root.subjectChoices[index])
                                subjectMenu.close()
                            }
                        }
                    }
                }
            }
        }
    }
}
