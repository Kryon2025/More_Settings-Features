"""适配清单体检工具。发布前跑一遍，把结构性错误挡在上传之前。

用法：
    python tools/validate_manifest.py                     # 只查格式
    python tools/validate_manifest.py --dir "F:\\class widgets 2 插件"
                                                          # 额外核对文件是否存在、sha256 是否一致

检查项：
    - schema / installer / features 结构完整
    - 每个 feature 的 id 唯一、字段齐全
    - 每个版本号能被主程序的日期版本规则接受
    - asset 地址形态正确（GitHub Release 固定格式）
    - sha256 是 64 位十六进制
    - cw2_min <= cw2_max（都填了的话）
    - 同一个主程序文件被多个功能声明时给出冲突警告（不是错误，但要知道）
    - 给了 --dir 时：包存在、大小一致、sha256 一致、包内版本的版本号与条目一致
"""

import argparse
import hashlib
import json
import pathlib
import re
import sys
import zipfile

from make_manifest import cw_key, sha256_of

HEX64 = re.compile(r"^[0-9a-f]{64}$")
DATE8 = re.compile(r"\d{8}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="manifest.json")
    ap.add_argument("--dir", default="", help="给了就核对包文件")
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parent.parent
    path = root / args.manifest
    errors, warns = [], []

    if not path.exists():
        print(f"找不到清单文件: {path}")
        return 2

    try:
        m = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"JSON 解析失败: {e}")
        return 2

    if not isinstance(m.get("schema"), int):
        errors.append("缺少 schema（应为整数）")
    inst = m.get("installer") or {}
    if not inst.get("repo"):
        errors.append("installer.repo 缺失")
    if inst.get("min_cw2") and not DATE8.search(str(inst["min_cw2"])):
        warns.append(f"installer.min_cw2={inst['min_cw2']} 取不到 8 位日期，"
                     f"将退回字符串比较")

    feats = m.get("features")
    if not isinstance(feats, list) or not feats:
        errors.append("features 缺失或为空")
        feats = []

    seen_ids, file_owner = set(), {}
    total = 0
    for f in feats:
        fid = f.get("id", "<无 id>")
        if fid in seen_ids:
            errors.append(f"重复的功能 id: {fid}")
        seen_ids.add(fid)
        if not f.get("name"):
            errors.append(f"{fid}: 缺少 name")
        if "versions" not in f:
            errors.append(f"{fid}: 缺少 versions 字段")

        lo, hi = f.get("cw2_min"), f.get("cw2_max")
        if lo and not DATE8.search(str(lo)):
            warns.append(f"{fid}: cw2_min={lo} 取不到日期")
        if hi and not DATE8.search(str(hi)):
            warns.append(f"{fid}: cw2_max={hi} 取不到日期")
        if lo and hi and cw_key(lo) > cw_key(hi):
            errors.append(f"{fid}: cw2_min({lo}) 大于 cw2_max({hi})")

        for p in f.get("patches", []):
            file_owner.setdefault(p, []).append(fid)

        vers = f.get("versions") or []
        if not vers:
            warns.append(f"{fid}: 没有任何版本条目")
        for v in vers:
            total += 1
            tag = f"{fid} {v.get('version')}"
            if not DATE8.search(str(v.get("version", ""))):
                warns.append(f"{tag}: 版本号取不到日期")
            if not isinstance(v.get("tested"), bool):
                errors.append(f"{tag}: tested 必须是 true/false")
            sha = v.get("sha256", "")
            if not HEX64.match(sha):
                errors.append(f"{tag}: sha256 不是 64 位十六进制")
            asset = v.get("asset", "")
            if not asset.startswith("https://github.com/"):
                errors.append(f"{tag}: asset 不是 GitHub 地址")
            elif "/releases/download/" not in asset:
                errors.append(f"{tag}: asset 不是 Release 固定格式")

    for p, owners in file_owner.items():
        if len(owners) > 1:
            warns.append(f"主程序文件被多个功能声明: {p} ← {', '.join(owners)}")

    # 可选：核对实际文件
    if args.dir:
        d = pathlib.Path(args.dir)
        for f in feats:
            for v in f.get("versions") or []:
                name = str(v.get("asset", "")).rsplit("/", 1)[-1]
                if not name:
                    continue
                # 允许包放在子目录里（发布构建目录常常是分层的）
                hits = list(d.rglob(name))
                tag = f"{f.get('id')} {v.get('version')}"
                if not hits:
                    warns.append(f"{tag}: 本地找不到 {name}（可能尚未构建）")
                    continue
                pkg = hits[0]
                if pkg.stat().st_size != v.get("size"):
                    errors.append(f"{tag}: 大小不一致 "
                                  f"（清单 {v.get('size')} / 实际 {pkg.stat().st_size}）")
                actual = sha256_of(pkg)
                if actual != v.get("sha256"):
                    errors.append(f"{tag}: sha256 不一致（清单 {v.get('sha256')[:12]}… / "
                                  f"实际 {actual[:12]}…）")
                else:
                    with zipfile.ZipFile(pkg) as z:
                        try:
                            meta = json.loads(z.read("cwplugin.json").decode("utf-8"))
                        except Exception:
                            meta = {}
                    if meta.get("version") != v.get("version"):
                        errors.append(f"{tag}: 包内版本 {meta.get('version')} 与条目不一致")

    print(f"清单: {path}")
    print(f"功能 {len(feats)} 个，版本条目 {total} 条")
    print()
    if errors:
        print(f"错误 {len(errors)} 项：")
        for e in errors:
            print(f"  !! {e}")
    else:
        print("错误：无")
    if warns:
        print()
        print(f"提醒 {len(warns)} 项：")
        for w in warns:
            print(f"  ~  {w}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
