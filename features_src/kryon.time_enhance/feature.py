"""时间组件增强 —— payload 实现。

把主程序内置的 widgets/Time.qml 整体换成带开关的补丁版。

补丁走宿主接口，与插件内置补丁共用同一个备份命名空间，所以重复安装是幂等的，
卸载时由插件的 restore_all() 统一还原，这里不需要自己回滚。
"""

NAME = "时间组件增强"


def on_load(host):
    if host.app_root is None:
        host.warn("未找到主程序目录，跳过")
        return
    try:
        changed = host.replace_host_qml(
            "time", host.read_own("qml/time.patch.qml"), NAME)
    except Exception as e:
        host.warn(f"应用补丁失败: {e}")
        return
    host.log("已应用补丁" if changed else "补丁内容已是最新，跳过")


def on_unload(host):
    # 主程序文件由插件统一还原（共享备份命名空间），此处不单独回滚，
    # 否则会把同一文件上其它补丁的成果一起抹掉。
    host.log("已卸载")
