# Kryon-Features

「Kryon 的扩展设置」插件用的**功能包（payload）仓库**。功能实现放这里，
插件本体只留宿主接口 —— 用户点「安装」时才从这里下载。

## 为什么单独开一个仓库

- `.cwplugin` 里不带功能实现，只有一个下载器；
- 改一个功能不用重新发布插件；
- 用户没装的功能不会落到他机器上，**卸载才是真的卸载**。

## 目录

    manifest.json              适配清单。插件读它决定「你这个主程序版本能用哪些功能」
    payloads/*.cwpayload       功能包本体（仓库里的普通文件，下载地址就在 manifest 里）
    features_src/<功能 id>/    功能源码：payload.json（元数据）+ feature.py（入口）
    qml/  host_patch/  overlay_backend.py
                               payload.json 里 resources 声明的资源，路径必须与声明一致
    tools/features.json        人工维护的适配策略：功能叫什么、碰哪些文件、适配哪段主程序版本
    tools/make_payloads.py     构建 payload 并生成 manifest.json
    tools/payload_editor.py    开发者编辑器源码（改版本号 / 改适配范围 / 重建 / 校验）
    开发者编辑器.exe            上面那个源码打包成的窗口程序，双击即用
    开发者说明.md              给作者看的操作步骤

## 功能包怎么发给用户

功能包**不作为 GitHub Release 的附件**，它们就是仓库里的普通文件：

    payloads/<功能 id>-<版本号>.cwpayload

`manifest.json` 里每个版本条目带的 `asset` 就是这个文件的直链
（地址模板见 `tools/features.json` 的 `asset_url_template`）。
插件读清单 → 按直链下载 → 核对 sha256 → 解压落盘。

旧版本的文件**不要删**：老用户机器上记录的还是旧版本号，删了他们就下不到了。

## 加 / 改一个功能（用开发者编辑器，四步）

双击 `开发者编辑器.exe`：

1. 改版本号 —— 列表里点一行，在第 3 栏改 payload 版本，点「应用修改」；
2. 点「保存到文件」；
3. 点「重建勾选的」或「只重建有变化的」；
4. 试装 → 勾上「新版本标为已测试」→ 再重建一次 → 点「校验清单」。

然后**提交并推送 `payloads/` 与 `manifest.json`**，发布就完成了。

### 只想命令行也行

    # 重建全部并标记为已测试（默认输出到 payloads/）
    python tools/make_payloads.py --tested

    # 只重建指定功能
    python tools/make_payloads.py --only kryon.extended_settings,kryon.overlay --tested

    # 只重建「内容与上一版不同」的功能（代码 + 资源，不含版本号）
    python tools/make_payloads.py --changed --tested

    # 校验 manifest.json 与 payloads/ 里的文件是否一致
    python tools/make_payloads.py --check

改了源码却没重建就推送，GitHub Actions 的「校验功能包清单」会直接失败 ——
这是刻意的：`manifest.json` 里存着每个包的 sha256，插件下载后会核对，
发布一堆 hash 对不上的包比直接报错更糟。

## 版本号约定

功能版本用四段式 `1.3.3.20260916`，末段是日期，也可以直接用插件版本号（如 `1.3.4`）。

`cw2_min` / `cw2_max` 是**主程序**版本区间，必须写成主程序真实的写法
（`2.0.0.dev20260916` 或 `2.0.1.0`），**不要**写裸日期 `20260916` —— 两种写法会落进
不同的比较桶，判定会完全失真，表现为「所有功能都提示不在适配范围内」。

> 判定「适不适用」的代码，插件侧是 `installer_backend.cw_in_range`，
> 编辑器里是一份同源的拷贝（`tools/payload_editor.py`）。改一处要记得改另一处。
