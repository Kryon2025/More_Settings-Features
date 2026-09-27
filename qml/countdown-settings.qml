import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import RinUI

/*
    倒计时动画 —— 功能自己的设置页。

    由插件主设置页的功能格子用 Loader 加载，加载完由 Loader.onLoaded
    把插件对象注入到这里的 backend（理由见 time-settings.qml 的注释）。

    这个开关原本在主设置页里占了一个独立的大格子（「组件动画」），
    现在收进它所属的功能格子里 —— 装了才看得到、才有意义。
*/

ColumnLayout {
    id: countdownSettings
    spacing: 0

    // 由插件设置页在 Loader.onLoaded 里注入
    property var backend: null

    property bool loading: false
    property bool animation: true

    Component.onCompleted: load()
    onBackendChanged: load()

    function load() {
        if (!backend)
            return
        loading = true
        animation = backend.getCountdownAnimation()
        loading = false
    }

    SettingItem {
        showDivider: false
        color: "transparent"
        title: qsTr("事件倒计时动画")
        description: qsTr("开启后内置“事件倒计时”组件的分钟/秒数字带滚动动画；关闭后静态显示。")

        Switch {
            primaryColor: Colors.proxy.controlStrongColor
            checked: countdownSettings.animation
            onToggled: {
                countdownSettings.animation = checked
                if (!countdownSettings.loading && countdownSettings.backend)
                    countdownSettings.backend.setCountdownAnimation(checked)
            }
        }
    }
}
