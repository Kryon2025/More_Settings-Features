"""列出每个功能包各自应发的标签与标题，输出给发布工作流的矩阵用。

用法（在仓库根目录执行）：
    python tools/list_payloads.py            # 打印 payloads=<json>
    python tools/list_payloads.py >> "$GITHUB_OUTPUT"

每个功能包一个独立标签：<功能 id>-<版本>，例如 kryon.overlay-1.4.3。
标题：<功能名> <版本>。正文：适配的主程序版本区间。
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    out = []
    for feat in manifest.get("features", []):
        for ver in feat.get("versions", []):
            name = ver["asset"].rstrip("/").split("/")[-1]
            lo = ver.get("cw2_min", feat.get("cw2_min"))
            hi = ver.get("cw2_max", feat.get("cw2_max"))
            rng = f"{lo} ~ {hi}" if hi else f"{lo} 及以上"
            out.append({
                "tag": f"{feat['id']}-{ver['version']}",
                "name": name,
                "title": f"{feat.get('name', feat['id'])} {ver['version']}",
                "body": (f"`{feat.get('name', feat['id'])}` 功能包 **{ver['version']}**。\n\n"
                         f"- 适配主程序：`{rng}`\n"
                         f"- 文件：`{name}`\n"
                         f"- 版本号 / 大小 / sha256 以仓库根目录 "
                         f"[manifest.json](https://github.com/Kryon2025/More_Settings-Features/blob/main/manifest.json)"
                         f" 为准 —— 加载器读的就是它。"),
            })
    print("payloads=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
