"""堆叠组件 —— payload 实现。

两件事：
1. 给主程序 WidgetsContainer.qml / WidgetLoader.qml 打「编辑成员组件」入口补丁；
2. 注册 com.overlay 组件，用 payload 自带的 qml 与后端。

补丁锚点复用 integrations.py 里预置的组（同一份真相，不在这里复制一遍 QML 字符串），
但组件资源用 payload 自己的 —— 这样不必等插件本体发版就能更新堆叠组件。
"""

WIDGET_ID = "com.overlay"
NAME = "堆叠 / Stack"


def on_load(host):
    if host.app_root is None:
        host.warn("未找到主程序目录，跳过补丁")
    else:
        # 顺序很重要：容器补丁会往 WidgetsContainer.qml 注入
        # `AddOverlayMemberDialog { ... }` 这个引用，所以**必须先把它装进主程序**。
        # 反过来的话，补丁落盘了而组件不存在，主程序 QML 会因找不到组件而加载失败。
        try:
            host.install_host_file(
                "dialog",
                host.read_own_bytes("host_patch/AddOverlayMemberDialog.qml"),
                NAME,
            )
        except Exception as e:
            host.warn(f"装入成员选择窗口失败，跳过容器补丁: {e}")
            return

        try:
            # atomic：容器补丁里「引用对话框」与「入口按钮」必须成套，
            # 少一半会让主程序 QML 加载失败，所以整组成功才落盘。
            host.apply_ops("container", host.ops("overlay_container"), NAME, atomic=True)
            host.apply_ops("wloader", host.ops("overlay_wloader"), NAME)
        except Exception as e:
            host.warn(f"应用容器补丁失败: {e}")

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
