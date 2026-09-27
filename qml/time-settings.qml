import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import RinUI

/*
    时间组件增强 —— 功能自己的设置页。

    由插件主设置页的功能格子用 Loader 加载（路径取自后端 featureSettingsUrl），
    加载完由 Loader.onLoaded 把**插件对象**注入到这里的 backend。

    为什么要注入：这些开关读写的是插件的配置（plugins.configs.com.kryon.more_settings），
    而不是某个组件实例的设置。payload 设置页自己去翻 WidgetsModel 只能拿到
    「组件后端」，拿不到插件对象，所以由宿主注入更直接、也不会混淆两者。

    根元素用 ColumnLayout 而不是 SettingsLayout：Loader 会把 item 的尺寸设成自己的尺寸，
    ColumnLayout 的行为完全可预测，不依赖框架容器的默认属性怎么排布子项。
*/

ColumnLayout {
    id: timeSettings
    spacing: 0

    // 由插件设置页在 Loader.onLoaded 里注入
    property var backend: null

    property var cfg: ({})
    // 载入时压住改动通知：整份 cfg 重设会改到每个 Switch 的 checked，
    // 进而触发 onToggled 把配置又写回去（写的是同值，但会多一轮无谓的持久化）。
    property bool loading: false

    Component.onCompleted: load()
    onBackendChanged: load()

    function load() {
        if (!backend)
            return
        var info = backend.getConfig() || {}
        loading = true
        cfg = {
            time_animation: info.time_animation !== false,
            time_show_seconds: info.time_show_seconds !== false,
            time_show_date: info.time_show_date !== false,
            time_show_year: info.time_show_year !== false,
            time_show_month: info.time_show_month !== false,
            time_show_day: info.time_show_day !== false,
            time_show_weekday: info.time_show_weekday !== false,
            time_title_mode: info.time_title_mode || "side_by_side",
            time_alternate_interval: info.time_alternate_interval || 3000,
            time_alternate_animation: info.time_alternate_animation === true
        }
        loading = false
    }

    function commit(key, value) {
        if (loading)
            return
        var c = cfg
        c[key] = value
        cfg = c
        if (backend)
            backend.setTimeConfig(cfg)
    }

    SettingItem {
        color: "transparent"
        title: qsTr("时钟动画")
        description: qsTr("官方内置“时间”组件的时分秒数字更新时是否播放滚动动画。")

        Switch {
            primaryColor: Colors.proxy.controlStrongColor
            checked: timeSettings.cfg.time_animation
            onToggled: timeSettings.commit("time_animation", checked)
        }
    }

    SettingItem {
        color: "transparent"
        title: qsTr("显示秒")
        description: qsTr("在官方内置“时间”组件中显示秒数。")

        Switch {
            primaryColor: Colors.proxy.controlStrongColor
            checked: timeSettings.cfg.time_show_seconds
            onToggled: timeSettings.commit("time_show_seconds", checked)
        }
    }

    SettingItem {
        color: "transparent"
        title: qsTr("显示日期")
        description: qsTr("在组件标题栏显示日期。")

        Switch {
            primaryColor: Colors.proxy.controlStrongColor
            checked: timeSettings.cfg.time_show_date
            onToggled: timeSettings.commit("time_show_date", checked)
        }
    }

    SettingItem {
        color: "transparent"
        title: qsTr("日期内容")
        description: qsTr("选择日期需要展示的部分。")

        RowLayout {
            Layout.preferredWidth: 260
            spacing: 8
            Switch {
                primaryColor: Colors.proxy.controlStrongColor
                text: qsTr("年")
                checked: timeSettings.cfg.time_show_year
                onToggled: timeSettings.commit("time_show_year", checked)
            }
            Switch {
                primaryColor: Colors.proxy.controlStrongColor
                text: qsTr("月")
                checked: timeSettings.cfg.time_show_month
                onToggled: timeSettings.commit("time_show_month", checked)
            }
            Switch {
                primaryColor: Colors.proxy.controlStrongColor
                text: qsTr("日")
                checked: timeSettings.cfg.time_show_day
                onToggled: timeSettings.commit("time_show_day", checked)
            }
        }
    }

    SettingItem {
        color: "transparent"
        title: qsTr("显示星期")
        description: qsTr("在组件标题栏显示星期几。")

        Switch {
            primaryColor: Colors.proxy.controlStrongColor
            checked: timeSettings.cfg.time_show_weekday
            onToggled: timeSettings.commit("time_show_weekday", checked)
        }
    }

    SettingItem {
        color: "transparent"
        title: qsTr("日期与星期布局")
        description: qsTr("并排显示在同一行，或按间隔时间交替展示。")

        Segmented {
            currentIndex: timeSettings.cfg.time_title_mode === "alternate" ? 1 : 0
            onCurrentIndexChanged: timeSettings.commit(
                "time_title_mode", currentIndex === 1 ? "alternate" : "side_by_side")
            SegmentedItem { text: qsTr("并排") }
            SegmentedItem { text: qsTr("交替") }
        }
    }

    SettingItem {
        color: "transparent"
        title: qsTr("交替间隔")
        description: qsTr("交替展示时，日期与星期各自停留的时间（毫秒），加减按钮以 100ms 调整。")
        enabled: timeSettings.cfg.time_title_mode === "alternate"

        RowLayout {
            Layout.preferredWidth: 260
            spacing: 8
            Button {
                text: "−"
                implicitWidth: 36
                onClicked: timeSettings.commit("time_alternate_interval",
                    Math.max(500, (timeSettings.cfg.time_alternate_interval || 3000) - 100))
            }
            Text {
                Layout.preferredWidth: 90
                horizontalAlignment: Text.AlignHCenter
                text: (timeSettings.cfg.time_alternate_interval || 3000) + " ms"
            }
            Button {
                text: "+"
                implicitWidth: 36
                onClicked: timeSettings.commit("time_alternate_interval",
                    Math.min(10000, (timeSettings.cfg.time_alternate_interval || 3000) + 100))
            }
        }
    }

    SettingItem {
        showDivider: false
        color: "transparent"
        title: qsTr("交替动画")
        description: qsTr("交替展示时，日期与星期切换是否带淡入淡出效果。")
        enabled: timeSettings.cfg.time_title_mode === "alternate"

        Switch {
            primaryColor: Colors.proxy.controlStrongColor
            checked: timeSettings.cfg.time_alternate_animation
            onToggled: timeSettings.commit("time_alternate_animation", checked)
        }
    }
}
