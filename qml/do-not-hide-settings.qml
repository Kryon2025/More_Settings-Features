import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import RinUI

/*
    特定课程不隐藏 —— 功能自己的设置页。

    由插件主设置页的功能格子用 Loader 加载，加载完由 Loader.onLoaded
    把插件对象注入到这里的 backend（与 countdown-settings.qml 同一机制）。

    UI 沿用拆分前「组件增强」里的原版：列表 + 添加菜单 + 逐项删除。
    （出处 c1c9728^:qml/extended-settings.qml，本次仅把容器
      SettingCard -> SettingItem，并去掉与本功能无关的高度部分。）

    持久化走 backend（= 插件的 @Slot），不能写 Configs.set：
    preferences 是主程序的固定 schema，新键会被拒；而插件 id 自带点，
    Configs.set("plugins.configs.com.kryon.more_settings.*") 的点号路径
    也会被拆错。插件 Slot 是框架给出的唯一可靠通道。
*/

ColumnLayout {
    id: root
    spacing: 0

    // 宿主在 Loader 加载后注入插件对象（见 settings.qml 的 onLoaded）
    property var backend: null

    // 排除科目（按课表所选科目判定，与课程标题无关）
    property bool excludedEnabled: false
    property var excludedSubjects: []
    property var subjectChoices: []

    Component.onCompleted: Qt.callLater(reloadExcluded)
    onBackendChanged: { if (backend) Qt.callLater(reloadExcluded) }

    Connections {
        target: backend
        function onConfigChanged() { root.reloadExcluded() }
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
        showDivider: false
        color: "transparent"
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
