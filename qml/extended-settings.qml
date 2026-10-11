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
    }

    function syncControls() {
        root.syncingControls = true
        var hd = info.hide_depth
        hideSlider.value = (hd !== undefined && hd !== null) ? hd : 24
        root.syncingControls = false
    }


    SettingItem {
        color: "transparent"
        title: qsTr("展示高度")
        description: qsTr("可在主程序设置-小组件-小组件布局-展开设置列表 中进行Y轴偏移修改")
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

}
