import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import RinUI

/*
    特定课程不隐藏 —— 功能自己的设置页。

    由插件主设置页的功能格子用 Loader 加载，加载完由 Loader.onLoaded
    把插件对象注入到这里的 backend（与 countdown-settings.qml 同一机制）。

    持久化必须走 backend（= 插件的 @Slot），不能写 Configs.set：
    preferences 是主程序的固定 schema，新键会被拒；而插件 id 自带点，
    Configs.set("plugins.configs.com.kryon.more_settings.*") 的点号路径
    也会被拆错。插件 Slot 是框架给出的唯一可靠通道。
*/

ColumnLayout {
    id: excludedSettings
    spacing: 0

    // 由插件设置页在 Loader.onLoaded 里注入
    property var backend: null

    property bool loading: false
    property bool enabled: false
    property var selected: []

    Component.onCompleted: load()
    onBackendChanged: load()

    function load() {
        if (!backend) {
            return
        }
        loading = true
        var cfg = backend.getExcludedLessonConfig()
        enabled = cfg && cfg.enabled === true
        selected = (cfg && cfg.subjects) ? cfg.subjects : []
        loading = false
        rebuildModel()
    }

    function save() {
        if (loading || !backend) {
            return
        }
        backend.setExcludedLessonConfig(enabled, selected)
    }

    // 可选科目：直接读宿主课表的科目表（与 overlay.qml 同一来源）
    property var allSubjects: []
    ListModel { id: subjectModel }

    function rebuildModel() {
        try {
            var s = AppCentral.scheduleRuntime.subjects || []
            var names = []
            for (var i = 0; i < s.length; i++) {
                if (s[i] && s[i].name) {
                    names.push(s[i].name)
                }
            }
            allSubjects = names
        } catch (e) {
            allSubjects = []
        }
        subjectModel.clear()
        for (var j = 0; j < allSubjects.length; j++) {
            subjectModel.append({
                "name": allSubjects[j],
                "on": selected.indexOf(allSubjects[j]) >= 0
            })
        }
    }

    function toggleSubject(name, isOn) {
        var idx = selected.indexOf(name)
        if (isOn && idx < 0) {
            selected = selected.concat([name])
        } else if (!isOn && idx >= 0) {
            var next = selected.slice()
            next.splice(idx, 1)
            selected = next
        }
        save()
    }

    SettingItem {
        showDivider: false
        color: "transparent"
        title: qsTr("特定课程不隐藏")
        description: qsTr("开启后，下面选中的科目上课时，小组件保持可见，不受主程序「在课堂中隐藏」影响。")

        Switch {
            primaryColor: Colors.proxy.controlStrongColor
            checked: excludedSettings.enabled
            onToggled: {
                excludedSettings.enabled = checked
                excludedSettings.save()
            }
        }
    }

    SettingItem {
        showDivider: false
        color: "transparent"
        title: qsTr("不隐藏的科目")
        description: excludedSettings.allSubjects.length > 0
                     ? qsTr("勾选后，该科目上课时不隐藏。")
                     : qsTr("课表里还没有科目。")

        ColumnLayout {
            Layout.preferredWidth: 300
            Layout.fillWidth: true
            spacing: 4

            Repeater {
                model: subjectModel
                delegate: CheckBox {
                    required property string name
                    required property bool on
                    text: name
                    checked: on
                    enabled: excludedSettings.enabled
                    onToggled: excludedSettings.toggleSubject(name, checked)
                }
            }
        }
    }
}
