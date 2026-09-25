# Kryon-Features

「Kryon 的扩展设置」插件用的**功能包（payload）仓库**。功能实现放这里，
插件本体只留宿主接口 —— 用户点「安装」时才从这里下载。

## 为什么单独开一个仓库

- `.cwplugin` 里不带功能实现，只有一个下载器；
- 改一个功能不用重新发布插件；
- 用户没装的功能不会落到他机器上，**卸载才是真的卸载**。

## 目录

    manifest.json              适配清单。插件读它决定「你这个主程序版本能用哪些功能」
    features_src/<功能 id>/    功能源码：payload.json（元数据）+ feature.py（入口）
    qml/  host_patch/  overlay_backend.py
                               payload.json 里 resources 声明的资源，路径必须与声明一致
    tools/features.json        人工维护的适配策略：功能叫什么、碰哪些文件、适配哪段主程序版本
    tools/make_payloads.py     构建 payload 并生成 manifest.json

## 加 / 改一个功能

1. 改 `features_src/<id>/feature.py`；
2. 用户能感觉到的改动，就把 `features_src/<id>/payload.json` 的 `version` 提到新版本号；
3. 构建：`python tools/make_payloads.py --out-dir dist --tag v<新版本号> --tested`
4. 把被它更新过的 `manifest.json` **一起提交**；
5. 打标签 `v<新版本号>` 推送。GitHub Actions 会校验 manifest.json 与本次构建产物
   一致，然后建发行版、把 `dist/*.cwpayload` 作为发行版文件传上去。

第 5 步的校验是刻意的：`manifest.json` 里存着每个包的 sha256，插件下载后会核对。
本地不提交、直接打标签，流水线会直接失败 —— 而不是发布一堆 hash 对不上的包。

### 用户怎么拿到功能包

两条路，都能用：

- **设置页里点安装** —— 插件读 manifest.json，下载对应功能包、核对 sha256、解压落盘。
- **去发行页手动下载** —— 功能包是发行版的普通文件，点一下直接下载，
  然后在设置页用「导入本地文件」导进来。插件里那套下载逻辑不通时，这条路还能走。

### 不想开流水线也行

流水线只是把下面两步连起来，手动做完全成立（就三个文件）。装了 `gh` 的话：

    python tools/make_payloads.py --out-dir dist --tag v<新版本号> --tested
    gh release create v<新版本号> dist/*.cwpayload --generate-notes

或者更省事：在 GitHub 的发行页上「Draft a new release」，把 `dist/` 里那三个
`.cwpayload` 拖进去。

## 版本号约定

功能版本用四段式 `1.3.3.20260916`，末段是日期。

`cw2_min` / `cw2_max` 是**主程序**版本区间，必须写成主程序真实的写法
（`2.0.0.dev20260916`），**不要**写裸日期 `20260916` —— 两种写法会落进不同的
比较桶，判定会完全失真，表现为「所有功能都提示不在适配范围内」。
