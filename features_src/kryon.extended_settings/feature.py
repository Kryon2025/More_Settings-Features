"""组件增强 —— payload 实现。

小组件高度/深度 + 特定课程不隐藏 + 组件设置页的 backendObj 注入。

这三项原本由插件本体的核心补丁无条件打进主程序（看起来像"自带功能"）；
现在归到可安装的功能名下，卸载后是真的从主程序里消失。

补丁锚点复用 integrations.py 里预置的组（同一份真相，不在这里复制 QML 字符串），
否则主程序改版时两边会各改各的。
"""

NAME = "组件增强"


def apply_patches(host):
    """只打补丁，不注册组件。返回是否成功。

    插件重建主程序文件时（main.py 的 _rebuild_patches）会调这个函数，
    所以它与 on_load 分开：重建只重打补丁，不重复注册。
    """
    if host.app_root is None:
        host.warn("未找到主程序目录")
        return False

    # 旧「小组件高度」插件（com.kryon.widgets-high）遗留的配置 key 与 Timer id 改名。
    # 单独一步、先判断：只有那个老插件打过补丁的文件里才有这些锚点，
    # 别的情况下不该去试，否则每次都会白报一条「锚点未找到」。
    try:
        text, _ = host.read_host("container")
        if "com.kryon.widgets-high" in text:
            host.apply_ops("container", host.ops("extended_legacy"), NAME)
    except Exception as e:
        host.warn(f"处理旧插件遗留失败，跳过: {e}")

    try:
        host.apply_ops("container", host.ops("extended_container"), NAME)
    except Exception as e:
        host.warn(f"应用容器补丁失败: {e}")
        return False

    # 旧版主程序（位置还写成 calcY 的时候）才套用 v1 整组，
    # 否则在 v2 上每次启动都会白报一串「锚点未找到」。
    try:
        text, _ = host.read_host("container")
        if "shownY" not in text:
            host.apply_ops("container", host.ops("extended_container_v1"), NAME)
    except Exception as e:
        host.warn(f"处理旧版主程序补丁失败，跳过: {e}")

    # v2：组件设置页的 setSource 在代理项文件里，backendObj 注入跟着搬过去
    try:
        host.apply_ops("delegate", host.ops("extended_delegate"), NAME)
    except Exception as e:
        host.warn(f"应用组件设置页补丁失败: {e}")

    return True


def on_load(host):
    if not apply_patches(host):
        return
    host.log("补丁已注入")


def on_unload(host):
    host.log("已卸载")
