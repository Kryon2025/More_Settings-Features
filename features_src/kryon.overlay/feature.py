"""堆叠组件 —— payload 实现。

两件事：
1. 给主程序 WidgetsContainer.qml / WidgetLoader.qml 打「编辑成员组件」入口补丁，
   并把成员选择窗口装进主程序；
2. 注册 com.overlay 组件，用 payload 自带的 qml 与后端。

补丁锚点复用 integrations.py 里预置的组（同一份真相，不在这里复制一遍 QML 字符串），
但组件资源用 payload 自己的 —— 这样不必等插件本体发版就能更新堆叠组件。

补丁与注册分成两个函数：插件重建主程序文件时只调 apply_patches，
不重复注册组件（注册是进程级的，重来一次会冲突）。
"""

WIDGET_ID = "com.overlay"
NAME = "堆叠 / Stack"


def _patched(host, file_key, marker):
    """判断某个主程序文件是否已经带上了本次补丁的标记。"""
    try:
        text, _ = host.read_host(file_key)
        return marker in text
    except Exception:                                          # noqa: BLE001
        return False


def apply_patches(host):
    """只打补丁，不注册组件。返回是否全部成功。"""
    if host.app_root is None:
        host.warn("未找到主程序目录")
        return False

    # 补丁 ops 随功能包版本走（原来放在加载器 integrations.py 里）
    P = host.import_own("patches.py")

    # 已移除「编辑成员组件」入口与其成员弹窗：把对应 op 全部剔除，避免再次注入
    _DROP = ("编辑成员组件", "overlayMemberDialog", "AddOverlayMemberDialog")
    for _n in ("_OVERLAY_LAYOUT_OPS", "_OVERLAY_DELEGATE_OPS",
               "_OVERLAY_CONTAINER_V2_OPS", "_CONTAINER_OVERLAY_OPS", "_WLOADER_OPS"):
        setattr(P, _n, [o for o in getattr(P, _n)
                        if not any(m in o[1] for m in _DROP)])

    # 顺序很重要：容器补丁会往 WidgetsContainer.qml 注入
    # `AddOverlayMemberDialog { ... }` 这个引用，所以**必须先把它装进主程序**。
    # 反过来的话，补丁落盘了而组件不存在，主程序 QML 会因找不到组件而加载失败。
    # 成员弹窗已移除（AddOverlayMemberDialog 不再安装）

    # 新版主程序（2.0.0.dev20260928 起）把每个组件的界面代码拆进了
    # WidgetsLayout.qml 与 WidgetsLayoutDelegate.qml，补丁随之分到这两个文件。
    # 判定方式与「组件增强」一致：看布局文件里有没有新属性。
    try:
        host.apply_ops("layout", P._OVERLAY_LAYOUT_OPS, NAME, atomic=True)
    except Exception as e:
        host.warn(f"新版布局补丁未应用（旧版主程序属正常）: {e}")

    if _patched(host, "layout", "overlayEditingId"):
        # 布局必须先成：代理项会引用 host.overlayEditingId
        try:
            # atomic：入口菜单项、编辑行、成员窗口引用必须成套，
            # 少一半会让主程序 QML 加载失败，所以整组成功才落盘。
            host.apply_ops("delegate", P._OVERLAY_DELEGATE_OPS, NAME, atomic=True)
        except Exception as e:
            host.warn(f"应用新版代理项补丁失败: {e}")
            return False
        try:
            host.apply_ops("container", P._OVERLAY_CONTAINER_V2_OPS, NAME)
        except Exception as e:
            host.warn(f"应用新版容器可见性补丁失败: {e}")
    else:
        # 旧版主程序：原来的容器 + WidgetLoader 补丁
        try:
            # atomic：容器补丁里「引用对话框」与「入口按钮」必须成套，
            # 少一半会让主程序 QML 加载失败，所以整组成功才落盘。
            host.apply_ops("container", P._CONTAINER_OVERLAY_OPS, NAME, atomic=True)
            host.apply_ops("wloader", P._WLOADER_OPS, NAME)
        except Exception as e:
            host.warn(f"应用容器补丁失败: {e}")
            return False
    return True


def on_load(host):
    if host.app_root is None:
        host.warn("未找到主程序目录，跳过补丁")
    elif not apply_patches(host):
        # 补丁没打成就不注册组件：注册了界面上也会多一个用不了的组件
        host.warn("补丁未全部打上，跳过组件注册")
        return

    backend = None
    try:
        mod = host.import_own("overlay_backend.py")
        backend = mod.OverlayBackend(host.plugin)
    except Exception as e:
        host.warn(f"堆叠后端加载失败，改用无后端模式: {e}")

    try:
        host.register_widget(
            WIDGET_ID, NAME,
            qml_path="qml/overlay.qml",
            backend_obj=backend,
            settings_qml="qml/overlay-settings.qml",
            default_settings={"interval_ms": 5000, "lyric_gate": False},
        )
        host.log("组件已注册")
    except Exception as e:
        host.warn(f"注册组件失败: {e}")


def on_unload(host):
    host.log("已卸载")
