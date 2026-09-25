"""倒计时动画 —— payload 实现。

把主程序内置的 widgets/eventCountdown.qml 整体换成带开关的补丁版，
补丁版会读插件配置里的 countdown_animation。

与内置补丁共用备份命名空间，重复安装幂等，卸载时由插件统一还原。
"""

NAME = "倒计时动画"


def on_load(host):
    if host.app_root is None:
        host.warn("未找到主程序目录，跳过")
        return
    try:
        changed = host.replace_host_qml(
            "countdown", host.read_own("qml/eventCountdown.patch.qml"), NAME)
    except Exception as e:
        host.warn(f"应用补丁失败: {e}")
        return
    host.log("已应用补丁" if changed else "补丁内容已是最新，跳过")


def on_unload(host):
    host.log("已卸载")
