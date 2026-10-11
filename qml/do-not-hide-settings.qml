import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import RinUI


// 「特定课程不隐藏」功能的设置页 —— 装了它才会出现。
//
// 与旧版的区别：不再经插件 backend 读写配置（那是要拆掉的那根线），
// 改为直接读宿主全局单例 —— 与 eventCountdown.patch.qml 里
// Configs.data.plugins.configs["com.kryon.more_settings"] 同一套写法。
// 科目列表本来就直接读 AppCentral.scheduleRuntime.subjects。
ColumnLayout {
    id: root
    spacing: 0

    readonly property string pluginId: "com.kryon.more_settings"

    // 排除科目（按课表所选科目判定，与课程标题无关）
    property bool excludedEnabled: false
    property var excludedSubjects: []
    property var subjectChoices: []

    Component.onCompleted: Qt.callLater(reload)

    function pluginCfg() {
        try {
            return Configs.data.plugins.configs[root.pluginId] || null
        } catch (e) {
            return null
        }
    }

    function reload() {
        var cfg = root.pluginCfg()
        root.excludedEnabled = cfg ? (cfg.hide_excluded_enabled === true) : false
        var raw = cfg ? cfg.hide_excluded_subjects : ""
        var arr = []
        try {
            arr = typeof raw === "string" ? JSON.parse(raw || "[]") : (raw || [])
        } catch (e) {
            arr = []
        }
        root.excludedSubjects = Array.isArray(arr) ? arr.map(String) : []
        refreshSubjectMenu()
    }

    function saveExcluded() {
        try {
            Configs.set("plugins.configs." + root.pluginId + ".hide_excluded_enabled",
                        root.excludedEnabled)
            Configs.set("plugins.configs." + root.pluginId + ".hide_excluded_subjects",
                        JSON.stringify(root.excludedSubjects))
        } catch (e) {
            console.warn("保存「特定课程不隐藏」配置失败:", e)
        }
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
        root.subjectChoices = allSubjectNames().filter(function (n) {
            return picked.indexOf(n) < 0
        })
    }

    function addExcludedSubject(name) {
        if (!name || root.excludedSubjects.indexOf(name) >= 0) return
        if (root.excludedSubjects.length >= 20) return
        var arr = root.excludedSubjects.slice()
        arr.push(name)
        root.excludedSubjects = arr
        refreshSubjectMenu()
        saveExcluded()
    }

    function removeExcludedSubject(name) {
        root.excludedSubjects = root.excludedSubjects.filter(function (n) {
            return n !== name
        })
        refreshSubjectMenu()
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

    SettingCard {
        Layout.fillWidth: true
        title: qsTr("特定课程不隐藏")
        description: qsTr("仅在主程序「在课堂中隐藏」开启时生效；按课表所选科目判定，与课程标题无关。")

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8

            Switch {
                id: excludedEnabledSwitch
                checked: root.excludedEnabled
                text: qsTr("启用")
                onCheckedChanged: {
                    root.excludedEnabled = checked
                    root.saveExcluded()
                }
            }

            Text {
                Layout.fillWidth: true
                visible: root.excludedSubjects.length === 0
                opacity: 0.6
                wrapMode: Text.WordWrap
                text: qsTr("还没有排除科目。用下面的按钮从课表里选。")
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Repeater {
                    model: root.excludedSubjects

                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Rectangle {
                            width: 10
                            height: 10
                            radius: 5
                            color: root.subjectColor(modelData)
                        }
                        Text {
                            Layout.fillWidth: true
                            text: modelData
                            elide: Text.ElideRight
                        }
                        Button {
                            text: "−"
                            implicitWidth: 36
                            onClicked: root.removeExcludedSubject(modelData)
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                ComboBox {
                    id: subjectPicker
                    Layout.fillWidth: true
                    model: root.subjectChoices
                    enabled: root.excludedSubjects.length < 20
                    onActivated: {
                        root.addExcludedSubject(currentText)
                        currentIndex = -1
                    }
                }
                Button {
                    text: qsTr("刷新课表")
                    onClicked: root.refreshSubjectMenu()
                }
            }
        }
    }
}
