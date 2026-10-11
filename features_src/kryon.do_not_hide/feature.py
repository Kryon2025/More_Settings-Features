"""特定课程不隐藏 —— payload 实现。

官方「在课堂中隐藏」的例外：在排除列表里的科目上课时，保持小组件可见。

为什么这个包**不需要插件后端、也不需要 api**：
容器的 `hide` 本身就是一条 QML 绑定（`Configs.data.interactions.hide.state`），
而补丁把它改成「再与一个纯 QML 判断取与」即可 ——
科目与状态都从宿主单例直接读（`AppCentral.scheduleRuntime`），
与 overlay.qml:52、FloatingWidget.qml:78 的既有写法是同一套。
因此判断常驻在绑定里，不需要单独的看门狗进程。

配置落点必须用**无点号的键**：
`Configs.set` 只接受点号路径，而插件 id `com.kryon.more_settings` 自带点，
会被拆成多余的层级 -> 写不进去。故使用 `preferences.kryon_do_not_hide_*`
（`preferences` 是宿主自己就在写的可写字典，如 `floating_widget_x`）。

补丁锚点由本功能包在**自己安装后**才应用（见 on_load），
卸载即撤（宿主按 NAME 标签回退）。补丁字符串仍在插件 integrations.py 里，
保持「同一份真相」，不在两个仓库各存一份。
"""

NAME = "特定课程不隐藏"


def apply_patches(host):
    """只打补丁，不注册组件。返回是否成功。"""
    if host.app_root is None:
        host.warn("未找到主程序目录")
        return False

    try:
        host.apply_ops("container", host.ops("do_not_hide_ops"), NAME)
    except Exception as e:
        host.warn(f"应用「特定课程不隐藏」容器补丁失败: {e}")
        return False

    return True


def on_load(host):
    if not apply_patches(host):
        return
    host.log("补丁已注入")


def on_unload(host):
    host.log("已卸载")
